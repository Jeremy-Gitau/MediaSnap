"""Data models for scraped Instagram data."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class MediaItem:
    """Represents a single media item (image or video)."""
    url: str
    media_type: str  # 'image' or 'video'
    order: int = 0


@dataclass
class PostData:
    """Represents an Instagram post."""
    shortcode: str
    typename: str
    caption: Optional[str] = None
    taken_at: Optional[datetime] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    display_url: Optional[str] = None
    is_video: bool = False
    video_url: Optional[str] = None
    media_items: List[MediaItem] = field(default_factory=list)


@dataclass
class ProfileData:
    """Represents an Instagram profile."""
    instagram_id: str
    username: str
    full_name: Optional[str] = None
    biography: Optional[str] = None
    profile_pic_url: Optional[str] = None
    follower_count: Optional[int] = None
    following_count: Optional[int] = None
    post_count: Optional[int] = None
    is_private: bool = False
    is_verified: bool = False
    posts: List[PostData] = field(default_factory=list)
