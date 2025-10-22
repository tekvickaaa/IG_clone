from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from database import SessionLocal
from starlette import status
from sqlalchemy.orm import Session, joinedload
from models import User, Follow, Post
from schemas import UserResponse, FollowResponse
from routers.auth import get_current_user

router = APIRouter(
    prefix="/user",
    tags=["user"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

@router.get("/", response_model=UserResponse)
async def get_user(db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    account = db.query(User).filter(User.id == user["id"]).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return account

@router.get("/all", response_model=list[UserResponse])
async def get_all_users(db: db_dependency):
    users = db.query(User).all()
    if not users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No users found")
    return users

@router.get("/{id}", response_model=UserResponse)
async def get_user_by_id(id: int, db: db_dependency):
    account = db.query(User).filter(User.id == id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return account

@router.get("/{id}/followers", response_model=list[FollowResponse])
async def get_followers_by_id(id: int, db: db_dependency):
    followers = db.query(Follow).filter(Follow.following_id == id).all()
    if not followers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No followers found for this user")
    return followers

@router.get("/{id}/following", response_model=list[FollowResponse])
async def get_following_by_id(id: int, db: db_dependency):
    following = db.query(Follow).filter(Follow.follower_id == id).all()
    if not following:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No following found for this user")
    return following

@router.post("/{id}/follow", response_model=FollowResponse)
async def follow(db: db_dependency, id: int, user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    account = db.query(User).filter(User.id == id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    follow = db.query(Follow).filter(Follow.follower_id == user["id"], Follow.following_id == id).first()
    if follow:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already following this user")
    new_follow = Follow(
        follower_id=user["id"],
        following_id=id
    )
    db.add(new_follow)
    db.commit()
    db.refresh(new_follow)
    return new_follow

@router.delete("/{id}/follow")
async def unfollow_user(id: int, db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    account = db.query(User).filter(User.id == id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    follow = db.query(Follow).filter(Follow.follower_id == user["id"], Follow.following_id == id).first()
    if not follow:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not following this user")
    db.delete(follow)
    db.commit()
    return {"message": "Unfollowed successfully"}

@router.get("/{id}/posts")
async def get_posts_by_user(id: int, db: db_dependency):
    posts = db.query(Post).options(joinedload(Post.user)).filter(Post.user_id == id).all()
    if not posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No posts found for this user")
    return posts