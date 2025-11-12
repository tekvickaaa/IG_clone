from datetime import datetime, timedelta

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, computed_field
from typing import List, Optional
import os

load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://56.228.35.186")

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class CreateUserRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    pfp_url: Optional[str] = None
    nickname: Optional[str] = None
    bio: Optional[str] = None
    song_id: Optional[str] = None

    @computed_field
    @property
    def full_pfp_url(self) -> str | None:
        if self.pfp_url:
            if self.pfp_url.startswith('http'):
                return self.pfp_url
            return f"{BASE_URL}{self.pfp_url}"
        return None

    posts_count: Optional[int] = 0
    followers_count: Optional[int] = 0
    following_count: Optional[int] = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class FollowResponse(BaseSchema):
    follower_id: int
    following_id: int
    followed_at: datetime

class PostResponse(BaseSchema):
    id: int
    user_id: int
    media_url: str
    title: Optional[str] = None
    description: Optional[str] = None
    like_count: int
    created_at: datetime

    @computed_field
    @property
    def full_media_url(self) -> str | None:
        if self.media_url:
            if self.media_url.startswith('http'):
                return self.media_url
            return f"{BASE_URL}{self.media_url}"
        return None

    class Config:
        from_attributes = True


class FeedStoryResponse(BaseSchema):
    id: int
    user_id: int
    media_url: str
    has_liked: bool
    created_at: datetime
    expires_at: datetime


class StoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    highlight_id: Optional[int] = None
    user_id: int
    media_url: str
    created_at: datetime
    expires_at: datetime

    @computed_field
    @property
    def full_media_url(self) -> str | None:
        if self.media_url:
            if self.media_url.startswith('http'):
                return self.media_url
            return f"{BASE_URL}{self.media_url}"
        return None