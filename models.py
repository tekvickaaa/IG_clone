from sqlalchemy import Column, Integer, Text, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import datetime
from sqlalchemy.sql.sqltypes import Interval
from database import Base


class Follow(Base):
    __tablename__ = "follows"
    follower_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    following_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    followed_at = Column(DateTime(timezone=True), default=func.now())
    follower = relationship("User", foreign_keys=[follower_id], back_populates="following")
    following = relationship("User", foreign_keys=[following_id], back_populates="followers")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    bio = Column(Text, nullable=True)
    song_id = Column(Integer, nullable=True)
    pfp_url = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    posts_count = Column(Integer, default=0)
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)

    posts = relationship("Post", back_populates="user")
    likes = relationship("PostLike", back_populates="user")
    following = relationship("Follow", foreign_keys=[Follow.follower_id], back_populates="follower")
    followers = relationship("Follow", foreign_keys=[Follow.following_id], back_populates="following")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    media_url = Column(String, nullable=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    like_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="posts")
    likes = relationship("PostLike", back_populates="post")

class PostLike(Base):
    __tablename__ = "post_likes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    liked_at = Column(DateTime(timezone=True), default=func.now())
    __table_args__ = (UniqueConstraint('user_id', 'post_id', name='_user_post_uc'),)
    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")
