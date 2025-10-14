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
    bio: Optional[str] = None
    pfp_url: str | None = None
    song_id: int | None = None
    posts_count: int
    followers_count: int
    following_count: int

class FollowResponse(BaseSchema):
    follower_id: int
    following_id: int
    followed_at: datetime