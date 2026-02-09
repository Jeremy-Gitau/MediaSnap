"""Bridge between asyncio and tkinter event loops."""

import asyncio
import threading
from concurrent.futures import Future
from typing import Any, Coroutine, Optional

from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


class AsyncExecutor:
    """
    Manages an asyncio event loop in a background thread for running
    async operations without blocking the tkinter UI thread.
    """
    
    def __init__(self):
        """Initialize the executor."""
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self) -> None:
        """
        Start the background thread with asyncio event loop.
        Must be called before submitting tasks.
        """
        if self._running:
            logger.warning("AsyncExecutor already running")
            return
        
        self._running = True
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()
        logger.info("AsyncExecutor started")
    
    def _run_event_loop(self) -> None:
        """
        Run the asyncio event loop in the background thread.
        This method runs in a separate thread.
        """
        # Create new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_forever()
        finally:
            # Cleanup
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            
            self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()
            logger.info("AsyncExecutor event loop closed")
    
    def submit(self, coro: Coroutine) -> Future:
        """
        Submit a coroutine to run in the background asyncio loop.
        
        Args:
            coro: Coroutine to execute
        
        Returns:
            Future that will contain the result
        
        Raises:
            RuntimeError: If executor not started
        """
        if not self._running or self.loop is None:
            raise RuntimeError("AsyncExecutor not started. Call start() first.")
        
        # Create a Future that will bridge to the UI thread
        future = Future()
        
        async def wrapped():
            """Wrapper that handles result/exception propagation."""
            try:
                result = await coro
                future.set_result(result)
            except Exception as e:
                logger.exception("Error in async task")
                future.set_exception(e)
        
        # Schedule the coroutine in the background loop
        asyncio.run_coroutine_threadsafe(wrapped(), self.loop)
        
        return future
    
    def stop(self) -> None:
        """
        Stop the background thread and event loop.
        Should be called when shutting down the application.
        """
        if not self._running:
            return
        
        self._running = False
        
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        if self.thread:
            self.thread.join(timeout=5.0)
        
        logger.info("AsyncExecutor stopped")
    
    def is_running(self) -> bool:
        """Check if the executor is running."""
        return self._running
