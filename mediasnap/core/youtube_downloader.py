"""YouTube channel downloader using yt-dlp."""

import asyncio
import re
import shutil
from pathlib import Path
from typing import Callable, Optional

import yt_dlp

from mediasnap.core.exceptions import DownloadError
from mediasnap.utils.config import DOWNLOAD_DIR
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)

# Type alias for progress callback
ProgressCallback = Optional[Callable[[str, int, int, str], None]]


def _check_ffmpeg() -> bool:
    """Check if ffmpeg is installed."""
    return shutil.which("ffmpeg") is not None


class YouTubeDownloader:
    """
    YouTube channel video downloader using yt-dlp.
    """
    
    def __init__(self):
        """Initialize YouTube downloader."""
        self.downloaded_count = 0
        self.failed_count = 0
        self.failed_videos = []
    
    def _is_youtube_url(self, url: str) -> bool:
        """
        Check if URL is a YouTube channel or video URL.
        
        Args:
            url: URL to check
        
        Returns:
            True if YouTube URL
        """
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|@|user/)',
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=',
            r'(?:https?://)?youtu\.be/',
        ]
        return any(re.search(pattern, url) for pattern in patterns)
    
    async def download_channel(
        self,
        channel_url: str,
        progress_callback: ProgressCallback = None,
    ) -> dict:
        """
        Download all videos from a YouTube channel.
        
        Args:
            channel_url: YouTube channel URL
            progress_callback: Optional callback(stage, current, total, message)
        
        Returns:
            Dictionary with download statistics
        """
        if not self._is_youtube_url(channel_url):
            raise DownloadError("Invalid YouTube URL")
        
        logger.info(f"Starting YouTube channel download: {channel_url}")
        
        # Extract channel name from URL
        channel_name = self._extract_channel_name(channel_url)
        download_path = DOWNLOAD_DIR / "youtube" / channel_name
        download_path.mkdir(parents=True, exist_ok=True)
        
        if progress_callback:
            progress_callback("Fetching", 0, 100, "Fetching channel info...")
        
        # Check if ffmpeg is available
        has_ffmpeg = _check_ffmpeg()
        if not has_ffmpeg:
            logger.warning("ffmpeg not found - videos will be downloaded in single-file format (may be lower quality)")
        
        # Configure yt-dlp options
        if has_ffmpeg:
            # Best quality with merging (requires ffmpeg)
            video_format = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            postprocessors = [{
                'key': 'FFmpegMetadata',
            }]
        else:
            # Single file format (no merging needed)
            video_format = 'best[ext=mp4]/best'
            postprocessors = []
        
        ydl_opts = {
            'format': video_format,
            'outtmpl': str(download_path / '%(title)s.%(ext)s'),
            'ignoreerrors': True,  # Continue on errors
            'no_warnings': False,
            'quiet': False,
            'progress_hooks': [self._create_progress_hook(progress_callback)],
            'postprocessors': postprocessors,
            'writesubtitles': False,
            'writethumbnail': False,
            'merge_output_format': 'mp4',
        }
        
        try:
            # Run yt-dlp in thread pool (it's blocking)
            await asyncio.to_thread(self._download_with_ytdlp, channel_url, ydl_opts)
            
            logger.info(
                f"YouTube download complete: {self.downloaded_count} downloaded, "
                f"{self.failed_count} failed"
            )
            
            return {
                "success": True,
                "channel_name": channel_name,
                "downloaded": self.downloaded_count,
                "failed": self.failed_count,
                "failed_videos": self.failed_videos,
                "download_path": str(download_path),
            }
            
        except Exception as e:
            logger.exception(f"YouTube download failed: {e}")
            raise DownloadError(f"YouTube download failed: {str(e)}")
    
    def _extract_channel_name(self, url: str) -> str:
        """
        Extract channel name from YouTube URL.
        
        Args:
            url: YouTube URL
        
        Returns:
            Channel name
        """
        # Try to extract from URL patterns
        patterns = [
            r'youtube\.com/@([^/\?]+)',
            r'youtube\.com/c/([^/\?]+)',
            r'youtube\.com/channel/([^/\?]+)',
            r'youtube\.com/user/([^/\?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Fallback to generic name
        return "youtube_channel"
    
    def _create_progress_hook(self, progress_callback: ProgressCallback):
        """
        Create a progress hook for yt-dlp.
        
        Args:
            progress_callback: Progress callback function
        
        Returns:
            Progress hook function
        """
        def progress_hook(d):
            if progress_callback:
                if d['status'] == 'downloading':
                    # Calculate progress
                    if 'total_bytes' in d:
                        current = d.get('downloaded_bytes', 0)
                        total = d['total_bytes']
                        percent = int((current / total) * 100) if total > 0 else 0
                        filename = d.get('filename', 'video')
                        progress_callback(
                            "Downloading",
                            percent,
                            100,
                            f"{Path(filename).name}"
                        )
                    elif '_percent_str' in d:
                        percent_str = d['_percent_str'].strip()
                        try:
                            percent = int(float(percent_str.replace('%', '')))
                            filename = d.get('filename', 'video')
                            progress_callback(
                                "Downloading",
                                percent,
                                100,
                                f"{Path(filename).name}"
                            )
                        except:
                            pass
                
                elif d['status'] == 'finished':
                    filename = d.get('filename', 'video')
                    progress_callback(
                        "Processing",
                        100,
                        100,
                        f"Finalizing {Path(filename).name}"
                    )
                    self.downloaded_count += 1
        
        return progress_hook
    
    def _download_with_ytdlp(self, url: str, options: dict):
        """
        Download videos using yt-dlp (blocking operation).
        
        Args:
            url: YouTube URL
            options: yt-dlp options dictionary
        """
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])
        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            self.failed_count += 1
            self.failed_videos.append(str(e))
            raise
