"""Media downloader with streaming and progress tracking."""

import asyncio
import random
from pathlib import Path
from typing import Callable, List, Optional

import aiofiles
import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from mediasnap.core.exceptions import DownloadError
from mediasnap.utils.config import (
    CONNECT_TIMEOUT,
    DOWNLOAD_CHUNK_SIZE,
    DOWNLOAD_DIR,
    MAX_CONCURRENT_DOWNLOADS,
    MAX_RETRIES,
    READ_TIMEOUT,
    RETRY_INITIAL_WAIT,
    RETRY_MAX_WAIT,
    RETRY_MULTIPLIER,
    USER_AGENTS,
)
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)

# Type alias for progress callback
ProgressCallback = Optional[Callable[[int, int, str], None]]


class MediaDownloader:
    """
    Async media downloader with streaming, progress tracking, and retry logic.
    """
    
    def __init__(self, max_concurrent: int = MAX_CONCURRENT_DOWNLOADS):
        """
        Initialize downloader.
        
        Args:
            max_concurrent: Maximum concurrent downloads
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.client: Optional[httpx.AsyncClient] = None
        self.download_count = 0
        self.failed_downloads: List[str] = []
    
    async def __aenter__(self):
        """Create HTTP client on context entry."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(CONNECT_TIMEOUT, read=READ_TIMEOUT),
            follow_redirects=True,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close HTTP client on context exit."""
        if self.client:
            await self.client.aclose()
    
    def _get_headers(self) -> dict:
        """Generate request headers with random user agent."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
    
    @retry(
        retry=retry_if_exception_type((DownloadError, httpx.HTTPError)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(
            multiplier=RETRY_MULTIPLIER,
            min=RETRY_INITIAL_WAIT,
            max=RETRY_MAX_WAIT,
        ),
        reraise=True,
    )
    async def download_media(
        self,
        url: str,
        filepath: Path,
        progress_callback: ProgressCallback = None,
    ) -> Path:
        """
        Download a single media file with streaming.
        
        Args:
            url: Media URL
            filepath: Destination file path
            progress_callback: Optional callback(current_bytes, total_bytes, status)
        
        Returns:
            Path to downloaded file
        
        Raises:
            DownloadError: If download fails
        """
        if not self.client:
            raise DownloadError("MediaDownloader must be used as context manager")
        
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Use temp file during download
        temp_filepath = filepath.with_suffix(filepath.suffix + ".tmp")
        
        try:
            logger.debug(f"Downloading: {url} -> {filepath}")
            
            async with self.semaphore:  # Limit concurrent downloads
                async with self.client.stream("GET", url, headers=self._get_headers()) as response:
                    response.raise_for_status()
                    
                    # Get content length
                    total_bytes = int(response.headers.get("content-length", 0))
                    downloaded_bytes = 0
                    
                    # Stream to file
                    async with aiofiles.open(temp_filepath, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=DOWNLOAD_CHUNK_SIZE):
                            await f.write(chunk)
                            downloaded_bytes += len(chunk)
                            
                            # Report progress
                            if progress_callback and total_bytes > 0:
                                progress_callback(downloaded_bytes, total_bytes, str(filepath.name))
                    
                    # Verify download
                    if total_bytes > 0 and downloaded_bytes != total_bytes:
                        raise DownloadError(
                            f"Incomplete download: {downloaded_bytes}/{total_bytes} bytes"
                        )
                    
                    # Move temp file to final destination
                    temp_filepath.rename(filepath)
                    
                    self.download_count += 1
                    logger.info(f"Downloaded: {filepath.name} ({downloaded_bytes} bytes)")
                    
                    return filepath
        
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} downloading {url}"
            logger.error(error_msg)
            self.failed_downloads.append(str(filepath))
            raise DownloadError(error_msg)
        
        except httpx.HTTPError as e:
            error_msg = f"Network error downloading {url}: {str(e)}"
            logger.error(error_msg)
            self.failed_downloads.append(str(filepath))
            raise DownloadError(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error downloading {url}: {str(e)}"
            logger.exception(error_msg)
            self.failed_downloads.append(str(filepath))
            raise DownloadError(error_msg)
        
        finally:
            # Clean up temp file if it exists
            if temp_filepath.exists():
                try:
                    temp_filepath.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_filepath}: {e}")
    
    async def download_batch(
        self,
        media_urls: List[tuple[str, Path]],
        progress_callback: ProgressCallback = None,
    ) -> List[Path]:
        """
        Download multiple media files concurrently.
        
        Args:
            media_urls: List of (url, filepath) tuples
            progress_callback: Optional callback for progress updates
        
        Returns:
            List of successfully downloaded file paths
        """
        logger.info(f"Starting batch download of {len(media_urls)} files")
        
        tasks = []
        for url, filepath in media_urls:
            task = self.download_media(url, filepath, progress_callback)
            tasks.append(task)
        
        # Download all concurrently (semaphore limits actual concurrency)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Separate successful and failed downloads
        successful = []
        for result, (url, filepath) in zip(results, media_urls):
            if isinstance(result, Exception):
                logger.error(f"Failed to download {filepath.name}: {result}")
            else:
                successful.append(result)
        
        logger.info(
            f"Batch download complete: {len(successful)}/{len(media_urls)} successful"
        )
        
        return successful
    
    def get_stats(self) -> dict:
        """
        Get downloader statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            "total_downloads": self.download_count,
            "failed_downloads": len(self.failed_downloads),
            "failed_files": self.failed_downloads,
        }
