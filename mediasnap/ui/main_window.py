"""Main application window."""

import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk, CENTER
from concurrent.futures import Future
from typing import Optional

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from mediasnap import __version__
from mediasnap.core.app_service import MediaSnapService, FetchSummary
from mediasnap.storage.database import close_db, init_db
from mediasnap.ui.async_bridge import AsyncExecutor
from mediasnap.ui.styles import (
    FONT_BUTTON,
    FONT_HEADER,
    FONT_LABEL,
    FONT_LOG,
    PAD_LARGE,
    PAD_MEDIUM,
    PAD_SMALL,
    THEME,
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_WIDTH,
)
from mediasnap.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


class MainWindow(ttkb.Window):
    """Main application window for MediaSnap."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__(themename=THEME)
        
        self.title(f"MediaSnap v{__version__}")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # Initialize services
        self.async_executor = AsyncExecutor()
        self.async_executor.start()
        self.service = MediaSnapService()
        
        # State
        self.is_fetching = False
        self.current_future: Optional[Future] = None
        
        # Statistics tracking
        self.total_profiles = 0
        self.total_posts = 0
        self.total_downloads = 0
        
        # Build UI
        self._build_ui()
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        logger.info("MainWindow initialized")
    
    def _create_stat_card(self, parent, icon: str, label: str, value: str, style: str) -> ttk.Frame:
        """
        Create a statistics card widget.
        
        Args:
            parent: Parent widget
            icon: Emoji icon
            label: Card label
            value: Initial value
            style: Bootstrap style
        
        Returns:
            Frame containing the stat card
        """
        # Use LabelFrame for colored border effect
        card = ttk.LabelFrame(parent, bootstyle=style, padding=10)
        
        # Icon
        icon_label = ttk.Label(
            card,
            text=icon,
            font=("Helvetica", 32),
        )
        icon_label.pack(pady=(5, 0))
        
        # Value (large number)
        value_label = ttk.Label(
            card,
            text=value,
            font=("Helvetica", 28, "bold"),
            bootstyle=style,
        )
        value_label.pack()
        
        # Label (description)
        desc_label = ttk.Label(
            card,
            text=label,
            font=("Helvetica", 9),
            bootstyle=SECONDARY,
            justify=CENTER,
        )
        desc_label.pack(pady=(0, 5))
        
        # Store label references for updating
        card.value_label = value_label
        card.desc_label = desc_label
        
        return card
    
    def _update_stats(self) -> None:
        """Update statistics display."""
        self.stats_cards[0].value_label.config(text=str(self.total_profiles))
        self.stats_cards[1].value_label.config(text=str(self.total_posts))
        self.stats_cards[2].value_label.config(text=str(self.total_downloads))
    
    def _build_ui(self) -> None:
        """Build the user interface."""
        # Main container with padding
        main_frame = ttk.Frame(self, padding=PAD_LARGE)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # Header section with gradient-like appearance
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, PAD_LARGE))
        
        # Main title
        header_label = ttk.Label(
            header_frame,
            text="📸 MediaSnap",
            font=("Helvetica", 32, "bold"),
            bootstyle=PRIMARY,
        )
        header_label.pack()
        
        # Subtitle  
        subtitle_label = ttk.Label(
            header_frame,
            text="✨ Archive Instagram & YouTube with style ✨",
            font=("Helvetica", 12),
            bootstyle=SECONDARY,
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Stats cards row
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=X, pady=(0, PAD_LARGE))
        
        # Create three stat cards with vibrant colors
        self.stats_cards = []
        stats_data = [
            ("🎯", "Profiles\nFetched", "0", "success"),
            ("📦", "Total\nPosts", "0", "info"),
            ("💾", "Files\nDownloaded", "0", "warning"),
        ]
        
        for icon, label, value, style in stats_data:
            card = self._create_stat_card(stats_frame, icon, label, value, style)
            card.pack(side=LEFT, fill=BOTH, expand=YES, padx=5)
            self.stats_cards.append(card)
        
        # Input section with modern styling
        input_container = ttk.LabelFrame(
            main_frame,
            text="",
            bootstyle="primary",
            padding=PAD_MEDIUM,
        )
        input_container.pack(fill=X, pady=PAD_MEDIUM)
        
        # Input label with icon
        ttk.Label(
            input_container,
            text="🔗 Instagram, YouTube, or LinkedIn Profile URL",
            font=("Helvetica", 12, "bold"),
            bootstyle="primary",
        ).pack(anchor=W, pady=(0, PAD_SMALL))
        
        # Entry with button in same row
        input_row = ttk.Frame(input_container)
        input_row.pack(fill=X)
        
        self.username_entry = ttk.Entry(
            input_row,
            font=("Helvetica", 13),
            bootstyle=PRIMARY,
        )
        self.username_entry.pack(side=LEFT, fill=X, expand=YES, padx=(0, PAD_SMALL))
        self.username_entry.bind("<Return>", lambda e: self._on_fetch_clicked())
        self.username_entry.focus()
        
        # Fetch button with icon
        self.fetch_button = ttk.Button(
            input_row,
            text="🚀 Fetch",
            command=self._on_fetch_clicked,
            bootstyle="success",
            width=15,
        )
        self.fetch_button.pack(side=LEFT)
        
        # Progress section with modern design
        progress_container = ttk.LabelFrame(
            main_frame,
            text="📊 Download Progress",
            padding=PAD_MEDIUM,
            bootstyle="info",
        )
        progress_container.pack(fill=X, pady=PAD_LARGE)
        
        # Progress bar with striped animated style
        self.progress_bar = ttk.Progressbar(
            progress_container,
            mode="determinate",
            bootstyle="success-striped",
            maximum=100,
        )
        self.progress_bar.pack(fill=X, pady=(0, PAD_SMALL))
        
        # Status with icon
        self.status_label = ttk.Label(
            progress_container,
            text="🎬 Ready to fetch profiles - Enter a username to begin!",
            font=("Helvetica", 11),
            bootstyle=SECONDARY,
        )
        self.status_label.pack(anchor=W)
        
        # Log output section with modern frame
        log_container = ttk.LabelFrame(
            main_frame,
            text="📝 Activity Log",
            padding=PAD_MEDIUM,
        )
        log_container.pack(fill=BOTH, expand=YES, pady=PAD_MEDIUM)
        
        self.log_text = scrolledtext.ScrolledText(
            log_container,
            font=FONT_LOG,
            height=12,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#1e1e1e" if THEME == "darkly" else "#f8f9fa",
            fg="#d4d4d4" if THEME == "darkly" else "#212529",
        )
        self.log_text.pack(fill=BOTH, expand=YES)
        
        # Footer with helpful info
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=X, pady=(PAD_MEDIUM, 0))
        
        ttk.Label(
            footer_frame,
            text="💡 Instagram: reels/, images/, carousel/, tagged/ • YouTube: organized by title",
            font=("Helvetica", 9),
            bootstyle=SECONDARY,
        ).pack()
    
    def _on_fetch_clicked(self) -> None:
        """Handle fetch button click."""
        if self.is_fetching:
            return
        
        input_text = self.username_entry.get().strip()
        if not input_text:
            self._set_status("⚠️  Please enter a username or URL", bootstyle=WARNING)
            return
        
        # Check if it's a YouTube URL
        if self._is_youtube_url(input_text):
            self._start_youtube_fetch(input_text)
            return
        
        # Check if it's a LinkedIn URL
        if self._is_linkedin_url(input_text):
            self._start_linkedin_fetch(input_text)
            return
        
        # Extract username from Instagram URL or clean input
        username = self._extract_username(input_text)
        if not username:
            self._set_status("❌ Invalid Instagram, YouTube, or LinkedIn URL", bootstyle=WARNING)
            return
        
        # Start Instagram fetch
        self._start_fetch(username)
    
    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube URL."""
        import re
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|@|user/)',
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=',
            r'(?:https?://)?youtu\.be/',
        ]
        return any(re.search(pattern, url) for pattern in patterns)
    
    def _is_linkedin_url(self, url: str) -> bool:
        """Check if URL is a LinkedIn URL."""
        import re
        patterns = [
            r'(?:https?://)?(?:www\.)?linkedin\.com/in/',  # Profile
            r'(?:https?://)?(?:www\.)?linkedin\.com/company/',  # Company
        ]
        return any(re.search(pattern, url) for pattern in patterns)
    
    def _start_youtube_fetch(self, channel_url: str) -> None:
        """Start fetching YouTube channel in background."""
        import shutil
        
        self.is_fetching = True
        self.fetch_button.config(state=tk.DISABLED)
        self.username_entry.config(state=tk.DISABLED)
        
        self.progress_bar["value"] = 0
        self._set_status(f"🚀 Starting YouTube download...", bootstyle=INFO)
        self._log(f"╔═══════════════════════════════════╗")
        self._log(f"║  Downloading YouTube Channel  ║")
        self._log(f"╚═══════════════════════════════════╝")
        
        # Check for ffmpeg
        if not shutil.which("ffmpeg"):
            self._log("⚠️  ffmpeg not found - videos will be lower quality")
            self._log("   💡 Install ffmpeg for best quality: brew install ffmpeg")
            self._log("   📖 See YOUTUBE_SETUP.md for details")
        
        # Submit async task
        def progress_callback(stage, current, total, message):
            # Schedule UI update on main thread
            self.after(0, self._update_progress, stage, current, total, message)
        
        coro = self.service.download_youtube_channel(channel_url, progress_callback)
        self.current_future = self.async_executor.submit(coro)
        
        # Poll for completion
        self._check_future_status()
    
    def _start_linkedin_fetch(self, profile_url: str) -> None:
        """Start fetching LinkedIn profile in background."""
        self.is_fetching = True
        self.fetch_button.config(state=tk.DISABLED)
        self.username_entry.config(state=tk.DISABLED)
        
        self.progress_bar["value"] = 0
        self._set_status(f"🚀 Starting LinkedIn download...", bootstyle=INFO)
        self._log(f"╔═══════════════════════════════════╗")
        self._log(f"║  Downloading LinkedIn Profile  ║")
        self._log(f"╚═══════════════════════════════════╝")
        self._log(f"🔗 URL: {profile_url}")
        self._log("")
        self._log("💡 LinkedIn requires authentication")
        self._log("   Run scripts/linkedin_login.py if you haven't already")
        self._log("   📖 See LINKEDIN_SETUP.md for details")
        
        # Submit async task
        def progress_callback(stage, current, total, message):
            # Schedule UI update on main thread
            self.after(0, self._update_progress, stage, current, total, message)
        
        coro = self.service.download_linkedin_profile(profile_url, progress_callback)
        self.current_future = self.async_executor.submit(coro)
        
        # Poll for completion
        self._check_future_status()
    
    def _start_fetch(self, username: str) -> None:
        """Start fetching Instagram profile in background."""
        self.is_fetching = True
        self.fetch_button.config(state=tk.DISABLED)
        self.username_entry.config(state=tk.DISABLED)
        
        self.progress_bar["value"] = 0
        self._set_status(f"🚀 Starting fetch for @{username}...", bootstyle=INFO)
        self._log(f"╔═══════════════════════════════════╗")
        self._log(f"║  Fetching @{username}  ║")
        self._log(f"╚═══════════════════════════════════╝")
        
        # Submit async task
        def progress_callback(stage, current, total, message):
            # Schedule UI update on main thread
            self.after(0, self._update_progress, stage, current, total, message)
        
        coro = self.service.fetch_and_save_profile(username, progress_callback)
        self.current_future = self.async_executor.submit(coro)
        
        # Poll for completion
        self._check_future_status()
    
    def _check_future_status(self) -> None:
        """Check if the async task has completed."""
        if self.current_future is None:
            return
        
        if not self.current_future.done():
            # Still running, check again soon
            self.after(100, self._check_future_status)
            return
        
        # Task completed, get result
        try:
            summary: FetchSummary = self.current_future.result()
            self._on_fetch_complete(summary)
        except Exception as e:
            logger.exception("Error in fetch task")
            self._on_fetch_error(str(e))
    
    def _update_progress(self, stage: str, current: int, total: int, message: str) -> None:
        """Update progress bar and status (called from main thread)."""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar["value"] = progress
        else:
            self.progress_bar["value"] = current
        
        status_text = f"{stage}: {message}" if message else stage
        self._set_status(status_text, bootstyle=INFO)
        
        if message:
            self._log(f"  {message}")
    
    def _extract_username(self, text: str) -> str:
        """Extract username from URL or return cleaned username."""
        import re
        
        # Clean leading/trailing whitespace
        text = text.strip()
        
        # Remove @ if present
        text = text.lstrip("@")
        
        # Check if it's a URL
        url_pattern = r'(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9._]+)/?.*'
        match = re.match(url_pattern, text)
        if match:
            return match.group(1)
        
        # Otherwise treat as username (validate basic format)
        if re.match(r'^[a-zA-Z0-9._]+$', text):
            return text
        
        return ""
    
    def _on_fetch_complete(self, summary: FetchSummary) -> None:
        """Handle successful fetch completion."""
        self.is_fetching = False
        self.fetch_button.config(state=tk.NORMAL)
        self.username_entry.config(state=tk.NORMAL)
        self.current_future = None
        
        if summary.success:
            # Update statistics
            self.total_profiles += 1
            self.total_posts += summary.total_posts_found
            self.total_downloads += summary.media_downloaded
            self._update_stats()
            
            # Success
            self.progress_bar["value"] = 100
            
            # Different messages for Instagram vs YouTube vs LinkedIn
            if summary.platform == "youtube":
                if summary.new_posts > 0:
                    status = (
                        f"✅ Success! Downloaded {summary.media_downloaded} videos from YouTube"
                    )
                    self._set_status(status, bootstyle=SUCCESS)
                    self._log(f"✅ Success! {summary.media_downloaded} videos downloaded")
                    self._log(f"   📁 Saved to: {summary.download_path}")
                else:
                    status = "✅ YouTube download complete"
                    self._set_status(status, bootstyle=SUCCESS)
                    self._log("✅ No new videos to download")
            elif summary.platform == "linkedin":
                if summary.new_posts > 0:
                    status = (
                        f"✅ Success! Downloaded {summary.media_downloaded} items from LinkedIn"
                    )
                    self._set_status(status, bootstyle=SUCCESS)
                    self._log(f"✅ Success! {summary.media_downloaded} items downloaded")
                    self._log(f"   📁 Saved to: {summary.download_path}")
                    self._log(f"   📂 Organized into: posts/, articles/, videos/, documents/")
                else:
                    status = "✅ LinkedIn download complete"
                    self._set_status(status, bootstyle=SUCCESS)
                    self._log("✅ No new content to download")
            else:
                if summary.new_posts > 0:
                    status = (
                        f"✅ Success! Downloaded {summary.new_posts} new posts "
                        f"({summary.media_downloaded} media files)"
                    )
                    self._set_status(status, bootstyle=SUCCESS)
                    self._log(f"✅ Success! {summary.media_downloaded} files downloaded")
                    self._log(f"   📁 Organized into: reels/, images/, carousel/, tagged/")
                else:
                    status = "✅ Profile up to date (no new posts)"
                    self._set_status(status, bootstyle=SUCCESS)
                    self._log("✅ No new posts to download")
            
            # Log summary
            self._log(f"📊 Total posts: {summary.total_posts_found}")
            if summary.platform == "instagram":
                self._log(f"   ✨ New: {summary.new_posts}, Already saved: {summary.existing_posts}")
            
            if summary.media_failed > 0:
                self._log(f"⚠️  {summary.media_failed} media files failed to download", warning=True)
            
            # Show completion dialog if files were downloaded
            if summary.media_downloaded > 0 and summary.download_path:
                self.after(500, lambda: self._show_completion_dialog(summary))
        else:
            # Failure
            error_msg = summary.errors[0] if summary.errors else "Unknown error"
            self._set_status(f"❌ {error_msg}", bootstyle=DANGER)
            self._log(f"❌ Error: {error_msg}", error=True)
        
        if summary.errors:
            for error in summary.errors:
                self._log(f"  ⚠️  {error}", warning=True)
        
        self._log("")  # Empty line for spacing
    
    def _show_completion_dialog(self, summary: FetchSummary) -> None:
        """Show completion dialog with option to open folder."""
        import subprocess
        import platform
        
        # Create dialog
        dialog = tk.Toplevel(self)
        dialog.title("✅ Download Complete!")
        dialog.geometry("450x250")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog on parent window
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Content frame
        content = ttk.Frame(dialog, padding=20)
        content.pack(fill=BOTH, expand=YES)
        
        # Success icon and message
        icon_label = ttk.Label(
            content,
            text="🎉",
            font=("Helvetica", 48),
        )
        icon_label.pack(pady=(10, 5))
        
        title_label = ttk.Label(
            content,
            text="Download Complete!",
            font=("Helvetica", 18, "bold"),
            bootstyle=SUCCESS,
        )
        title_label.pack(pady=(0, 10))
        
        # Summary info
        platform_emoji = "📸" if summary.platform == "instagram" else "📺"
        summary_text = (
            f"{platform_emoji} {summary.media_downloaded} files downloaded\n"
            f"📁 Saved to: {Path(summary.download_path).name}"
        )
        summary_label = ttk.Label(
            content,
            text=summary_text,
            font=("Helvetica", 11),
            justify=CENTER,
        )
        summary_label.pack(pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(content)
        button_frame.pack(pady=(10, 0))
        
        def open_folder():
            """Open the download folder."""
            try:
                folder_path = Path(summary.download_path)
                if platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", str(folder_path)])
                elif platform.system() == "Windows":
                    subprocess.run(["explorer", str(folder_path)])
                else:  # Linux
                    subprocess.run(["xdg-open", str(folder_path)])
                dialog.destroy()
            except Exception as e:
                logger.error(f"Failed to open folder: {e}")
        
        def close_dialog():
            """Close the dialog."""
            dialog.destroy()
        
        # Open Folder button (primary)
        open_btn = ttk.Button(
            button_frame,
            text="📂 Open Folder",
            command=open_folder,
            bootstyle="success",
            width=15,
        )
        open_btn.pack(side=LEFT, padx=5)
        
        # Close button
        close_btn = ttk.Button(
            button_frame,
            text="Close",
            command=close_dialog,
            bootstyle="secondary",
            width=15,
        )
        close_btn.pack(side=LEFT, padx=5)
    
    def _on_fetch_error(self, error: str) -> None:
        """Handle fetch error."""
        self.is_fetching = False
        self.fetch_button.config(state=tk.NORMAL)
        self.username_entry.config(state=tk.NORMAL)
        self.current_future = None
        self.progress_bar["value"] = 0
        
        self._set_status(f"❌ Error: {error}", bootstyle=DANGER)
        self._log(f"❌ Unexpected error: {error}", error=True)
        self._log("")
    
    def _set_status(self, text: str, bootstyle: str = SECONDARY) -> None:
        """Set status label text and style."""
        self.status_label.config(text=text, bootstyle=bootstyle)
    
    def _log(self, message: str, error: bool = False, warning: bool = False) -> None:
        """Add message to log output."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _on_closing(self) -> None:
        """Handle window close event."""
        logger.info("Shutting down MediaSnap")
        
        # Stop async executor
        self.async_executor.stop()
        
        # Close database
        import asyncio
        try:
            asyncio.run(close_db())
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        
        self.destroy()


def main() -> None:
    """Main entry point for the application."""
    # Setup logging
    setup_logging()
    logger.info("Starting MediaSnap")
    
    # Initialize database
    init_db()
    
    # Create and run UI
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
