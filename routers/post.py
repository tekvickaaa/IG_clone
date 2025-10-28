from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from typing import Annotated, Optional
from fastapi.params import Form
from database import SessionLocal
from starlette import status
from sqlalchemy.orm import Session, joinedload
from models import Post, PostLike, User
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
MEDIA_DIR = Path(os.getenv("MEDIA_DIR"))


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
                      media: Optional[UploadFile] = File(None)
                      ):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if not media or not getattr(media, 'filename'):
        media_url = None
    if media:
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
        media_url = f"/media/{user['id']}/{unique_name}"
    else:
        media_url = None

    new_post = Post(
        user_id=user["id"],
        title=title,
        description=description,
        media_url=media_url,
    )

    db.add(new_post)
    account = db.query(User).filter(User.id == user["id"]).first()
    account.posts_count+=1
    db.commit()
    db.refresh(new_post)
    return new_post


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