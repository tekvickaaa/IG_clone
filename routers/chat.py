from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict
from schemas import MessageResponse
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Message, User


router = APIRouter(tags=["chat"])
connections: Dict[int, WebSocket] = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    user_id = int(user_id)
    connections[user_id] = websocket

    db: Session = SessionLocal()
    try:
        unread_msgs = db.query(Message).filter(
            Message.receiver_id == user_id,
            Message.read == False
        ).order_by(Message.sent_at).all()

        for msg in unread_msgs:
            await websocket.send_json({
                "id": msg.id,
                "sender_id": msg.sender_id,
                "receiver_id": msg.receiver_id,
                "content": msg.content,
                "type": msg.type,
                "sent_at": str(msg.sent_at)
            })
            msg.read = True
        db.commit()

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                try:
                    new_msg = Message(
                        sender_id=int(data["sender_id"]),
                        receiver_id=int(data["receiver_id"]),
                        content=data["content"],
                        type=data.get("type", "text"),
                        read=False
                    )
                    db.add(new_msg)
                    db.commit()
                    db.refresh(new_msg)
                except Exception:
                    db.rollback()
                    continue

                message_payload = {
                    "id": new_msg.id,
                    "sender_id": new_msg.sender_id,
                    "receiver_id": new_msg.receiver_id,
                    "content": new_msg.content,
                    "type": new_msg.type,
                    "sent_at": str(new_msg.sent_at),
                    "read": False
                }
                
          
                receiver_id = int(data["receiver_id"])
                receiver_ws = connections.get(receiver_id)
                if receiver_ws:
                    try:
                        await receiver_ws.send_json(message_payload)
                    except Exception:
                        pass
                
              
                sender_id = int(data["sender_id"])
                sender_ws = connections.get(sender_id)
                if sender_ws:
                    try:
                        await sender_ws.send_json(message_payload)
                    except Exception:
                        pass

            elif msg_type == "read_receipt":
                try:
                    msg = db.query(Message).get(data["message_id"])
                    if msg:
                        msg.read = True
                        db.commit()
                        sender_ws = connections.get(msg.sender_id)
                        if sender_ws:
                            await sender_ws.send_json({
                                "type": "read_receipt",
                                "message_id": msg.id
                            })
                except Exception:
                    db.rollback()

    except WebSocketDisconnect:
        connections.pop(user_id, None)
        db.close()

@router.get("/dm_previews/{user_id}")
def get_dm_previews(user_id: int, db: Session = Depends(get_db)):
    conv_user_ids = db.query(
        Message.sender_id, Message.receiver_id
    ).filter(
        or_(Message.sender_id == user_id, Message.receiver_id == user_id)
    ).all()

    partners = set()
    for s_id, r_id in conv_user_ids:
        partner_id = r_id if s_id == user_id else s_id
        partners.add(partner_id)

    previews = []
    for partner_id in partners:
        latest_msg = db.query(Message).filter(
            or_(
                (Message.sender_id == user_id) & (Message.receiver_id == partner_id),
                (Message.sender_id == partner_id) & (Message.receiver_id == user_id)
            )
        ).order_by(desc(Message.sent_at)).first()

        unread_count = db.query(func.count(Message.id)).filter(
            Message.sender_id == partner_id,
            Message.receiver_id == user_id,
            Message.read == False
        ).scalar()

        previews.append({
            "chat_with_id": partner_id,
            "latest_message": latest_msg.content if latest_msg else None,
            "latest_sent_at": str(latest_msg.sent_at) if latest_msg else None,
            "unread_count": unread_count
        })

    return previews


@router.get("/messages/{user_id}/{partner_id}", response_model=list[MessageResponse])
def get_messages(
    user_id: int,
    partner_id: int,
    db: Session = Depends(get_db)
):
    messages = db.query(Message).filter(
        or_(
            (Message.sender_id == user_id) & (Message.receiver_id == partner_id),
            (Message.sender_id == partner_id) & (Message.receiver_id == user_id)
        )
    ).order_by(Message.sent_at.asc()).all()

    for msg in messages:
        if msg.receiver_id == user_id and msg.read is False:
            msg.read = True
    db.commit()

    return messages