"""Instaloader-based scraper for Instagram profiles."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

import instaloader

from mediasnap.core.exceptions import (
    ProfileNotFoundError,
    RateLimitedError,
    ScrapingFailedError,
)
from mediasnap.models.data_models import MediaItem, PostData, ProfileData
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


class InstaloaderScraper:
    """Scraper using instaloader library."""
    
    def __init__(self, session_file: Optional[str] = None):
        """
        Initialize instaloader.
        
        Args:
            session_file: Path to session file for authenticated requests (optional)
        """
        self.loader = instaloader.Instaloader(
            download_pictures=False,  # We'll handle downloads ourselves
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=False,  # Show retry messages to help debug
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            max_connection_attempts=3,  # Reduce retry attempts
        )
        
        # Load session if provided
        if session_file and Path(session_file).exists():
            try:
                self.loader.load_session_from_file(session_file)
                logger.info("Loaded Instagram session from file")
            except Exception as e:
                logger.warning(f"Failed to load session file: {e}")
    
    async def fetch_profile(self, username: str) -> ProfileData:
        """
        Fetch profile data using instaloader.
        
        Args:
            username: Instagram username
        
        Returns:
            ProfileData object
        
        Raises:
            ProfileNotFoundError: If profile doesn't exist
            RateLimitedError: If rate limited
            ScrapingFailedError: If scraping fails
        """
        logger.info(f"Fetching profile with instaloader: {username}")
        
        try:
            # Run instaloader in thread pool since it's blocking
            profile = await asyncio.to_thread(
                instaloader.Profile.from_username,
                self.loader.context,
                username
            )
            
            logger.debug(f"Profile loaded: {profile.username}")
            
            # Convert to our ProfileData format
            profile_data = ProfileData(
                instagram_id=str(profile.userid),
                username=profile.username,
                full_name=profile.full_name,
                biography=profile.biography,
                profile_pic_url=profile.profile_pic_url,
                follower_count=profile.followers,
                following_count=profile.followees,
                post_count=profile.mediacount,
                is_private=profile.is_private,
                is_verified=profile.is_verified,
            )
            
            logger.info(f"Fetching posts for {username}...")
            
            # Get posts
            posts = []
            post_count = 0
            max_posts = 50  # Limit to first 50 posts for performance
            
            # Fetch posts in thread pool
            for post in await asyncio.to_thread(self._get_posts, profile, max_posts):
                posts.append(post)
                post_count += 1
                if post_count % 10 == 0:
                    logger.debug(f"Fetched {post_count} posts...")
            
            profile_data.posts = posts
            
            logger.info(f"Successfully fetched {username}: {len(posts)} posts")
            return profile_data
            
        except instaloader.exceptions.ProfileNotExistsException:
            raise ProfileNotFoundError(f"Profile not found: {username}")
        
        except instaloader.exceptions.PrivateProfileNotFollowedException:
            raise ProfileNotFoundError(
                f"Profile {username} is private. MediaSnap only works with public profiles."
            )
        
        except instaloader.exceptions.ConnectionException as e:
            error_msg = str(e).lower()
            if "403" in error_msg or "forbidden" in error_msg:
                raise ScrapingFailedError(
                    "Instagram blocked the request (403 Forbidden). "
                    "This usually means Instagram is blocking unauthenticated scraping. "
                    "Solutions:\n"
                    "1. Wait 10-15 minutes and try again\n"
                    "2. Try a different profile\n"
                    "3. Login with Instagram credentials (see README for instructions)\n"
                    "Instagram has become very strict about blocking automated access."
                )
            elif "429" in error_msg or "rate" in error_msg:
                raise RateLimitedError(
                    "Rate limited by Instagram. Please wait 10-15 minutes and try again."
                )
            elif "login" in error_msg or "logged" in error_msg:
                raise ScrapingFailedError(
                    "Instagram requires login for this profile. "
                    "Try a different public profile or wait and retry."
                )
            else:
                raise ScrapingFailedError(f"Connection error: {str(e)}")
        
        except instaloader.exceptions.QueryReturnedNotFoundException:
            raise ProfileNotFoundError(f"Profile not found: {username}")
        
        except Exception as e:
            logger.exception(f"Unexpected error fetching {username}")
            raise ScrapingFailedError(f"Unexpected error: {str(e)}")
    
    def _get_posts(self, profile: instaloader.Profile, max_posts: int) -> list:
        """
        Get posts from profile (blocking operation).
        
        Args:
            profile: Instaloader Profile object
            max_posts: Maximum posts to fetch
        
        Returns:
            List of PostData objects
        """
        posts = []
        
        try:
            for post in profile.get_posts():
                if len(posts) >= max_posts:
                    break
                
                try:
                    post_data = self._parse_post(post)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.warning(f"Failed to parse post {post.shortcode}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error fetching posts: {e}")
        
        return posts
    
    def _parse_post(self, post: instaloader.Post) -> Optional[PostData]:
        """
        Parse instaloader Post into PostData.
        
        Args:
            post: Instaloader Post object
        
        Returns:
            PostData object or None
        """
        try:
            # Convert timestamp to datetime
            taken_at = datetime.fromtimestamp(post.date_utc.timestamp())
            
            # Create post data
            post_data = PostData(
                shortcode=post.shortcode,
                typename=post.typename,
                caption=post.caption if post.caption else None,
                taken_at=taken_at,
                like_count=post.likes,
                comment_count=post.comments,
                display_url=post.url,
                is_video=post.is_video,
                video_url=post.video_url if post.is_video else None,
            )
            
            # Handle carousel/sidecar posts (multiple media items)
            if post.typename == "GraphSidecar":
                media_items = []
                for idx, node in enumerate(post.get_sidecar_nodes()):
                    media_item = MediaItem(
                        url=node.video_url if node.is_video else node.display_url,
                        media_type="video" if node.is_video else "image",
                        order=idx,
                    )
                    media_items.append(media_item)
                post_data.media_items = media_items
            
            return post_data
            
        except Exception as e:
            logger.warning(f"Failed to parse post: {e}")
            return None
