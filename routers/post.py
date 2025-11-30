from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from typing import Annotated, Optional
from fastapi.params import Form
from database import SessionLocal
from starlette import status
from sqlalchemy.orm import Session, joinedload
from models import Post, PostLike, User, PostMedia, PostComment
from routers.auth import get_current_user
from schemas import PostResponse, PostCommentResponse
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


@router.get("/", response_model=list[PostResponse])
async def get_all_posts(db: db_dependency, user: user_dependency):
    posts = (
        db.query(Post)
        .options(joinedload(Post.user))
        .order_by(Post.created_at.desc())
        .all()
    )

    results = []

    for post in posts:
        has_liked = db.query(PostLike).filter(
            PostLike.post_id == post.id,
            PostLike.user_id == user["id"]
        ).first() is not None

        comment_count = db.query(PostComment).filter(
            PostComment.post_id == post.id
        ).count()

        post.has_liked = has_liked
        post.comment_count = comment_count

        results.append(post)

    return results


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PostResponse)
async def create_post(
    db: db_dependency,
    user: user_dependency,
    title: str | None = Form(None),
    description: str | None = Form(None),
    media: UploadFile = File(...)
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not media or not media.filename:
        raise HTTPException(status_code=400, detail="No media provided")

    allowed_media = [
        "image/jpeg", "image/png", "image/gif", "video/mp4", "image/webp",
        "image/avif", "image/svg+xml", "video/quicktime", "image/bmp",
        "image/tiff", "image/heic"
    ]

    if media.content_type not in allowed_media:
        raise HTTPException(status_code=400, detail=f"Unsupported media type: {media.content_type}")

    user_dir = MEDIA_DIR / str(user["id"])
    user_dir.mkdir(parents=True, exist_ok=True)

    ext = os.path.splitext(media.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = user_dir / unique_name

    try:
        file_size = 0
        max_size = MAX_VIDEO_SIZE if "video" in media.content_type else MAX_IMAGE_SIZE

        with open(file_path, "wb") as f:
            while chunk := await media.read(1024 * 1024):
                file_size += len(chunk)
                if file_size > max_size:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Max size: {max_size / (1024 * 1024):.0f}MB"
                    )
                f.write(chunk)

        media_url = f"{BASE_URL}/media/{user['id']}/{unique_name}"

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

        new_post.has_liked = False
        new_post.comment_count = 0

        return new_post

    except:
        if file_path.exists():
            file_path.unlink()
        db.rollback()
        raise


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(db: db_dependency, post_id: int, user: user_dependency):
    post = (
        db.query(Post)
        .options(joinedload(Post.user))
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    has_liked = db.query(PostLike).filter(
        PostLike.post_id == post_id,
        PostLike.user_id == user["id"]
    ).first() is not None

    comment_count = db.query(PostComment).filter(
        PostComment.post_id == post_id
    ).count()

    post.has_liked = has_liked
    post.comment_count = comment_count

    return post


@router.delete("/{post_id}")
async def delete_post(db: db_dependency, post_id: int, user: user_dependency):
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user["id"]).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found or no permission")

    account = db.query(User).filter(User.id == user["id"]).first()
    account.posts_count -= 1

    db.delete(post)
    db.commit()

    return {"detail": "Post deleted successfully"}


@router.post("/{post_id}/like", status_code=status.HTTP_202_ACCEPTED)
async def like_post(db: db_dependency, post_id: int, user: user_dependency):
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing_like = db.query(PostLike).filter(
        PostLike.post_id == post_id,
        PostLike.user_id == user["id"]
    ).first()

    if existing_like:
        raise HTTPException(status_code=400, detail="Already liked")

    post.like_count += 1
    db.add(PostLike(user_id=user["id"], post_id=post_id))
    db.commit()


@router.post("/{post_id}/comment")
async def comment_post(
    post_id: int,
    content: Annotated[str, Form(...)],
    db: db_dependency,
    user: user_dependency
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comment = PostComment(
        post_id=post_id,
        user_id=user["id"],
        content=content
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "user_id": comment.user_id,
        "content": comment.content,
        "created_at": str(comment.created_at)
    }


@router.get("/{post_id}/comments", response_model=list[PostCommentResponse])
async def get_comments(post_id: int, db: db_dependency):
    comments = (
        db.query(PostComment)
        .options(joinedload(PostComment.user))
        .filter(PostComment.post_id == post_id)
        .order_by(PostComment.created_at)
        .all()
    )

    return [
        PostCommentResponse(
            id=c.id,
            post_id=c.post_id,
            user_id=c.user_id,
            content=c.content,
            created_at=c.created_at,
            username=c.user.username
        )
        for c in comments
    ]
