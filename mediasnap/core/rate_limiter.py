"""Rate limiting for API requests."""

import asyncio
import random
import time
from typing import Optional

from mediasnap.utils.config import REQUEST_DELAY, REQUEST_JITTER
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Async rate limiter to prevent overwhelming Instagram's servers.
    
    Implements:
    - Minimum delay between requests
    - Jitter to avoid detection patterns
    - Request counting for monitoring
    """
    
    def __init__(self, delay: float = REQUEST_DELAY, jitter: float = REQUEST_JITTER):
        """
        Initialize rate limiter.
        
        Args:
            delay: Base delay in seconds between requests
            jitter: Maximum random variation (±jitter seconds)
        """
        self.delay = delay
        self.jitter = jitter
        self.last_request_time: Optional[float] = None
        self.request_count = 0
        self._lock = asyncio.Lock()
    
    async def wait(self) -> None:
        """
        Wait if necessary to respect rate limiting.
        Should be called before each request.
        """
        async with self._lock:
            now = time.time()
            
            if self.last_request_time is not None:
                elapsed = now - self.last_request_time
                
                # Calculate wait time with jitter
                jitter_value = random.uniform(-self.jitter, self.jitter)
                required_wait = self.delay + jitter_value
                
                if elapsed < required_wait:
                    wait_time = required_wait - elapsed
                    logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
            
            self.last_request_time = time.time()
            self.request_count += 1
    
    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            "total_requests": self.request_count,
            "last_request_time": self.last_request_time,
        }
    
    def reset(self) -> None:
        """Reset rate limiter state."""
        self.last_request_time = None
        self.request_count = 0
        logger.debug("Rate limiter reset")


# Global rate limiter instance
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance.
    
    Returns:
        RateLimiter instance
    """
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter
