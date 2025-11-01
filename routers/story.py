from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from typing import Annotated, Optional
from fastapi.params import Form
from database import SessionLocal
from starlette import status
from sqlalchemy.orm import Session, joinedload
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
    pass

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=StoryResponse)
async def create_story(db: db_dependency,
                      user: user_dependency,
                      song_id: str,
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
        media_url = f"/media/{user['id']}/{unique_name}"
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
    following = db.query(Follow)
    stories = db.query(Story).options(joinedload(Story.user)).filter(Story.user_id == user["id"]).all()
    if not stories:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No posts found")
    return [story for story in stories]