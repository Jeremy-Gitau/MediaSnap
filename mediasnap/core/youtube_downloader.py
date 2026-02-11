"""YouTube channel downloader using yt-dlp."""

import asyncio
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

import yt_dlp

from mediasnap.core.exceptions import DownloadError
from mediasnap.utils.config import DOWNLOAD_DIR
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)

# Type alias for progress callback
ProgressCallback = Optional[Callable[[str, int, int, str], None]]


def _get_extended_path() -> str:
    """Get extended PATH with common binary locations for executables."""
    current_path = os.environ.get('PATH', '')
    
    # Add common binary paths (especially important for PyInstaller executables)
    additional_paths = []
    
    if platform.system() == 'Darwin':  # macOS
        additional_paths = [
            '/usr/local/bin',  # Intel Homebrew
            '/opt/homebrew/bin',  # Apple Silicon Homebrew
            '/usr/bin',
            '/bin',
        ]
    elif platform.system() == 'Linux':
        additional_paths = [
            '/usr/local/bin',
            '/usr/bin',
            '/bin',
        ]
    elif platform.system() == 'Windows':
        additional_paths = [
            r'C:\Program Files\ffmpeg\bin',
            r'C:\Program Files\aria2',
        ]
    
    # Combine current PATH with additional paths
    all_paths = current_path.split(os.pathsep) + additional_paths
    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for p in all_paths:
        if p and p not in seen:
            seen.add(p)
            unique_paths.append(p)
    
    return os.pathsep.join(unique_paths)


def _find_executable(name: str) -> Optional[Path]:
    """Find executable in extended PATH."""
    # Update PATH temporarily
    old_path = os.environ.get('PATH', '')
    os.environ['PATH'] = _get_extended_path()
    
    try:
        result = shutil.which(name)
        return Path(result) if result else None
    finally:
        os.environ['PATH'] = old_path


def _check_ffmpeg() -> bool:
    """Check if ffmpeg is installed."""
    return _find_executable("ffmpeg") is not None


def _check_aria2c() -> bool:
    """Check if aria2c is installed."""
    return _find_executable("aria2c") is not None


def _install_ffmpeg() -> bool:
    """Auto-install ffmpeg via Homebrew on macOS."""
    if platform.system() != 'Darwin':
        logger.warning("Auto-install only supported on macOS. Install ffmpeg manually.")
        return False
    
    try:
        logger.info("📦 ffmpeg not found. Installing via Homebrew...")
        subprocess.run(
            ["brew", "install", "ffmpeg"],
            check=True,
            capture_output=True,
            timeout=600,  # 10 minutes for ffmpeg (larger package)
        )
        logger.info("✅ ffmpeg installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install ffmpeg: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg installation timed out")
        return False
    except FileNotFoundError:
        logger.warning("Homebrew not found. Install manually: brew install ffmpeg")
        return False
    except Exception as e:
        logger.error(f"Failed to install ffmpeg: {e}")
        return False


