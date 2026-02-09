"""Download control for pause/resume/cancel functionality."""

import asyncio
from enum import Enum
from typing import Optional


class DownloadState(Enum):
    """Download state enumeration."""
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class DownloadController:
    """
    Controls download execution with pause/resume/cancel support.
    """
    
    def __init__(self):
        """Initialize download controller."""
        self.state = DownloadState.RUNNING
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start in running state
        
    def is_running(self) -> bool:
        """Check if download is running."""
        return self.state == DownloadState.RUNNING
    
    def is_paused(self) -> bool:
        """Check if download is paused."""
        return self.state == DownloadState.PAUSED
    
    def is_cancelled(self) -> bool:
        """Check if download is cancelled."""
        return self.state == DownloadState.CANCELLED
    
    def is_completed(self) -> bool:
        """Check if download is completed."""
        return self.state == DownloadState.COMPLETED
    
    def should_continue(self) -> bool:
        """Check if download should continue."""
        return self.state in [DownloadState.RUNNING, DownloadState.PAUSED]
    
    def pause(self):
        """Pause the download."""
        if self.state == DownloadState.RUNNING:
            self.state = DownloadState.PAUSED
            self._pause_event.clear()
    
    def resume(self):
        """Resume the download."""
        if self.state == DownloadState.PAUSED:
            self.state = DownloadState.RUNNING
            self._pause_event.set()
    
    def cancel(self):
        """Cancel the download."""
        self.state = DownloadState.CANCELLED
        self._pause_event.set()  # Unblock if paused
    
    def complete(self):
        """Mark download as completed."""
        self.state = DownloadState.COMPLETED
        self._pause_event.set()  # Ensure not blocked
    
    def fail(self):
        """Mark download as failed."""
        self.state = DownloadState.FAILED
        self._pause_event.set()  # Ensure not blocked
    
    async def wait_if_paused(self):
        """Wait while the download is paused."""
        await self._pause_event.wait()
        
        # Check if cancelled after waiting
        if self.is_cancelled():
            raise asyncio.CancelledError("Download cancelled")
    
    def check_cancelled(self):
        """Raise exception if download is cancelled."""
        if self.is_cancelled():
            raise asyncio.CancelledError("Download cancelled")
