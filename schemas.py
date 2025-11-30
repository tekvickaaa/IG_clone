from datetime import datetime, timedelta

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, computed_field
from typing import List, Optional
import os

load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://56.228.35.186")

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
class IsFollowingResponse(BaseModel):
    is_following: bool
class PostCommentResponse(BaseModel):
    id: int
    post_id: int
    user_id: int
    content: str
    created_at: datetime
    username: str  

    class Config:
        orm_mode = True

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



class UserShortResponse(BaseModel):
    id: int
    username: str
    pfp_url: Optional[str] = None

    @computed_field
    @property
    def full_pfp_url(self) -> str | None:
        if self.pfp_url:
            if self.pfp_url.startswith("http"):
                return self.pfp_url
            return f"{BASE_URL}{self.pfp_url}"
        return None

    class Config:
        from_attributes = True


class PostResponse(BaseSchema):
    id: int
    user_id: int
    media_url: str
    title: Optional[str] = None
    description: Optional[str] = None
    like_count: int
    created_at: datetime
    user: Optional[UserShortResponse] = None
    has_liked: bool = False
    comment_count: int = 0

    @computed_field
    @property
    def full_media_url(self) -> str | None:
        if self.media_url:
            if self.media_url.startswith('http'):
                return self.media_url
            return f"{BASE_URL}{self.media_url}"
        return None

class FeedStoryResponse(BaseSchema):
    id: int
    user_id: int
    media_url: str
    has_liked: bool
    created_at: datetime
    expires_at: datetime
    has_seen: bool  
    user: Optional[UserShortResponse] = None

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
    

class ReelCommentResponse(BaseModel):
    id: int
    reel_id: int
    user_id: int
    content: str
    created_at: datetime
    username: Optional[str] = None
    pfp_url: Optional[str] = None  

  

    class Config:
        orm_mode = True

class ReelResponse(BaseModel):
    id: int
    user_id: int
    description: Optional[str]
    video_url: str
    like_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: Optional[dict] = None

    class Config:
        orm_mode = True

class ReelListItem(BaseModel):
    id: int
    user_id: int
    description: Optional[str]
    video_url: Optional[str]
    like_count: int
    comment_count: int
    created_at: datetime
    user: Optional[dict] = None

    class Config:
        orm_mode = True

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    type: str
    read: bool
    sent_at: datetime

    class Config:
        from_attributes = True
