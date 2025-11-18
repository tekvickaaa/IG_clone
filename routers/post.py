from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from typing import Annotated, Optional
from fastapi.params import Form
from database import SessionLocal
from starlette import status
from sqlalchemy.orm import Session, joinedload
from models import Post, PostLike, User, PostMedia
from routers.auth import get_current_user
from schemas import PostResponse
import os
import uuid
from pathlib import Path
from dotenv import load_dotenv

router = APIRouter(
    prefix="/posts",
    tags=["posts"]
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

MAX_IMAGE_SIZE = 20 * 1024 * 1024
MAX_VIDEO_SIZE = 400 * 1024 * 1024
MAX_MEDIA_COUNT = 10


@router.get("/", response_model=list[PostResponse])
async def get_all_posts(db: db_dependency):
    posts = db.query(Post).options(joinedload(Post.user)).all()
    if not posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No posts found")
    return [post for post in posts]


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PostResponse)
async def create_post(db: db_dependency,
                      user: user_dependency,
                      title: str | None = Form(None),
                      description: str | None = Form(None),
                      media: UploadFile = File(...),
                      ):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if not media or not media.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No media provided")

    if media.content_type not in [
        "image/jpeg", "image/png", "image/gif", "video/mp4", "image/webp",
        "image/avif", "image/svg+xml", "video/quicktime", "image/bmp",
        "image/tiff", "image/heic"
    ]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unsupported media type: {media.content_type}")

    user_dir = MEDIA_DIR / str(user["id"])
    user_dir.mkdir(parents=True, exist_ok=True)

    ext = os.path.splitext(media.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = user_dir / unique_name

    try:
        file_size = 0
        max_size = MAX_VIDEO_SIZE if 'video' in media.content_type else MAX_IMAGE_SIZE

        with open(file_path, "wb") as f:
            while chunk := await media.read(1024 * 1024):  # 1MB chunks
                file_size += len(chunk)
                if file_size > max_size:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File too large. Max size: {max_size / (1024 * 1024):.0f}MB"
                    )
                f.write(chunk)

        media_url = f"http://56.228.35.186/media/{user['id']}/{unique_name}"

        new_post = Post(
            user_id=user["id"],
            title=title,
            description=description,
            media_url=media_url,
        )
        db.add(new_post)
        db.flush()

        new_post_media = PostMedia(
            media_url=media_url,
            post_id=new_post.id,
        )
        db.add(new_post_media)

        account = db.query(User).filter(User.id == user["id"]).first()
        account.posts_count += 1

        db.commit()
        db.refresh(new_post)
        return new_post

    except HTTPException:
        if file_path.exists():
            file_path.unlink()
        db.rollback()
        raise

    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading media: {str(e)}"
        )
@router.get("/{post_id}", response_model=PostResponse)
async def get_post(db: db_dependency, post_id: int):
    post = db.query(Post).options(joinedload(Post.user)).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post
@router.delete("/{post_id}")
async def delete_post(db: db_dependency, post_id: int, user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user["id"]).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Post not found or you do not have permission to delete it")

    account = db.query(User).filter(User.id == user["id"]).first()
    account.posts_count -= 1
    db.delete(post)
    db.commit()
    return {"detail": "Post deleted successfully"}
@router.post("/{post_id}/like", status_code=status.HTTP_202_ACCEPTED)
async def like_post(db: db_dependency,
                    post_id: int,
                    user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing_like = db.query(PostLike).filter(PostLike.post_id == post_id, PostLike.user_id == user["id"]).first()
    if existing_like:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already liked this post")

    post.like_count += 1
    post_like = PostLike(
        user_id=user["id"],
        post_id=post_id
    )
    db.add(post_like)
    db.commit()
    db.refresh(post)
@router.post("/{post_id}/comment")
async def comment_post():
    pass