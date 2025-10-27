from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

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
    nickname: Optional[str] = None
    bio: Optional[str] = None
    song_id: Optional[str] = None
    pfp_url: Optional[str] = None
    posts_count: Optional[int] = 0
    followers_count: Optional[int] = 0
    following_count: Optional[int] = 0
    created_at: Optional[datetime] = None

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