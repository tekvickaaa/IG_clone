from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from typing import Annotated, Optional
from fastapi.params import Form
from database import SessionLocal
from starlette import status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models import Story, StoryLike, User, Follow
from routers.auth import get_current_user
from schemas import FeedStoryResponse, StoryResponse
import os
import uuid
from pathlib import Path
from dotenv import load_dotenv

router = APIRouter(
    prefix="/stories",
    tags=["stories"]
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

@router.get("/", response_model=list[StoryResponse])
async def get_all_stories(db: db_dependency):
    stories = db.query(Story).options(joinedload(Story.user)).all()
    if not stories:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No posts found")
    return stories

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=StoryResponse)
async def create_story(db: db_dependency,
                      user: user_dependency,
                      song_id: int,
                      media: UploadFile = File(...),
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
        media_url = f"http://56.228.35.186/media/{user['id']}/{unique_name}"
    else:
        media_url = None

    new_story = Story(
        user_id=user["id"],
        song_id=song_id,
        media_url=media_url,
    )

    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    return new_story


@router.get("/following", response_model=list[FeedStoryResponse])
async def get_following_stories(db: db_dependency, user: user_dependency):
    following_ids = db.execute(
        select(Follow.following_id).where(Follow.follower_id == user["id"])
    ).scalars().all()

    if not following_ids:
        return []

    stories = db.execute(
        select(Story)
        .options(joinedload(Story.user))
        .where(Story.user_id.in_(following_ids))
        .order_by(Story.created_at.desc())
    ).scalars().all()

    if not stories:
        return []

    story_ids = [story.id for story in stories]
    liked_story_ids = set(
        db.execute(
            select(StoryLike.story_id)
            .where(
                StoryLike.story_id.in_(story_ids),
                StoryLike.user_id == user["id"]
            )
        ).scalars().all()
    )

    return [
        {
            "id": story.id,
            "user_id": story.user_id,
            "media_url": story.media_url,
            "created_at": story.created_at,
            "expires_at": story.expires_at,
            "user": {
                "id": story.user.id,
                "username": story.user.username,
                "pfp_url": story.user.pfp_url
            },
            "has_liked": story.id in liked_story_ids
        }
        for story in stories
    ]
