"""Facebook profile scraper using facebook-scraper library."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
import re

from mediasnap.models.data_models import MediaItem, PostData, ProfileData
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


class FacebookScraper:
    """
    Facebook scraper using facebook-scraper library.
    
    Note: Works with public Facebook profiles and pages.
    Private profiles require being friends with the user.
    """
    
    def __init__(self):
        """Initialize Facebook scraper."""
        self.scraper_available = self._check_facebook_scraper()
    
    def _check_facebook_scraper(self) -> bool:
        """Check if facebook-scraper is installed."""
        try:
            import facebook_scraper
            return True
        except ImportError:
            return False
    
    def _extract_username(self, url: str) -> str:
        """Extract username from Facebook URL."""
        # Remove protocol and www
        url = re.sub(r'https?://(www\.)?', '', url)
        
        # Handle fb.com and facebook.com
        url = url.replace('fb.com/', 'facebook.com/')
        
        # Extract username/page_id
        match = re.search(r'facebook\.com/([^/?]+)', url)
        if match:
            return match.group(1)
        
        return url.strip('/')
    
    async def fetch_profile(self, url_or_username: str, max_posts: int = 50) -> ProfileData:
        """
        Fetch Facebook profile data.
        
        Args:
            url_or_username: Facebook URL or username
            max_posts: Maximum number of posts to fetch (default 50)
        
        Returns:
            ProfileData object
        
        Raises:
            Exception: If scraping fails
        """
        if not self.scraper_available:
            raise Exception(
                "facebook-scraper not installed. "
                "Install with: pip install facebook-scraper"
            )
        
        # Extract username from URL
        username = self._extract_username(url_or_username)
        logger.info(f"Fetching Facebook profile: {username}")
        
        try:
            from facebook_scraper import get_posts, get_profile
            
            # Try to get profile info
            try:
                profile_info = await asyncio.to_thread(get_profile, username)
                full_name = profile_info.get('Name', username)
                about = profile_info.get('About', '')
                followers = profile_info.get('Followers', 0)
                logger.info(f"📘 Found profile: {full_name}")
            except Exception as e:
                logger.warning(f"Could not fetch profile info: {e}")
                full_name = username
                about = ""
                followers = 0
            
            # Create profile data
            profile_data = ProfileData(
                instagram_id=f"fb_{username}",
                username=username,
                full_name=full_name,
                biography=about,
                profile_pic_url="",
                follower_count=followers,
                following_count=0,
                post_count=0,
                is_private=False,
                is_verified=False,
            )
            
            # Fetch posts
            logger.info(f"Fetching posts from {username}...")
            posts = []
            post_count = 0
            
            try:
                for post in get_posts(username, pages=5):  # Fetch 5 pages
                    if post_count >= max_posts:
                        break
                    
                    # Extract media
                    media_items = []
                    
                    # Check for images
                    if post.get('images'):
                        for idx, img_url in enumerate(post['images']):
                            media_items.append(MediaItem(
                                url=img_url,
                                media_type='image',
                                order=idx
                            ))
                    
                    # Check for video
                    if post.get('video'):
                        media_items.append(MediaItem(
                            url=post['video'],
                            media_type='video',
                            order=0
                        ))
                    
                    # Create post data
                    post_data = PostData(
                        shortcode=post.get('post_id', f"fb_{post_count}"),
                        timestamp=post.get('time', datetime.now()),
                        is_video=bool(post.get('video')),
                        caption=post.get('text', ''),
                        likes=post.get('likes', 0),
                        comments=post.get('comments', 0),
                        media_items=media_items,
                    )
                    
                    posts.append(post_data)
                    post_count += 1
                    
                    if post_count % 10 == 0:
                        logger.debug(f"Fetched {post_count} posts...")
                
                logger.info(f"✓ Successfully fetched {len(posts)} posts from {username}")
                
            except Exception as e:
                logger.error(f"Error fetching posts: {e}")
                logger.info("Fetched posts so far will be processed")
            
            profile_data.posts = posts
            profile_data.post_count = len(posts)
            
            return profile_data
            
        except Exception as e:
            logger.exception(f"Facebook scraping failed for {username}")
            raise Exception(f"Failed to fetch Facebook profile: {str(e)}")
