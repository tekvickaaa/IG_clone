from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from typing import Annotated
from fastapi.params import Form
from database import SessionLocal
from starlette import status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func
from models import Reel, ReelLike, ReelComment, User
from routers.auth import get_current_user
from schemas import ReelResponse, ReelListItem, ReelCommentResponse
import os
import uuid
from pathlib import Path
from dotenv import load_dotenv

router = APIRouter(
    prefix="/reels",
    tags=["reels"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = Path(os.getenv("MEDIA_DIR", "media"))
MEDIA_DIR = BASE_DIR / MEDIA_DIR
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
BASE_URL = os.getenv("BASE_URL", "http://56.228.35.186")

MAX_VIDEO_SIZE = 400 * 1024 * 1024
ALLOWED_VIDEO_MIME = "video/mp4"

@router.get("/", response_model=list[ReelListItem])
async def get_all_reels(db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    reels = (
        db.query(Reel)
        .options(joinedload(Reel.user))
        .order_by(Reel.created_at.desc())
        .all()
    )

    counts = (
        db.query(ReelComment.reel_id, func.count(ReelComment.id))
        .group_by(ReelComment.reel_id)
        .all()
    )
    comment_map = {r[0]: r[1] for r in counts}

    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "description": r.description,
            "video_url": r.video_url if r.video_url and r.video_url.startswith("http") else (f"{BASE_URL}{r.video_url}" if r.video_url else None),
            "like_count": r.like_count,
            "comment_count": comment_map.get(r.id, 0),
            "created_at": r.created_at,
            "user": {"id": r.user.id, "username": r.user.username, "pfp_url": r.user.pfp_url},
            "has_liked": user["id"] in r.like
        }
        for r in reels
    ]

@router.get("/explore", response_model=list[ReelListItem])
async def get_explore_reels(db: db_dependency, user: user_dependency, limit: int = 20):
    results = (
        db.execute(
            select(Reel)
            .options(joinedload(Reel.user))
            .order_by(func.random())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    counts = (
        db.query(ReelComment.reel_id, func.count(ReelComment.id))
        .group_by(ReelComment.reel_id)
        .all()
    )
    comment_map = {r[0]: r[1] for r in counts}

    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "description": r.description,
            "video_url": r.video_url if r.video_url and r.video_url.startswith("http") else (f"{BASE_URL}{r.video_url}" if r.video_url else None),
            "like_count": r.like_count,
            "comment_count": comment_map.get(r.id, 0),
            "created_at": r.created_at,
            "user": {"id": r.user.id, "username": r.user.username, "pfp_url": r.user.pfp_url},
            "has_liked": user["id"] in r.like
        }
        for r in results
    ]
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ReelResponse)
async def create_reel(
    db: db_dependency,
    user: user_dependency,
    description: str | None = Form(None),
    video: UploadFile = File(...)
):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if not video or not getattr(video, "filename"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No video provided")

    if not (video.content_type and video.content_type.startswith(ALLOWED_VIDEO_MIME)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Only MP4 videos allowed. Got: {video.content_type}")

    user_dir = MEDIA_DIR / str(user["id"])
    user_dir.mkdir(parents=True, exist_ok=True)

    ext = os.path.splitext(video.filename)[1] or ".mp4"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = user_dir / unique_name

    try:
        file_size = 0
        with open(file_path, "wb") as f:
            while chunk := await video.read(1024 * 1024):
                file_size += len(chunk)
                if file_size > MAX_VIDEO_SIZE:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File too large. Max size: {MAX_VIDEO_SIZE/(1024*1024):.0f}MB")
                f.write(chunk)

        video_url = f"{BASE_URL}/media/{user['id']}/{unique_name}"

        new_reel = Reel(
            user_id=user["id"],
            description=description,
            video_url=video_url,
            like_count=0
        )
        db.add(new_reel)
        db.commit()
        db.refresh(new_reel)

        return {
            "id": new_reel.id,
            "user_id": new_reel.user_id,
            "description": new_reel.description,
            "video_url": new_reel.video_url,
            "like_count": new_reel.like_count,
            "created_at": new_reel.created_at,
            "updated_at": new_reel.updated_at,
            "user": {"id": new_reel.user.id, "username": new_reel.user.username, "pfp_url": new_reel.user.pfp_url},
            "has_liked": user["id"] in new_reel.like
        }

    except HTTPException:
        if file_path.exists():
            file_path.unlink()
        db.rollback()
        raise

    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error uploading video: {e}")


@router.delete("/{reel_id}")
async def delete_reel(reel_id: int, db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    reel = db.query(Reel).filter(Reel.id == reel_id).first()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    if reel.user_id != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    if reel.video_url:
        try:
            path = reel.video_url.replace(f"{BASE_URL}/", "")
            abs_path = BASE_DIR / path
            if abs_path.exists():
                abs_path.unlink()
        except:
            pass

    db.delete(reel)
    db.commit()
    return {"message": "Reel deleted successfully"}

@router.post("/{reel_id}/like")
async def like_reel(reel_id: int, db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    reel = db.query(Reel).filter(Reel.id == reel_id).first()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    existing = db.query(ReelLike).filter(ReelLike.reel_id == reel_id, ReelLike.user_id == user["id"]).first()
    if existing:
        db.delete(existing)
        if reel.like_count and reel.like_count > 0:
            reel.like_count -= 1
        db.commit()
        return {"message": "Reel unliked", "like_count": reel.like_count}
    else:
        new_like = ReelLike(user_id=user["id"], reel_id=reel_id)
        db.add(new_like)
        reel.like_count = (reel.like_count or 0) + 1
        db.commit()
        db.refresh(reel)
        return {"message": "Reel liked", "like_count": reel.like_count}

@router.post(
    "/{reel_id}/comment",
    response_model=ReelCommentResponse,
    status_code=status.HTTP_201_CREATED
)
async def comment_reel(
    reel_id: int,
    content: Annotated[str, Form(...)],
    db: db_dependency,
    user: user_dependency
):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    reel = db.query(Reel).filter(Reel.id == reel_id).first()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")


    comment = ReelComment(
        reel_id=reel_id,
        user_id=user["id"],
        content=content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)


    comment_with_user = (
        db.query(ReelComment)
        .options(joinedload(ReelComment.user))
        .filter(ReelComment.id == comment.id)
        .first()
    )

    if not comment_with_user or not comment_with_user.user:
        raise HTTPException(status_code=500, detail="Failed to load comment user")


    return ReelCommentResponse(
        id=comment_with_user.id,
        reel_id=comment_with_user.reel_id,
        user_id=comment_with_user.user_id,
        content=comment_with_user.content,
        created_at=comment_with_user.created_at,
        username=comment_with_user.user.username,
        pfp_url=comment_with_user.user.pfp_url
    )


@router.get("/{reel_id}/comments", response_model=list[ReelCommentResponse])
async def get_reel_comments(reel_id: int, db: db_dependency):
    comments = db.query(ReelComment).options(joinedload(ReelComment.user)).filter(ReelComment.reel_id == reel_id).order_by(ReelComment.created_at).all()
    return [
        ReelCommentResponse(
            id=c.id,
            reel_id=c.reel_id,
            user_id=c.user_id,
            content=c.content,
            created_at=c.created_at,
            username=c.user.username if c.user else None,
            pfp_url=c.user.pfp_url if c.user else None
        )
        for c in comments
    ]

