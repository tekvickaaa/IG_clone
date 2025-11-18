import os
from pathlib import Path
import uuid
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Annotated
from database import SessionLocal
from starlette import status
from sqlalchemy.orm import Session, joinedload
from models import User, Follow, Post
from schemas import UserResponse, FollowResponse, PostResponse
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

load_dotenv()
MEDIA_DIR = Path(os.getenv("MEDIA_DIR"))
BASE_URL = os.getenv("BASE_URL", "http://56.228.35.186")
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
@router.post("/nickname", response_model=UserResponse)
async def set_nickname(user: user_dependency, db: db_dependency, new_nickname: str):
    user = db.query(User).filter(User.id == user["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not signed in")
    if len(new_nickname) > 32:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bio too long")
    user.nickname = new_nickname
    db.commit()
    return user

@router.post("/bio", response_model=UserResponse)
async def set_bio(user: user_dependency, db: db_dependency, new_bio: str):
    user = db.query(User).filter(User.id == user["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not signed in")
    if len(new_bio) > 255:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bio too long")

    user.bio = new_bio
    db.commit()
    return user

@router.post("/pfp_url", response_model=UserResponse)
async def set_pfp(user: user_dependency, db: db_dependency, media: UploadFile = File(...)):
    if media.content_type not in [
        "image/jpeg", "image/png", "image/gif", "video/mp4", "image/webp",
        "image/avif", "image/svg+xml", "video/quicktime", "image/bmp",
        "image/tiff", "image/heic"
    ]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported media type")
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    user_dir = MEDIA_DIR / str(user["id"])
    user_dir.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(media.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = user_dir / unique_name

    with open(file_path, "wb") as f:
        f.write(await media.read())
    media_url = f"{BASE_URL}/media/{user['id']}/{unique_name}"

    db_user = db.query(User).filter(User.id == user["id"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.pfp_url = media_url
    db.commit()
    db.refresh(db_user)
    return user

@router.post("/song_url", response_model=UserResponse)
async def set_song_id(user: user_dependency, db: db_dependency, new_song: str):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not signed in")
    db_user = db.query(User).filter(User.id == user["id"]).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db_user.song_id = str(new_song)
    db.commit()
    db.refresh(db_user)
    return db_user
@router.get("/test")
async def test_endpoint():
    return {"message": "This a test endpoint for GitHub Webhooks. joj zeby uz? uz?"}
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
    account.followers_count+=1
    active = db.query(User).filter(User.id == user["id"]).first()
    active.following_count += 1
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
    active = db.query(User).filter(User.id == user["id"]).first()
    active.following_count -= 1
    account.followers_count-=1
    db.commit()
    return {"message": "Unfollowed successfully"}

@router.get("/{id}/posts", response_model=list[PostResponse])
async def get_posts_by_user(id: int, db: db_dependency):
    posts = db.query(Post).options(joinedload(Post.user)).filter(Post.user_id == id).all()
    if not posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No posts found for this user")
    return posts