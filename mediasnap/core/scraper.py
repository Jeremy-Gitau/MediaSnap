"""Instagram scraper using instaloader library."""

from pathlib import Path
from typing import Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from mediasnap.core.exceptions import (
    ProfileNotFoundError,
    RateLimitedError,
    ScrapingFailedError,
)
from mediasnap.core.scrapers.instaloader_scraper import InstaloaderScraper
from mediasnap.models.data_models import ProfileData
from mediasnap.utils.config import (
    MAX_RETRIES,
    RETRY_INITIAL_WAIT,
    RETRY_MAX_WAIT,
    RETRY_MULTIPLIER,
)
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


def _find_session_file() -> Optional[str]:
    """Find an existing session file."""
    session_dir = Path(__file__).parent.parent.parent / ".sessions"
    if not session_dir.exists():
        return None
    
    # Look for any session file
    session_files = list(session_dir.glob("*_session"))
    if session_files:
        logger.info(f"Found session file: {session_files[0]}")
        return str(session_files[0])
    
    return None


class InstagramScraper:
    """
    Instagram scraper using instaloader library.
    
    Instaloader handles all the complexity of Instagram's API,
    including authentication, rate limiting, and structure changes.
    """
    
    def __init__(self, session_file: Optional[str] = None):
        """
        Initialize scraper.
        
        Args:
            session_file: Path to session file (optional, will auto-detect if None)
        """
        # Auto-detect session file if not provided
        if session_file is None:
            session_file = _find_session_file()
        
        self.scraper = InstaloaderScraper(session_file=session_file)
    
    @retry(
        retry=retry_if_exception_type((ScrapingFailedError,)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(
            multiplier=RETRY_MULTIPLIER,
            min=RETRY_INITIAL_WAIT,
            max=RETRY_MAX_WAIT,
        ),
        reraise=True,
    )
    async def fetch_profile(self, username: str) -> ProfileData:
        """
        Fetch Instagram profile using instaloader.
        
        Args:
            username: Instagram username
        
        Returns:
            ProfileData object
        
        Raises:
            ProfileNotFoundError: If profile doesn't exist
            RateLimitedError: If rate limited
            ScrapingFailedError: If scraping fails
        """
        logger.info(f"Fetching profile: {username}")
        
        try:
            profile = await self.scraper.fetch_profile(username)
            logger.info(f"✓ Successfully fetched {username} ({len(profile.posts)} posts)")
            return profile
        except (ProfileNotFoundError, RateLimitedError) as e:
            # Don't retry these
            raise
        except Exception as e:
            logger.error(f"Error fetching {username}: {str(e)}")
            raise ScrapingFailedError(f"Failed to fetch profile: {str(e)}")
    
    def get_stats(self) -> dict:
        """
        Get scraper statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            "strategy": "instaloader",
        }
