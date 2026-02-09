"""Custom exceptions for MediaSnap."""


class MediaSnapError(Exception):
    """Base exception for MediaSnap."""
    pass


class ProfileNotFoundError(MediaSnapError):
    """Profile does not exist or is not accessible."""
    pass


class RateLimitedError(MediaSnapError):
    """Rate limited by Instagram."""
    pass


class ScrapingFailedError(MediaSnapError):
    """Failed to scrape data from Instagram."""
    pass


class DownloadError(MediaSnapError):
    """Failed to download media."""
    pass


class ParsingError(MediaSnapError):
    """Failed to parse data."""
    pass
