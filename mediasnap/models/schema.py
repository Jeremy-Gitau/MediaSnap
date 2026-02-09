"""SQLAlchemy ORM models for MediaSnap."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    BigInteger,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Profile(Base):
    """Instagram profile/user model."""
    
    __tablename__ = "profiles"
    
    # Primary key: Instagram's user ID (immutable)
    instagram_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Profile information
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    biography: Mapped[Optional[str]] = mapped_column(Text)
    profile_pic_url: Mapped[Optional[str]] = mapped_column(Text)
    
    # Counts
    follower_count: Mapped[Optional[int]] = mapped_column(Integer)
    following_count: Mapped[Optional[int]] = mapped_column(Integer)
    post_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Flags
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metadata
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    posts: Mapped[List["Post"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Profile(username='{self.username}', id='{self.instagram_id}')>"


class Post(Base):
    """Instagram post model."""
    
    __tablename__ = "posts"
    
    # Primary key: Instagram's shortcode (unique identifier for posts)
    shortcode: Mapped[str] = mapped_column(String(20), primary_key=True)
    
    # Foreign key to profile
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.instagram_id"), nullable=False, index=True)
    
    # Post metadata
    typename: Mapped[Optional[str]] = mapped_column(String(50))  # GraphImage, GraphVideo, GraphSidecar
    caption: Mapped[Optional[str]] = mapped_column(Text)
    taken_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Engagement metrics
    like_count: Mapped[Optional[int]] = mapped_column(Integer)
    comment_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Media information (for single image/video posts)
    display_url: Mapped[Optional[str]] = mapped_column(Text)
    is_video: Mapped[bool] = mapped_column(Boolean, default=False)
    video_url: Mapped[Optional[str]] = mapped_column(Text)
    
    # Download tracking
    is_downloaded: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    profile: Mapped["Profile"] = relationship(back_populates="posts")
    media: Mapped[List["Media"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Post(shortcode='{self.shortcode}', profile='{self.profile_id}')>"


class Media(Base):
    """Media assets for carousel posts (albums with multiple images/videos)."""
    
    __tablename__ = "media"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to post
    post_shortcode: Mapped[str] = mapped_column(ForeignKey("posts.shortcode"), nullable=False, index=True)
    
    # Media information
    url: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str] = mapped_column(String(20))  # 'image' or 'video'
    order: Mapped[int] = mapped_column(Integer, default=0)  # Position in carousel
    
    # Local storage
    local_path: Mapped[Optional[str]] = mapped_column(Text)
    is_downloaded: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    post: Mapped["Post"] = relationship(back_populates="media")
    
    def __repr__(self) -> str:
        return f"<Media(id={self.id}, post='{self.post_shortcode}', type='{self.media_type}')>"
