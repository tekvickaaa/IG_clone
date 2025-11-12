from sqlalchemy import Column, Integer, Text, String, DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import datetime
from sqlalchemy.sql.sqltypes import Interval, Boolean
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
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    nickname = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)

    bio = Column(Text, nullable=True)
    song_id = Column(String, nullable=True)
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
    stories = relationship("Story", back_populates="user")
    highlights = relationship("Highlight", back_populates="user")
    story_likes = relationship("StoryLike", back_populates="user")
    story_views = relationship("StoryView", back_populates="user")
    post_views = relationship("PostView", back_populates="user")

class Post(Base):
    __tablename__ = "posts"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    media_count = Column(Integer, default=0)
    song_id = Column(Integer, nullable=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    like_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="posts")
    likes = relationship("PostLike", back_populates="post")
    post_views = relationship("PostView", back_populates="post")
    media = relationship("PostMedia", back_populates="post")

class PostLike(Base):
    __tablename__ = "post_likes"
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, primary_key=True)
    liked_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")

class PostView(Base):
    __tablename__ = "post_views"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="post_views")
    post = relationship("Post", back_populates="post_views")

class PostMedia(Base):
   __tablename__ = "post_media"
   post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, primary_key=True)
   media_url = Column(String, nullable=False, primary_key=True)
   created_at = Column(DateTime(timezone=True), server_default=func.now())

   post = relationship("Post", back_populates="media")

class Highlight(Base):
    __tablename__ = "highlights"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    cover_story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="highlights")
    cover_story = relationship("Story", foreign_keys=[cover_story_id], back_populates="cover_highlights")
    stories = relationship("Story", foreign_keys="Story.highlight_id", back_populates="highlight")

class Story(Base):
    __tablename__ = "stories"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    song_id = Column(Integer, nullable=True)
    media_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), server_default=text("NOW() + INTERVAL '1 day'"))
    highlight_id = Column(Integer, ForeignKey("highlights.id"), nullable=True)

    user = relationship("User", back_populates="stories")
    highlight = relationship("Highlight", foreign_keys=[highlight_id], back_populates="stories")
    cover_highlights = relationship("Highlight", foreign_keys="Highlight.cover_story_id", back_populates="cover_story")
    story_likes = relationship("StoryLike", back_populates="story")
    story_views = relationship("StoryView", back_populates="story")

class StoryLike(Base):
    __tablename__ = "story_likes"
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False, primary_key=True)
    liked_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="story_likes")
    story = relationship("Story", back_populates="story_likes")

class StoryView(Base):
    __tablename__ = "story_views"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="story_views")
    story = relationship("Story", back_populates="story_views")