from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from typing import Annotated, Optional
from fastapi.params import Form
from database import SessionLocal
from starlette import status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models import Story, StoryLike, StoryView, User, Follow
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
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

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

    seen_story_ids = set(
        db.execute(
            select(StoryView.story_id)
            .where(
                StoryView.story_id.in_(story_ids),
                StoryView.user_id == user["id"]
            )
        ).scalars().all()
    )

    story_list = [
        {
            "id": story.id,
            "user_id": story.user_id,
            "media_url": story.media_url if story.media_url and story.media_url.startswith('http') else f"{BASE_URL}{story.media_url}" if story.media_url else None,
            "created_at": story.created_at,
            "expires_at": story.expires_at,
            "user": {
                "id": story.user.id,
                "username": story.user.username,
                "pfp_url": story.user.pfp_url
            },
            "has_liked": story.id in liked_story_ids,
            "has_seen": story.id in seen_story_ids
        }
        for story in stories
    ]

    story_list.sort(key=lambda x: (x["has_seen"], x["expires_at"]), reverse=True)

    return story_list


@router.post("/{story_id}/like")
async def like_story(story_id: int, db: db_dependency, user: user_dependency):
  
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    existing_like = db.query(StoryLike).filter(
        StoryLike.story_id == story_id,
        StoryLike.user_id == user["id"]
    ).first()

    if existing_like:
   
        db.delete(existing_like)
        db.commit()
        return {"message": "Story unliked"}
    else:
        
        new_like = StoryLike(user_id=user["id"], story_id=story_id)
        db.add(new_like)
        db.commit()
        db.refresh(new_like)
        return {"message": "Story liked"}
    
@router.post("/{story_id}/seen")
async def mark_story_seen(story_id: int, db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    
    existing_view = db.query(StoryView).filter(
        StoryView.story_id == story_id,
        StoryView.user_id == user["id"]
    ).first()

    if existing_view:
        return {"message": "Story already seen"}

    new_view = StoryView(user_id=user["id"], story_id=story_id)
    db.add(new_view)
    db.commit()
    db.refresh(new_view)
    return {"message": "Story marked as seen"}


@router.delete("/{story_id}", status_code=200)
async def delete_story(story_id: int, db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    if story.media_url:
        try:
            path = story.media_url.replace(f"{BASE_URL}/", "")
            abs_path = BASE_DIR / path
            if abs_path.exists():
                abs_path.unlink()
        except:
            pass

    db.delete(story)
    db.commit()
    return {"message": "Story deleted successfully"}