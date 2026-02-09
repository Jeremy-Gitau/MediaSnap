"""Application service layer orchestrating the fetch and save workflow."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime

from mediasnap.core.downloader import MediaDownloader
from mediasnap.core.exceptions import (
    DownloadError,
    ProfileNotFoundError,
    RateLimitedError,
    ScrapingFailedError,
)
from mediasnap.core.scraper import InstagramScraper
from mediasnap.core.youtube_downloader import YouTubeDownloader
from mediasnap.core.linkedin_downloader import LinkedInDownloader
from mediasnap.models.data_models import PostData, ProfileData
from mediasnap.storage.database import get_async_session
from mediasnap.storage.repository import (
    MediaRepository, 
    PostRepository, 
    ProfileRepository,
    DownloadHistoryRepository,
)
from mediasnap.utils.config import DOWNLOAD_DIR
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FetchSummary:
    """Summary of fetch operation."""
    username: str
    profile_id: str
    total_posts_found: int
    new_posts: int
    existing_posts: int
    media_downloaded: int
    media_failed: int
    skipped_posts: int = 0  # Posts skipped (already downloaded)
    errors: list[str]
    success: bool
    download_path: str = ""
    platform: str = "instagram"  # 'instagram', 'youtube', or 'linkedin'


class MediaSnapService:
    """
    Main application service orchestrating profile fetching and media download.
    """
    
    def __init__(self):
        """Initialize service."""
        self.scraper = InstagramScraper()
    
    async def _save_download_history(
        self,
        url: str,
        summary: FetchSummary,
        started_at: datetime,
    ) -> None:
        """
        Save download history to database.
        
        Args:
            url: Original URL/username
            summary: FetchSummary object
            started_at: Download start time
        """
        try:
            async with get_async_session() as session:
                history_data = {
                    'url': url,
                    'platform': summary.platform,
                    'username': summary.username,
                    'total_items': summary.total_posts_found,
                    'new_items': summary.new_posts,
                    'skipped_items': summary.skipped_posts,
                    'failed_items': summary.media_failed,
                    'success': summary.success,
                    'error_message': ', '.join(summary.errors) if summary.errors else None,
                    'download_path': summary.download_path,
                    'started_at': started_at,
                    'completed_at': datetime.utcnow(),
                }
                await DownloadHistoryRepository.create(session, history_data)
                logger.debug(f"Saved download history for {url}")
        except Exception as e:
            logger.error(f"Failed to save download history: {e}")
    
    def _get_folder_for_post(self, post: PostData) -> str:
        """
        Determine the folder name for a post based on its type.
        
        Args:
            post: PostData object
        
        Returns:
            Folder name (reels, carousel, images, or tagged)
        """
        # Check if it's a reel
        if post.typename and "reel" in post.typename.lower():
            return "reels"
        
        # Check if it's a carousel (multiple media items)
        if post.media_items and len(post.media_items) > 1:
            return "carousel"
        
        # Check if it's tagged content (has hashtags in caption)
        if post.caption and "#" in post.caption:
            return "tagged"
        
        # Default: single image/video
        if post.is_video:
            return "reels"
        else:
            return "images"
    
    async def fetch_and_save_profile(
        self,
        username: str,
        progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
    ) -> FetchSummary:
        """
        Fetch profile data and save to database with media download.
        
        This is the main workflow method that:
        1. Fetches profile data from Instagram
        2. Saves/updates profile in database
        3. Identifies new posts
        4. Downloads media for new posts
        5. Returns summary
        
        Args:
            username: Instagram username to fetch
            progress_callback: Optional callback(stage, current, total, message)
        
        Returns:
            FetchSummary object
        """
        started_at = datetime.utcnow()
        errors = []
        
        def report_progress(stage: str, current: int, total: int, message: str = ""):
            """Internal progress reporter."""
            if progress_callback:
                progress_callback(stage, current, total, message)
            logger.debug(f"{stage}: {current}/{total} - {message}")
        
        try:
            # Stage 1: Fetch profile data from Instagram
            report_progress("Fetching", 0, 100, f"Scraping profile: {username}")
            
            try:
                profile_data = await self.scraper.fetch_profile(username)
            except ProfileNotFoundError as e:
                summary = FetchSummary(
                    username=username,
                    profile_id="",
                    total_posts_found=0,
                    new_posts=0,
                    existing_posts=0,
                    media_downloaded=0,
                    media_failed=0,
                    errors=[f"Profile not found: {username}"],
                    success=False,
                )
                await self._save_download_history(username, summary, started_at)
                return summary
            except RateLimitedError as e:
                summary = FetchSummary(
                    username=username,
                    profile_id="",
                    total_posts_found=0,
                    new_posts=0,
                    existing_posts=0,
                    media_downloaded=0,
                    media_failed=0,
                    errors=["Rate limited by Instagram. Please wait and try again later."],
                    success=False,
                )
                await self._save_download_history(username, summary, started_at)
                return summary
            except ScrapingFailedError as e:
                summary = FetchSummary(
                    username=username,
                    profile_id="",
                    total_posts_found=0,
                    new_posts=0,
                    existing_posts=0,
                    media_downloaded=0,
                    media_failed=0,
                    errors=[f"Failed to scrape profile: {str(e)}"],
                    success=False,
                )
                await self._save_download_history(username, summary, started_at)
                return summary
            
            report_progress("Fetching", 20, 100, f"Found {len(profile_data.posts)} posts")
            
            # Stage 2: Save profile and posts to database
            report_progress("Saving", 20, 100, "Saving to database")
            
            async with get_async_session() as session:
                # Upsert profile
                profile_dict = {
                    "instagram_id": profile_data.instagram_id,
                    "username": profile_data.username,
                    "full_name": profile_data.full_name,
                    "biography": profile_data.biography,
                    "profile_pic_url": profile_data.profile_pic_url,
                    "follower_count": profile_data.follower_count,
                    "following_count": profile_data.following_count,
                    "post_count": profile_data.post_count,
                    "is_private": profile_data.is_private,
                    "is_verified": profile_data.is_verified,
                }
                await ProfileRepository.upsert(session, profile_dict)
                
                # Process posts
                new_posts = []
                existing_count = 0
                
                for post_data in profile_data.posts:
                    # Check if post exists
                    existing_post = await PostRepository.get_by_shortcode(
                        session, post_data.shortcode
                    )
                    
                    if existing_post:
                        existing_count += 1
                        continue
                    
                    # Create new post
                    post_dict = {
                        "shortcode": post_data.shortcode,
                        "profile_id": profile_data.instagram_id,
                        "typename": post_data.typename,
                        "caption": post_data.caption,
                        "taken_at": post_data.taken_at,
                        "like_count": post_data.like_count,
                        "comment_count": post_data.comment_count,
                        "display_url": post_data.display_url,
                        "is_video": post_data.is_video,
                        "video_url": post_data.video_url,
                    }
                    await PostRepository.upsert(session, post_dict)
                    
                    # Save media items for carousel posts
                    if post_data.media_items:
                        media_list = [
                            {
                                "post_shortcode": post_data.shortcode,
                                "url": item.url,
                                "media_type": item.media_type,
                                "order": item.order,
                            }
                            for item in post_data.media_items
                        ]
                        await MediaRepository.bulk_insert(session, media_list)
                    
                    new_posts.append(post_data)
            
            report_progress(
                "Saving",
                40,
                100,
                f"Saved {len(new_posts)} new posts ({existing_count} already downloaded)",
            )
            
            # Stage 3: Download media
            if not new_posts:
                logger.info("No new posts to download")
                username_dir = DOWNLOAD_DIR / username
                return FetchSummary(
                    username=username,
                    profile_id=profile_data.instagram_id,
                    total_posts_found=len(profile_data.posts),
                    new_posts=0,
                    existing_posts=existing_count,
                    media_downloaded=0,
                    media_failed=0,
                    errors=[],
                    success=True,
                    download_path=str(username_dir),
                    platform="instagram",
                )
            
            report_progress("Downloading", 40, 100, "Starting media downloads")
            
            # Prepare download list with organized folders
            downloads = []
            username_dir = DOWNLOAD_DIR / username
            username_dir.mkdir(parents=True, exist_ok=True)
            
            for post_data in new_posts:
                # Determine folder based on content type
                folder_name = self._get_folder_for_post(post_data)
                post_dir = username_dir / folder_name
                post_dir.mkdir(parents=True, exist_ok=True)
                
                # Download single media (image/video)
                if post_data.display_url and not post_data.media_items:
                    ext = "mp4" if post_data.is_video else "jpg"
                    url = post_data.video_url if post_data.is_video else post_data.display_url
                    if url:
                        filepath = post_dir / f"{post_data.shortcode}_0.{ext}"
                        downloads.append((url, filepath, post_data.shortcode, None))
                
                # Download carousel media
                for media_item in post_data.media_items:
                    ext = "mp4" if media_item.media_type == "video" else "jpg"
                    filepath = post_dir / f"{post_data.shortcode}_{media_item.order}.{ext}"
                    downloads.append(
                        (media_item.url, filepath, post_data.shortcode, media_item.order)
                    )
            
            # Download with progress tracking
            downloaded_count = 0
            failed_count = 0
            
            async with MediaDownloader() as downloader:
                for idx, (url, filepath, shortcode, order) in enumerate(downloads):
                    try:
                        def download_progress(current: int, total: int, filename: str):
                            progress = 40 + int((idx + (current / total if total > 0 else 0)) / len(downloads) * 50)
                            report_progress(
                                "Downloading",
                                progress,
                                100,
                                f"{filename} ({current}/{total} bytes)",
                            )
                        
                        await downloader.download_media(url, filepath, download_progress)
                        downloaded_count += 1
                        
                        # Update database
                        async with get_async_session() as session:
                            if order is not None:
                                # Update media item
                                media_list = await MediaRepository.get_by_post(session, shortcode)
                                for media in media_list:
                                    if media.order == order:
                                        await MediaRepository.mark_downloaded(
                                            session, media.id, str(filepath)
                                        )
                            else:
                                # Mark post as downloaded
                                await PostRepository.mark_downloaded(session, shortcode)
                        
                    except DownloadError as e:
                        failed_count += 1
                        error_msg = f"Failed to download {filepath.name}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
            
            report_progress("Complete", 100, 100, "Fetch complete!")
            
            summary = FetchSummary(
                username=username,
                profile_id=profile_data.instagram_id,
                total_posts_found=len(profile_data.posts),
                new_posts=len(new_posts),
                existing_posts=existing_count,
                media_downloaded=downloaded_count,
                media_failed=failed_count,
                errors=errors,
                success=True,
                download_path=str(username_dir),
                platform="instagram",
            )
            
            # Save to history
            await self._save_download_history(username, summary, started_at)
            
            return summary
        
        except Exception as e:
            logger.exception(f"Unexpected error in fetch_and_save_profile for {username}")
            summary = FetchSummary(
                username=username,
                profile_id="",
                total_posts_found=0,
                new_posts=0,
                existing_posts=0,
                media_downloaded=0,
                media_failed=0,
                errors=[f"Unexpected error: {str(e)}"],
                success=False,
            )
            await self._save_download_history(username, summary, started_at)
            return summary
    
    async def download_youtube_channel(
        self,
        channel_url: str,
        progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
    ) -> FetchSummary:
        """
        Download all videos from a YouTube channel.
        
        Args:
            channel_url: YouTube channel URL
            progress_callback: Optional callback(stage, current, total, message)
        
        Returns:
            FetchSummary object
        """
        started_at = datetime.utcnow()
        try:
            downloader = YouTubeDownloader()
            result = await downloader.download_channel(channel_url, progress_callback)
            
            summary = FetchSummary(
                username=result["channel_name"],
                profile_id="",
                total_posts_found=result["downloaded"] + result.get("skipped", 0) + result["failed"],
                new_posts=result["downloaded"],
                existing_posts=0,
                skipped_posts=result.get("skipped", 0),
                media_downloaded=result["downloaded"],
                media_failed=result["failed"],
                errors=result.get("failed_videos", []),
                success=result["success"],
                download_path=result["download_path"],
                platform="youtube",
            )
            
            # Save to history
            await self._save_download_history(channel_url, summary, started_at)
            
            return summary
            
        except Exception as e:
            logger.exception(f"YouTube download failed for {channel_url}")
            summary = FetchSummary(
                username=channel_url,
                profile_id="",
                total_posts_found=0,
                new_posts=0,
                existing_posts=0,
                media_downloaded=0,
                media_failed=0,
                errors=[f"YouTube download failed: {str(e)}"],
                success=False,
                platform="youtube",
            )
            await self._save_download_history(channel_url, summary, started_at)
            return summary
    
    async def download_linkedin_profile(
        self,
        profile_url: str,
        progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
    ) -> FetchSummary:
        """
        Download all content from a LinkedIn profile or company page.
        
        Args:
            profile_url: LinkedIn profile or company page URL
            progress_callback: Optional callback(stage, current, total, message)
        
        Returns:
            FetchSummary object
        """
        started_at = datetime.utcnow()
        try:
            downloader = LinkedInDownloader()
            result = await downloader.download_profile(profile_url, progress_callback)
            
            summary = FetchSummary(
                username=result["identifier"],
                profile_id="",
                total_posts_found=result["downloaded"] + result["failed"],
                new_posts=result["downloaded"],
                existing_posts=0,
                media_downloaded=result["downloaded"],
                media_failed=result["failed"],
                errors=result.get("failed_items", []),
                success=result["success"],
                download_path=result["download_path"],
                platform="linkedin",
            )
            
            # Save to history
            await self._save_download_history(profile_url, summary, started_at)
            
            return summary
            
        except Exception as e:
            logger.exception(f"LinkedIn download failed for {profile_url}")
            summary = FetchSummary(
                username=profile_url,
                profile_id="",
                total_posts_found=0,
                new_posts=0,
                existing_posts=0,
                media_downloaded=0,
                media_failed=0,
                errors=[f"LinkedIn download failed: {str(e)}"],
                success=False,
                platform="linkedin",
            )
            await self._save_download_history(profile_url, summary, started_at)
            return summary
