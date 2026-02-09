"""Repository layer for database operations."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from mediasnap.models.schema import Media, Post, Profile
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


class ProfileRepository:
    """Repository for Profile operations."""
    
    @staticmethod
    async def upsert(session: AsyncSession, profile_data: dict) -> Profile:
        """
        Insert or update a profile.
        
        Args:
            session: Database session
            profile_data: Profile data dictionary
        
        Returns:
            Profile instance
        """
        instagram_id = profile_data.get("instagram_id")
        
        # Try to fetch existing profile
        result = await session.execute(
            select(Profile).where(Profile.instagram_id == instagram_id)
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            # Update existing profile
            for key, value in profile_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            profile.fetched_at = datetime.utcnow()
            logger.debug(f"Updated profile: {profile.username}")
        else:
            # Create new profile
            profile = Profile(**profile_data)
            session.add(profile)
            logger.debug(f"Created new profile: {profile.username}")
        
        await session.flush()
        return profile
    
    @staticmethod
    async def get_by_username(session: AsyncSession, username: str) -> Optional[Profile]:
        """
        Get profile by username.
        
        Args:
            session: Database session
            username: Instagram username
        
        Returns:
            Profile instance or None
        """
        result = await session.execute(
            select(Profile).where(Profile.username == username)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_id(session: AsyncSession, instagram_id: str) -> Optional[Profile]:
        """
        Get profile by Instagram ID.
        
        Args:
            session: Database session
            instagram_id: Instagram user ID
        
        Returns:
            Profile instance or None
        """
        result = await session.execute(
            select(Profile).where(Profile.instagram_id == instagram_id)
        )
        return result.scalar_one_or_none()


class PostRepository:
    """Repository for Post operations."""
    
    @staticmethod
    async def upsert(session: AsyncSession, post_data: dict) -> Post:
        """
        Insert or update a post.
        
        Args:
            session: Database session
            post_data: Post data dictionary
        
        Returns:
            Post instance
        """
        shortcode = post_data.get("shortcode")
        
        # Try to fetch existing post
        result = await session.execute(
            select(Post).where(Post.shortcode == shortcode)
        )
        post = result.scalar_one_or_none()
        
        if post:
            # Update existing post (mainly engagement counts)
            for key, value in post_data.items():
                if hasattr(post, key) and key not in ["shortcode", "created_at"]:
                    setattr(post, key, value)
            logger.debug(f"Updated post: {shortcode}")
        else:
            # Create new post
            post = Post(**post_data)
            session.add(post)
            logger.debug(f"Created new post: {shortcode}")
        
        await session.flush()
        return post
    
    @staticmethod
    async def get_by_shortcode(session: AsyncSession, shortcode: str) -> Optional[Post]:
        """
        Get post by shortcode.
        
        Args:
            session: Database session
            shortcode: Instagram post shortcode
        
        Returns:
            Post instance or None
        """
        result = await session.execute(
            select(Post).where(Post.shortcode == shortcode)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_undownloaded(session: AsyncSession, profile_id: str) -> List[Post]:
        """
        Get all posts that haven't been downloaded yet.
        
        Args:
            session: Database session
            profile_id: Instagram user ID
        
        Returns:
            List of Post instances
        """
        result = await session.execute(
            select(Post)
            .where(Post.profile_id == profile_id)
            .where(Post.is_downloaded == False)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def mark_downloaded(session: AsyncSession, shortcode: str) -> None:
        """
        Mark a post as downloaded.
        
        Args:
            session: Database session
            shortcode: Instagram post shortcode
        """
        await session.execute(
            update(Post)
            .where(Post.shortcode == shortcode)
            .values(is_downloaded=True)
        )
        await session.flush()
        logger.debug(f"Marked post as downloaded: {shortcode}")
    
    @staticmethod
    async def get_by_profile(session: AsyncSession, profile_id: str) -> List[Post]:
        """
        Get all posts for a profile.
        
        Args:
            session: Database session
            profile_id: Instagram user ID
        
        Returns:
            List of Post instances
        """
        result = await session.execute(
            select(Post)
            .where(Post.profile_id == profile_id)
            .order_by(Post.taken_at.desc())
        )
        return list(result.scalars().all())


class MediaRepository:
    """Repository for Media operations."""
    
    @staticmethod
    async def bulk_insert(session: AsyncSession, media_list: List[dict]) -> List[Media]:
        """
        Insert multiple media items.
        
        Args:
            session: Database session
            media_list: List of media data dictionaries
        
        Returns:
            List of created Media instances
        """
        media_objects = []
        for media_data in media_list:
            media = Media(**media_data)
            session.add(media)
            media_objects.append(media)
        
        await session.flush()
        logger.debug(f"Inserted {len(media_objects)} media items")
        return media_objects
    
    @staticmethod
    async def mark_downloaded(session: AsyncSession, media_id: int, local_path: str) -> None:
        """
        Mark media as downloaded and set local path.
        
        Args:
            session: Database session
            media_id: Media ID
            local_path: Path where media was saved
        """
        await session.execute(
            update(Media)
            .where(Media.id == media_id)
            .values(is_downloaded=True, local_path=local_path)
        )
        await session.flush()
        logger.debug(f"Marked media as downloaded: {media_id} -> {local_path}")
    
    @staticmethod
    async def get_by_post(session: AsyncSession, post_shortcode: str) -> List[Media]:
        """
        Get all media for a post.
        
        Args:
            session: Database session
            post_shortcode: Instagram post shortcode
        
        Returns:
            List of Media instances
        """
        result = await session.execute(
            select(Media)
            .where(Media.post_shortcode == post_shortcode)
            .order_by(Media.order)
        )
        return list(result.scalars().all())
