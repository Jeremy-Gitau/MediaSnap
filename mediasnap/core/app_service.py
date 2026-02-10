"""Application service layer orchestrating the fetch and save workflow."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime

from mediasnap.core.downloader import MediaDownloader
from mediasnap.core.download_controller import DownloadController
from mediasnap.core.exceptions import (
    DownloadError,
    ProfileNotFoundError,
    RateLimitedError,
    ScrapingFailedError,
)
from mediasnap.core.scraper import InstagramScraper
from mediasnap.core.youtube_downloader import YouTubeDownloader
from mediasnap.core.linkedin_downloader import LinkedInDownloader
from mediasnap.core.facebook_scraper import FacebookScraper
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
    errors: list[str] = None
    success: bool = False
    skipped_posts: int = 0  # Posts skipped (already downloaded)
    download_path: str = ""
    platform: str = "instagram"  # 'instagram', 'youtube', or 'linkedin'
    
    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.errors is None:
            self.errors = []


class MediaSnapService:
    """
    Main application service orchestrating profile fetching and media download.
    """
    
    def __init__(self):
        """Initialize service."""
        self.scraper = InstagramScraper()
        self.facebook_scraper = FacebookScraper()
    
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
        controller: Optional[DownloadController] = None,
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
        
        # Create controller if not provided
        if controller is None:
            controller = DownloadController()
        
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
                        # Check if paused or cancelled
                        await controller.wait_if_paused()
                        controller.check_cancelled()
                        
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
            
            controller.complete()
            return summary
        
        except asyncio.CancelledError:
            logger.info(f"Download cancelled for {username}")
            summary = FetchSummary(
                username=username,
                profile_id="",
                total_posts_found=0,
                new_posts=0,
                existing_posts=0,
                media_downloaded=0,
                media_failed=0,
                errors=["Download cancelled by user"],
                success=False,
            )
            controller.cancel()
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
            controller.fail()
            await self._save_download_history(username, summary, started_at)
            return summary
    
    async def download_youtube_channel(
        self,
        channel_url: str,
        progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
        controller: Optional[DownloadController] = None,
    ) -> FetchSummary:
        """
        Download all videos from a YouTube channel.
        
        Args:
            channel_url: YouTube channel URL
            progress_callback: Optional callback(stage, current, total, message)
            controller: Optional download controller for pause/resume/cancel
        
        Returns:
            FetchSummary object
        """
        started_at = datetime.utcnow()
        
        # Create controller if not provided
        if controller is None:
            controller = DownloadController()
        
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
            
            controller.complete()
            return summary
        
        except asyncio.CancelledError:
            logger.info(f"YouTube download cancelled for {channel_url}")
            summary = FetchSummary(
                username=channel_url,
                profile_id="",
                total_posts_found=0,
                new_posts=0,
                existing_posts=0,
                media_downloaded=0,
                media_failed=0,
                errors=["Download cancelled by user"],
                success=False,
                platform="youtube",
            )
            controller.cancel()
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
            controller.fail()
            await self._save_download_history(channel_url, summary, started_at)
            return summary
    
    async def download_linkedin_profile(
        self,
        profile_url: str,
        progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
        controller: Optional[DownloadController] = None,
    ) -> FetchSummary:
        """
        Download all content from a LinkedIn profile or company page.
        
        Args:
            profile_url: LinkedIn profile or company page URL
            progress_callback: Optional callback(stage, current, total, message)
            controller: Optional download controller for pause/resume/cancel
        
        Returns:
            FetchSummary object
        """
        started_at = datetime.utcnow()
        
        # Create controller if not provided
        if controller is None:
            controller = DownloadController()
        
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
            
            controller.complete()
            return summary
        
        except asyncio.CancelledError:
            logger.info(f"LinkedIn download cancelled for {profile_url}")
            summary = FetchSummary(
                username=profile_url,
                profile_id="",
                total_posts_found=0,
                new_posts=0,
                existing_posts=0,
                media_downloaded=0,
                media_failed=0,
                errors=["Download cancelled by user"],
                success=False,
                platform="linkedin",
            )
            controller.cancel()
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
            controller.fail()
    
    async def download_facebook_profile(
        self,
        profile_url: str,
        progress_callback: Callable[[str, int, int, str], None],
        controller: Optional[DownloadController] = None,
    ) -> FetchSummary:
        """
        Download Facebook profile posts and media.
        
        Args:
            profile_url: Facebook profile URL or username
            progress_callback: Callback for progress updates
            controller: Optional download controller for pause/cancel
        
        Returns:
            FetchSummary with download results
        """
        started_at = datetime.utcnow()
        
        try:
            # Fetch profile data
            progress_callback("Fetching", 0, 100, "Fetching Facebook profile...")
            profile = await self.facebook_scraper.fetch_profile(profile_url, max_posts=50)
            
            # Progress: fetched profile
            progress_callback("Processing", 20, 100, f"Found {len(profile.posts)} posts")
            
            # Create download directory
            username = profile.username
            download_path = DOWNLOAD_DIR / "facebook" / username
            download_path.mkdir(parents=True, exist_ok=True)
            
            # Download media from posts
            media_downloaded = 0
            media_failed = 0
            
            total_posts = len(profile.posts)
            
            for idx, post in enumerate(profile.posts):
                # Check for cancellation
                if controller and controller.is_cancelled():
                    logger.info("Download cancelled by user")
                    break
                
                # Check for pause
                while controller and controller.is_paused():
                    await asyncio.sleep(0.5)
                
                # Create folder structure
                post_type = "videos" if post.is_video else "photos"
                post_folder = download_path / post_type
                post_folder.mkdir(exist_ok=True)
                
                # Download media
                for media in post.media_items:
                    try:
                        # Download logic here
                        filename = f"{post.shortcode}_{media.order}.{'mp4' if media.media_type == 'video' else 'jpg'}"
                        file_path = post_folder / filename
                        
                        if not file_path.exists():
                            # Use downloader to fetch media
                            downloader = MediaDownloader()
                            await downloader.download_media(media.url, str(file_path))
                            media_downloaded += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to download media: {e}")
                        media_failed += 1
                
                # Update progress
                progress = int(((idx + 1) / total_posts) * 80) + 20
                progress_callback(
                    "Downloading",
                    progress,
                    100,
                    f"Downloaded {media_downloaded} items from {idx + 1}/{total_posts} posts"
                )
            
            # Create summary
            summary = FetchSummary(
                username=username,
                profile_id=profile.instagram_id,
                total_posts_found=total_posts,
                new_posts=total_posts,
                existing_posts=0,
                media_downloaded=media_downloaded,
                media_failed=media_failed,
                success=True,
                download_path=str(download_path),
                platform="facebook",
            )
            
            # Save history
            await self._save_download_history(profile_url, summary, started_at)
            
            progress_callback("Complete", 100, 100, f"✓ Downloaded {media_downloaded} items!")
            
            controller.complete()
            return summary
            
        except asyncio.CancelledError:
            logger.info("Facebook download cancelled")
            summary = FetchSummary(
                username=profile_url,
                profile_id="unknown",
                total_posts_found=0,
                new_posts=0,
                existing_posts=0,
                media_downloaded=0,
                media_failed=0,
                success=False,
                errors=["Download cancelled by user"],
                platform="facebook",
            )
            controller.cancel()
            await self._save_download_history(profile_url, summary, started_at)
            return summary
        except Exception as e:
            logger.exception(f"Facebook download failed: {e}")
            summary = FetchSummary(
                username=profile_url,
                profile_id="unknown",
                total_posts_found=0,
                new_posts=0,
                existing_posts=0,
                media_downloaded=0,
                media_failed=0,
                success=False,
                errors=[str(e)],
                platform="facebook",
            )
            controller.fail()
            await self._save_download_history(profile_url, summary, started_at)
            return summary
    
    async def download_single_instagram_post(
        self,
        post_url: str,
        progress_callback: Callable[[str, int, int, str], None],
        controller: Optional[DownloadController] = None,
    ) -> FetchSummary:
        """
        Download a single Instagram post.
        
        Args:
            post_url: Instagram post URL (e.g., instagram.com/p/ABC123)
            progress_callback: Callback for progress updates
            controller: Optional download controller for pause/cancel
        
        Returns:
            FetchSummary with download results
        """
        started_at = datetime.utcnow()
        
        try:
            # Extract shortcode from URL
            import re
            match = re.search(r'/(p|reel|tv)/([^/]+)', post_url)
            if not match:
                raise Exception("Invalid Instagram post URL")
            
            shortcode = match.group(2)
            
            progress_callback("Fetching", 10, 100, f"Fetching post {shortcode}...")
            
            # Use instaloader to download single post
            from instaloader import Instaloader, Post
            from mediasnap.core.scraper import _find_session_file
            
            loader = Instaloader(download_videos=True, download_video_thumbnails=False,
                               download_geotags=False, download_comments=False,
                               save_metadata=False)
            
            # Load session if exists
            session_file = _find_session_file()
            if session_file:
                username = Path(session_file).stem.replace("_session", "")
                loader.load_session_from_file(username, session_file)
            
            progress_callback("Downloading", 30, 100, "Downloading media...")
            
            # Download the post
            post = Post.from_shortcode(loader.context, shortcode)
            download_path = DOWNLOAD_DIR / "instagram" / "single_posts"
            download_path.mkdir(parents=True, exist_ok=True)
            
            loader.download_post(post, target=str(download_path / shortcode))
            
            progress_callback("Complete", 100, 100, "✓ Download complete!")
            
            summary = FetchSummary(
                username=shortcode,
                profile_id=shortcode,
                total_posts_found=1,
                new_posts=1,
                existing_posts=0,
                media_downloaded=1,
                media_failed=0,
                success=True,
                download_path=str(download_path),
                platform="instagram",
            )
            
            controller.complete()
            await self._save_download_history(post_url, summary, started_at)
            return summary
            
        except Exception as e:
            logger.exception(f"Failed to download Instagram post: {e}")
            summary = FetchSummary(
                username=post_url,
                profile_id="",
                total_posts_found=0,
                new_posts=0,
                existing_posts=0,
                media_downloaded=0,
                media_failed=1,
                errors=[str(e)],
                success=False,
                platform="instagram",
            )
            controller.fail()
            await self._save_download_history(post_url, summary, started_at)
            return summary
    
    async def download_single_youtube_video(
        self,
        video_url: str,
        progress_callback: Callable[[str, int, int, str], None],
        controller: Optional[DownloadController] = None,
    ) -> FetchSummary:
        """
        Download a single YouTube video.
        
        Args:
            video_url: YouTube video URL
            progress_callback: Callback for progress updates
            controller: Optional download controller for pause/cancel
        
        Returns:
            FetchSummary with download results
        """
        started_at = datetime.utcnow()
        
        try:
            progress_callback("Fetching", 10, 100, "Fetching video info...")
            
            # Use yt-dlp to download single video
            result = await self.youtube_downloader.download_video(video_url, progress_callback)
            
            progress_callback("Complete", 100, 100, "✓ Download complete!")
            
            summary = FetchSummary(
                username=result.get("title", "video"),
                profile_id=result.get("id", ""),
                total_posts_found=1,
                new_posts=1,
                existing_posts=0,
                media_downloaded=1 if result.get("success") else 0,
                media_failed=0 if result.get("success") else 1,
                success=result.get("success", False),
                download_path=result.get("download_path", ""),
                platform="youtube",
            )
            
            controller.complete()
            await self._save_download_history(video_url, summary, started_at)
            return summary
            
        except Exception as e:
            logger.exception(f"Failed to download YouTube video: {e}")
            summary = FetchSummary(
                username=video_url,
                profile_id="",
                total_posts_found=0,
                new_posts=0,
                existing_posts=0,
                media_downloaded=0,
                media_failed=1,
                errors=[str(e)],
                success=False,
                platform="youtube",
            )
            controller.fail()
            await self._save_download_history(video_url, summary, started_at)
            return summary
    
    async def download_single_facebook_post(
        self,
        post_url: str,
        progress_callback: Callable[[str, int, int, str], None],
        controller: Optional[DownloadController] = None,
    ) -> FetchSummary:
        """
        Download a single Facebook post.
        
        Args:
            post_url: Facebook post URL
            progress_callback: Callback for progress updates
            controller: Optional download controller for pause/cancel
        
        Returns:
            FetchSummary with download results
        """
        started_at = datetime.utcnow()
        
        try:
            progress_callback("Fetching", 10, 100, "Fetching post...")
            
            # Use gallery-dl for single post download
            download_path = DOWNLOAD_DIR / "facebook" / "single_posts"
            download_path.mkdir(parents=True, exist_ok=True)
            
            # For now, return not implemented
            raise NotImplementedError("Single Facebook post download not yet fully implemented")
            
        except Exception as e:
            logger.exception(f"Failed to download Facebook post: {e}")
            summary = FetchSummary(
                username=post_url,
                profile_id="",
                total_posts_found=0,
                new_posts=0,
                existing_posts=0,
                media_downloaded=0,
                media_failed=1,
                errors=[str(e)],
                success=False,
                platform="facebook",
            )
            controller.fail()
            await self._save_download_history(post_url, summary, started_at)
            return summary