def _install_aria2c() -> bool:
    """Auto-install aria2c via Homebrew on macOS."""
    if platform.system() != 'Darwin':
        logger.warning("Auto-install only supported on macOS. Install aria2c manually.")
        return False
    
    try:
        logger.info("📦 aria2c not found. Installing via Homebrew...")
        subprocess.run(
            ["brew", "install", "aria2"],
            check=True,
            capture_output=True,
            timeout=300,
        )
        logger.info("✅ aria2c installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install aria2c: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except subprocess.TimeoutExpired:
        logger.error("aria2c installation timed out")
        return False
    except FileNotFoundError:
        logger.warning("Homebrew not found. Install manually: brew install aria2")
        return False
    except Exception as e:
        logger.error(f"Failed to install aria2c: {e}")
        return False


class YouTubeDownloader:
    """
    YouTube channel video downloader using yt-dlp.
    """
    
    def __init__(self):
        """Initialize YouTube downloader."""
        self.downloaded_count = 0
        self.failed_count = 0
        self.skipped_count = 0
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
            logger.warning("⚠️  ffmpeg not found - videos will be lower quality")
            logger.info("💻 Attempting to install ffmpeg...")
            if progress_callback:
                progress_callback("Setup", 3, 100, "Installing ffmpeg...")
            if _install_ffmpeg():
                has_ffmpeg = _check_ffmpeg()
                if has_ffmpeg:
                    logger.info("✅ ffmpeg installed and ready!")
        
        # Check if aria2c is available for faster downloads
        has_aria2c = _check_aria2c()
        if not has_aria2c:
            logger.info("💻 Attempting to install aria2c for faster downloads...")
            if progress_callback:
                progress_callback("Setup", 5, 100, "Installing aria2c...")
            if _install_aria2c():
                has_aria2c = _check_aria2c()
                if has_aria2c:
                    logger.info("✅ aria2c installed and ready!")
        
        # Create download archive file to track downloads and avoid duplicates
        archive_file = download_path / ".youtube_archive.txt"
        
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
            # Duplicate detection
            'download_archive': str(archive_file),  # Track downloaded videos
            'nooverwrites': True,  # Don't overwrite existing files
            # Performance optimizations
            'concurrent_fragment_downloads': 5,  # Download 5 fragments at once
            'retries': 3,  # Limit retries
            'fragment_retries': 3,
            'skip_unavailable_fragments': True,
            'continuedl': True,  # Resume partial downloads
            'noprogress': False,
            'http_chunk_size': 10485760,  # 10MB chunks
            'buffersize': 1024 * 64,  # 64KB buffer
            # Use external downloader if available (much faster)
            'external_downloader': 'aria2c' if has_aria2c else None,
            'external_downloader_args': ['-x', '16', '-s', '16', '-k', '1M'] if has_aria2c else None,
        }
        
        if has_aria2c:
            logger.info("🚀 Using aria2c for faster downloads (16 connections per file)")
        else:
            logger.info("💡 Install aria2c for faster downloads: brew install aria2")
        
        try:
            # Run yt-dlp in thread pool (it's blocking)
            await asyncio.to_thread(self._download_with_ytdlp, channel_url, ydl_opts)
            
            logger.info(
                f"YouTube download complete: {self.downloaded_count} downloaded, "
                f"{self.skipped_count} skipped (already exists), "
                f"{self.failed_count} failed"
            )
            
            return {
                "success": True,
                "channel_name": channel_name,
                "downloaded": self.downloaded_count,
                "skipped": self.skipped_count,
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
    
    async def download_video(
        self,
        video_url: str,
        progress_callback: ProgressCallback = None,
    ) -> dict:
        """
        Download a single YouTube video.
        
        Args:
            video_url: YouTube video URL
            progress_callback: Optional callback(stage, current, total, message)
        
        Returns:
            Dictionary with download info
        """
        if not self._is_youtube_url(video_url):
            raise DownloadError("Invalid YouTube video URL")
        
        logger.info(f"Starting YouTube video download: {video_url}")
        
        # Create download directory
        download_path = DOWNLOAD_DIR / "youtube" / "single_videos"
        download_path.mkdir(parents=True, exist_ok=True)
        
        # Configure yt-dlp options for single video
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(download_path / '%(title)s.%(ext)s'),
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'quiet': True,
            'progress_hooks': [self._create_progress_hook(progress_callback)],
        }
        
        # Add ffmpeg if available
        if _check_ffmpeg():
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }]
        
        # Add aria2c for faster downloads if available
        has_aria2c = _check_aria2c()
        if has_aria2c:
            ydl_opts['external_downloader'] = 'aria2c'
            ydl_opts['external_downloader_args'] = ['-x', '16', '-s', '16', '-k', '1M']
        
        try:
            if progress_callback:
                progress_callback("Fetching", 5, 100, "Getting video info...")
            
            # Download the video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                
                if progress_callback:
                    progress_callback("Complete", 100, 100, f"✓ Downloaded: {info.get('title', 'video')}")
                
                return {
                    "success": True,
                    "title": info.get("title", "video"),
                    "id": info.get("id", ""),
                    "download_path": str(download_path),
                }
                
        except Exception as e:
            logger.error(f"Failed to download video: {e}")
            raise DownloadError(f"Video download failed: {str(e)}")
    
    def _download_with_ytdlp(self, url: str, options: dict):
        """
        Download videos using yt-dlp (blocking operation).
        
        Args:
            url: YouTube URL
            options: yt-dlp options dictionary
        """
        # Custom logger to track skipped videos
        class SkipLogger:
            def __init__(self, parent):
                self.parent = parent
            
            def debug(self, msg):
                # Detect when video is skipped (already downloaded)
                if 'has already been recorded in archive' in msg or 'Skipping' in msg:
                    self.parent.skipped_count += 1
                    logger.debug(f"⏭️  Skipped (already downloaded): {msg.split(':')[0]}")
            
            def info(self, msg):
                logger.info(msg)
            
            def warning(self, msg):
                logger.warning(msg)
            
            def error(self, msg):
                logger.error(msg)
        
        # Add custom logger to options
        options_with_logger = options.copy()
        options_with_logger['logger'] = SkipLogger(self)
        
        try:
            with yt_dlp.YoutubeDL(options_with_logger) as ydl:
                ydl.download([url])
        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            self.failed_count += 1
            self.failed_videos.append(str(e))
            raise
