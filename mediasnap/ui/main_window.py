"""Main application window - Modern Interactive UI."""

import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk, CENTER, messagebox
from concurrent.futures import Future
from typing import Optional

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from mediasnap import __version__
from mediasnap.core.app_service import MediaSnapService, FetchSummary
from mediasnap.core.download_controller import DownloadController, DownloadState
from mediasnap.core.auth_helpers import (
    authenticate_instagram,
    authenticate_linkedin,
    check_instagram_auth,
    check_linkedin_auth,
)
from mediasnap.storage.database import close_db, init_db
from mediasnap.ui.async_bridge import AsyncExecutor
from mediasnap.ui.login_dialog import show_login_prompt
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
from mediasnap.utils.config import SESSION_DIR, DOWNLOAD_DIR, BASE_DIR
import sys

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
        self.controller: Optional[DownloadController] = None
        
        # Statistics tracking
        self.total_profiles = 0
        self.total_posts = 0
        self.total_downloads = 0
        
        # Build UI
        self._build_ui()
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Log startup information
        is_executable = getattr(sys, 'frozen', False)
        logger.info("="*60)
        logger.info(f"MediaSnap v{__version__} initialized")
        logger.info(f"Running as: {'Executable' if is_executable else 'Python Script'}")
        logger.info(f"Base directory: {BASE_DIR}")
        logger.info(f"Downloads: {DOWNLOAD_DIR}")
        logger.info(f"Sessions: {SESSION_DIR}")
        logger.info("="*60)
    
    def _create_stat_card(self, parent, icon: str, label: str, value: str, style: str) -> ttk.Frame:
        """
        Create a statistics card widget (legacy method for compatibility).
        
        Args:
            parent: Parent widget
            icon: Emoji icon
            label: Card label
            value: Initial value
            style: Bootstrap style
        
        Returns:
            Frame containing the stat card
        """
        return self._create_modern_stat_card(parent, icon, label, value, style, "#666666")
    
    def _create_modern_stat_card(
        self, parent, icon: str, label: str, value: str, style: str, color: str
    ) -> ttk.Frame:
        """
        Create a modern statistics card with gradient effects.
        
        Args:
            parent: Parent widget
            icon: Emoji icon
            label: Card label
            value: Initial value
            style: Bootstrap style
            color: Hex color for accent
        
        Returns:
            Frame containing the modern stat card
        """
        # Card container with shadow effect (simulated with border)
        card = ttk.LabelFrame(parent, bootstyle=style, padding=8)
        
        # Icon with compact size
        icon_label = ttk.Label(
            card,
            text=icon,
            font=("Apple Color Emoji", 24) if self._is_macos() else ("Segoe UI Emoji", 24),
        )
        icon_label.pack(pady=(3, 5))
        
        # Value (compact animated number)
        value_label = ttk.Label(
            card,
            text=value,
            font=("SF Pro Display", 20, "bold") if self._is_macos() else ("Segoe UI", 20, "bold"),
            bootstyle=style,
        )
        value_label.pack()
        
        # Label (description with compact spacing)
        desc_label = ttk.Label(
            card,
            text=label,
            font=("SF Pro Text", 9) if self._is_macos() else ("Segoe UI", 9),
            bootstyle=SECONDARY,
            justify=CENTER,
        )
        desc_label.pack(pady=(3, 3))
        
        # Store label references for updating
        card.value_label = value_label
        card.desc_label = desc_label
        card.icon_label = icon_label
        
        return card
    
    def _is_macos(self) -> bool:
        """Check if running on macOS."""
        import platform
        return platform.system() == "Darwin"
    
    def _on_platform_button_click(self, platform: str) -> None:
        """Handle platform button click and update button states."""
        # Update the platform variable
        self.platform_var.set(platform)
        
        # Update button styles - reset all to outline, selected gets thicker border
        styles_map = {
            "auto": "primary",
            "instagram": "danger",
            "youtube": "danger",
            "linkedin": "info",
        }
        
        for p, btn in self.platform_buttons.items():
            if p == platform:
                # Selected button - solid outline style
                btn.config(bootstyle=f"{styles_map[p]}")
            else:
                # Unselected buttons - outline style
                btn.config(bootstyle=f"{styles_map[p]}-outline")
        
        # Trigger platform change handler
        self._on_platform_change()
    
    def _on_platform_change(self) -> None:
        """Handle platform selection change."""
        platform = self.platform_var.get()
        logger.debug(f"Platform changed to: {platform}")
        
        # Update placeholder text
        placeholders = {
            "auto": "Paste any URL or @username...",
            "instagram": "e.g., instagram.com/username or @username",
            "youtube": "e.g., youtube.com/@channelname",
            "linkedin": "e.g., linkedin.com/in/username",
        }
        
        if not self.username_entry.get() or "Paste" in self.username_entry.get():
            self.username_entry.delete(0, tk.END)
            self.username_entry.insert(0, placeholders.get(platform, placeholders["auto"]))
            self.username_entry.config(foreground="gray")
    
    def _on_entry_change(self, event) -> None:
        """Validate and provide feedback on URL input."""
        text = self.username_entry.get().strip()
        
        if not text or "Paste" in text:
            self.validation_label.config(text="", bootstyle="")
            return
        
        # Check platform
        if "instagram.com" in text or text.startswith("@"):
            self.validation_label.config(text="✓ Instagram URL detected", bootstyle="success")
        elif "youtube.com" in text or "youtu.be" in text:
            self.validation_label.config(text="✓ YouTube URL detected", bootstyle="info")
        elif "linkedin.com" in text:
            self.validation_label.config(text="✓ LinkedIn URL detected", bootstyle="warning")
        else:
            self.validation_label.config(text="⚠ Enter a valid URL", bootstyle="secondary")
    
    def _on_entry_focus_in(self, event) -> None:
        """Handle entry focus in (clear placeholder)."""
        if self.username_entry.cget("foreground") == "gray":
            self.username_entry.delete(0, tk.END)
            self.username_entry.config(foreground="")
    
    def _on_entry_focus_out(self, event) -> None:
        """Handle entry focus out (restore placeholder if empty)."""
        if not self.username_entry.get():
            platform = self.platform_var.get()
            placeholders = {
                "auto": "Paste any URL or @username...",
                "instagram": "e.g., instagram.com/username or @username",
                "youtube": "e.g., youtube.com/@channelname",
                "linkedin": "e.g., linkedin.com/in/username",
            }
            self.username_entry.insert(0, placeholders.get(platform, placeholders["auto"]))
            self.username_entry.config(foreground="gray")
    
    def _clear_log(self) -> None:
        """Clear the activity log."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
        self._log("📝 Log cleared", tag="info")
    
    def _rotate_tips(self) -> None:
        """Rotate footer tips every 5 seconds."""
        if hasattr(self, 'tip_label') and hasattr(self, 'tips'):
            self.current_tip = (self.current_tip + 1) % len(self.tips)
            self.tip_label.config(text=self.tips[self.current_tip])
            self.after(5000, self._rotate_tips)
    
    def _update_stats(self) -> None:
        """Update statistics display."""
        self.stats_cards[0].value_label.config(text=str(self.total_profiles))
        self.stats_cards[1].value_label.config(text=str(self.total_posts))
        self.stats_cards[2].value_label.config(text=str(self.total_downloads))
    
    def _build_ui(self) -> None:
        """Build the modern, interactive user interface."""
        # Main container with custom background
        main_frame = ttk.Frame(self, padding=PAD_LARGE)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # ═══════════════════════════════════════════════════════
        # HERO HEADER SECTION 🎨
        # ═══════════════════════════════════════════════════════
        header_container = ttk.Frame(main_frame, bootstyle="primary")
        header_container.pack(fill=X, pady=(0, PAD_LARGE))
        
        header_frame = ttk.Frame(header_container, padding=20)
        header_frame.pack(fill=X)
        
        # Animated title
        header_label = ttk.Label(
            header_frame,
            text="📸 MediaSnap",
            font=("SF Pro Display", 42, "bold") if self._is_macos() else ("Segoe UI", 42, "bold"),
            bootstyle=PRIMARY,
        )
        header_label.pack()
        
        # Animated subtitle with gradient effect simulation
        subtitle_label = ttk.Label(
            header_frame,
            text="Archive Instagram • YouTube • LinkedIn with Style",
            font=("SF Pro Text", 14) if self._is_macos() else ("Segoe UI", 14),
            bootstyle=SECONDARY,
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Version badge
        version_label = ttk.Label(
            header_frame,
            text=f"v{__version__}",
            font=("Courier", 10),
            bootstyle="info",
        )
        version_label.pack(pady=(5, 0))
        
        # ═══════════════════════════════════════════════════════
        # STATS DASHBOARD WITH ANIMATIONS 📊
        # ═══════════════════════════════════════════════════════
        stats_container = ttk.Frame(main_frame)
        stats_container.pack(fill=X, pady=(0, PAD_LARGE))
        
        self.stats_cards = []
        stats_data = [
            ("🎯", "Profiles\nArchived", "0", "success", "#10b981"),
            ("📦", "Total\nPosts", "0", "info", "#3b82f6"),
            ("💾", "Files\nDownloaded", "0", "warning", "#f59e0b"),
            ("⚡", "Download\nSpeed", "0 MB/s", "danger", "#ef4444"),
        ]
        
        for icon, label, value, style, color in stats_data:
            card = self._create_modern_stat_card(
                stats_container, icon, label, value, style, color
            )
            card.pack(side=LEFT, fill=BOTH, expand=YES, padx=7)
            self.stats_cards.append(card)
        
        # ═══════════════════════════════════════════════════════
        # INPUT SECTION WITH SMART VALIDATION 🔗
        # ═══════════════════════════════════════════════════════
        input_container = ttk.Frame(main_frame, bootstyle="secondary", padding=20)
        input_container.pack(fill=X, pady=PAD_MEDIUM)
        
        # Platform selector with icons
        platform_frame = ttk.Frame(input_container)
        platform_frame.pack(fill=X, pady=(0, PAD_MEDIUM))
        
        ttk.Label(
            platform_frame,
            text="🌐 Select Platform",
            font=("Helvetica", 13, "bold"),
            bootstyle="primary",
        ).pack(anchor=W)
        
        # Platform buttons (toggle style)
        button_frame = ttk.Frame(platform_frame)
        button_frame.pack(fill=X, pady=(10, 0))
        
        self.platform_var = tk.StringVar(value="auto")
        self.platform_buttons = {}
        
        platforms = [
            ("auto", "🔮 Auto-Detect", "primary"),
            ("instagram", "📸 Instagram", "danger"),
            ("youtube", "▶️ YouTube", "danger"),
            ("linkedin", "💼 LinkedIn", "info"),
        ]
        
        for platform, text, style in platforms:
            btn = ttk.Button(
                button_frame,
                text=text,
                bootstyle=f"{style}-outline",
                command=lambda p=platform: self._on_platform_button_click(p),
            )
            btn.pack(side=LEFT, padx=5, expand=YES, fill=X)
            self.platform_buttons[platform] = btn
        
        # Set initial button state (auto-detect is selected by default)
        self.platform_buttons["auto"].config(bootstyle="primary")
        
        # URL input with placeholder effect
        input_label = ttk.Label(
            input_container,
            text="🔗 Enter Profile URL or Username",
            font=("Helvetica", 13, "bold"),
            bootstyle="primary",
        ).pack(anchor=W, pady=(PAD_MEDIUM, PAD_SMALL))
        
        # Entry with button in modern row
        input_row = ttk.Frame(input_container)
        input_row.pack(fill=X)
        
        # Entry with validation feedback
        entry_frame = ttk.Frame(input_row)
        entry_frame.pack(side=LEFT, fill=X, expand=YES, padx=(0, PAD_SMALL))
        
        self.username_entry = ttk.Entry(
            entry_frame,
            font=("Helvetica", 14),
            bootstyle=PRIMARY,
        )
        self.username_entry.pack(fill=X)
        self.username_entry.bind("<Return>", lambda e: self._on_fetch_clicked())
        self.username_entry.bind("<KeyRelease>", self._on_entry_change)
        self.username_entry.insert(0, "Paste URL or @username here...")
        self.username_entry.bind("<FocusIn>", self._on_entry_focus_in)
        self.username_entry.bind("<FocusOut>", self._on_entry_focus_out)
        self.username_entry.config(foreground="gray")
        self.username_entry.focus()
        
        # Validation indicator
        self.validation_label = ttk.Label(
            entry_frame,
            text="",
            font=("Helvetica", 9),
        )
        self.validation_label.pack(anchor=W, pady=(2, 0))
        
        # Action buttons with animations
        button_row = ttk.Frame(input_row)
        button_row.pack(side=LEFT)
        
        # Main fetch button with gradient effect
        self.fetch_button = ttk.Button(
            button_row,
            text="🚀 Start Download",
            command=self._on_fetch_clicked,
            bootstyle="success",
            width=18,
        )
        self.fetch_button.pack(side=LEFT, padx=2)
        
        # Control buttons (initially hidden)
        self.pause_button = ttk.Button(
            button_row,
            text="⏸️",
            command=self._on_pause_clicked,
            bootstyle="warning",
            width=5,
        )
        
        self.resume_button = ttk.Button(
            button_row,
            text="▶️",
            command=self._on_resume_clicked,
            bootstyle="info",
            width=5,
        )
        
        self.cancel_button = ttk.Button(
            button_row,
            text="⏹️",
            command=self._on_cancel_clicked,
            bootstyle="danger",
            width=5,
        )
        
        # Initially hide control buttons
        self._hide_control_buttons()
        
        # ═══════════════════════════════════════════════════════
        # PROGRESS VISUALIZATION WITH LIVE UPDATES 📊
        # ═══════════════════════════════════════════════════════
        progress_container = ttk.Frame(main_frame, bootstyle="info", padding=20)
        progress_container.pack(fill=X, pady=PAD_LARGE)
        
        ttk.Label(
            progress_container,
            text="📊 Download Progress",
            font=("Helvetica", 13, "bold"),
            bootstyle="info",
        ).pack(anchor=W, pady=(0, PAD_MEDIUM))
        
        # Modern progress bar with percentage overlay
        progress_frame = ttk.Frame(progress_container)
        progress_frame.pack(fill=X, pady=(0, PAD_SMALL))
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            bootstyle="info",
            maximum=100,
        )
        self.progress_bar.pack(fill=X)
        
        # Progress percentage label
        self.progress_percentage = ttk.Label(
            progress_container,
            text="0%",
            font=("Helvetica", 11, "bold"),
            bootstyle="success",
        )
        self.progress_percentage.pack(anchor=E, pady=(2, 8))
        
        # Status with animated icons
        self.status_label = ttk.Label(
            progress_container,
            text="🎬 Ready to download - Select a platform and enter a URL!",
            font=("Helvetica", 12),
            bootstyle=SECONDARY,
            wraplength=700,
        )
        self.status_label.pack(anchor=W)
        
        # Quick stats row during download
        quick_stats_frame = ttk.Frame(progress_container)
        quick_stats_frame.pack(fill=X, pady=(10, 0))
        
        self.quick_stat_labels = []
        quick_stats = [
            ("⏱️", "Elapsed:", "0:00"),
            ("📥", "Downloaded:", "0 items"),
            ("⏭️", "Remaining:", "0 items"),
        ]
        
        for icon, label, value in quick_stats:
            stat_frame = ttk.Frame(quick_stats_frame)
            stat_frame.pack(side=LEFT, expand=YES, fill=X, padx=5)
            
            ttk.Label(
                stat_frame,
                text=f"{icon} {label}",
                font=("Helvetica", 9),
                bootstyle=SECONDARY,
            ).pack(side=LEFT)
            
            value_label = ttk.Label(
                stat_frame,
                text=value,
                font=("Helvetica", 9, "bold"),
                bootstyle=PRIMARY,
            )
            value_label.pack(side=LEFT, padx=(5, 0))
            self.quick_stat_labels.append(value_label)
        
        # ═══════════════════════════════════════════════════════
        # ACTIVITY LOG WITH SYNTAX HIGHLIGHTING 📝
        # ═══════════════════════════════════════════════════════
        log_container = ttk.Frame(main_frame, padding=15)
        log_container.pack(fill=BOTH, expand=YES, pady=PAD_MEDIUM)
        
        log_header = ttk.Frame(log_container)
        log_header.pack(fill=X, pady=(0, PAD_SMALL))
        
        ttk.Label(
            log_header,
            text="📝 Activity Log",
            font=("Helvetica", 13, "bold"),
            bootstyle=PRIMARY,
        ).pack(side=LEFT)
        
        # Clear log button
        ttk.Button(
            log_header,
            text="🗑️ Clear",
            command=self._clear_log,
            bootstyle="secondary-outline",
            width=10,
        ).pack(side=RIGHT)
        
        self.log_text = scrolledtext.ScrolledText(
            log_container,
            font=("Monaco", 10) if self._is_macos() else ("Consolas", 10),
            height=14,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#1a1b26" if THEME == "darkly" else "#f8f9fa",
            fg="#c0caf5" if THEME == "darkly" else "#24292e",
            relief=tk.FLAT,
            borderwidth=2,
        )
        self.log_text.pack(fill=BOTH, expand=YES)
        
        # Configure log text tags for colored output
        self.log_text.tag_config("success", foreground="#10b981")
        self.log_text.tag_config("error", foreground="#ef4444")
        self.log_text.tag_config("warning", foreground="#f59e0b")
        self.log_text.tag_config("info", foreground="#3b82f6")
        self.log_text.tag_config("header", foreground="#8b5cf6", font=("Helvetica", 11, "bold"))
        
        # ═══════════════════════════════════════════════════════
        # FOOTER WITH TIPS & TRICKS 💡
        # ═══════════════════════════════════════════════════════
        footer_frame = ttk.Frame(main_frame, padding=10)
        footer_frame.pack(fill=X, pady=(PAD_MEDIUM, 0))
        
        tips = [
            "💡 Instagram: Login required for private accounts",
            "▶️ YouTube: aria2c auto-installs for faster downloads",
            "💼 LinkedIn: Respects rate limits automatically",
            "📁 Smart folders: reels/, images/, youtube/, linkedin/",
        ]
        
        self.tip_label = ttk.Label(
            footer_frame,
            text=tips[0],
            font=("Helvetica", 9),
            bootstyle=SECONDARY,
            anchor=CENTER,
        )
        self.tip_label.pack()
        
        # Rotate tips every 5 seconds
        self.current_tip = 0
        self.tips = tips
        self._rotate_tips()
    
    def _on_fetch_clicked(self) -> None:
        """Handle fetch button click with authentication checks."""
        if self.is_fetching:
            return
        
        input_text = self.username_entry.get().strip()
        
        # Remove placeholder text
        if not input_text or "Paste" in input_text or "e.g.," in input_text:
            self._set_status("⚠️  Please enter a username or URL", bootstyle=WARNING)
            self._animate_status_shake()
            return
        
        # Check if it's a YouTube URL
        if self._is_youtube_url(input_text):
            self._start_youtube_fetch(input_text)
            return
        
        # Check if it's a LinkedIn URL
        if self._is_linkedin_url(input_text):
            # Check LinkedIn authentication
            if not check_linkedin_auth():
                self._log("🔐 LinkedIn login required", tag="warning")
                credentials = show_login_prompt(self, "linkedin")
                
                if credentials:
                    username, password = credentials
                    self._log("Authenticating with LinkedIn...", tag="info")
                    
                    # Authenticate in background
                    async def auth_and_fetch():
                        success = await authenticate_linkedin(username, password)
                        if success:
                            self._log("✅ LinkedIn authentication successful!", tag="success")
                            # Now start the actual fetch
                            await self.service.download_linkedin_profile(
                                input_text,
                                lambda stage, current, total, message: self.after(
                                    0, self._update_progress, stage, current, total, message
                                ),
                                self.controller,
                            )
                        else:
                            self._log("❌ LinkedIn authentication failed", tag="error")
                            self.is_fetching = False
                            self.fetch_button.config(state=tk.NORMAL)
                            self.username_entry.config(state=tk.NORMAL)
                    
                    self.controller = DownloadController()
                    self.current_future = self.async_executor.submit(auth_and_fetch())
                    self.is_fetching = True
                    self.fetch_button.config(state=tk.DISABLED)
                    self.username_entry.config(state=tk.DISABLED)
                    self._show_control_buttons()
                    self._check_future_status()
                else:
                    self._log("❌ LinkedIn login cancelled", tag="warning")
                return
            
            self._start_linkedin_fetch(input_text)
            return
        
        # Extract username from Instagram URL or clean input
        username = self._extract_username(input_text)
        if not username:
            self._set_status("❌ Invalid Instagram, YouTube, or LinkedIn URL", bootstyle=WARNING)
            self._animate_status_shake()
            return
        
        # Check Instagram authentication
        if not check_instagram_auth():
            self._log("🔐 Instagram login required", tag="warning")
            credentials = show_login_prompt(self, "instagram")
            
            if credentials:
                username_ig, password = credentials
                self._log("Authenticating with Instagram...", tag="info")
                
                # Authenticate in background
                async def auth_and_fetch():
                    success = await authenticate_instagram(username_ig, password)
                    if success:
                        self._log("✅ Instagram authentication successful!", tag="success")
                        # Now start the actual fetch
                        await self.service.fetch_and_save_profile(
                            username,
                            lambda stage, current, total, message: self.after(
                                0, self._update_progress, stage, current, total, message
                            ),
                            self.controller,
                        )
                    else:
                        self._log("❌ Instagram authentication failed", tag="error")
                        self.is_fetching = False
                        self.fetch_button.config(state=tk.NORMAL)
                        self.username_entry.config(state=tk.NORMAL)
                
                self.controller = DownloadController()
                self.current_future = self.async_executor.submit(auth_and_fetch())
                self.is_fetching = True
                self.fetch_button.config(state=tk.DISABLED)
                self.username_entry.config(state=tk.DISABLED)
                self._show_control_buttons()
                self._check_future_status()
            else:
                self._log("❌ Instagram login cancelled", tag="warning")
            return
        
        # Start Instagram fetch with existing session
        self._start_fetch(username)
    
    def _animate_status_shake(self) -> None:
        """Animate status label with shake effect."""
        # Simple shake animation by moving label left and right
        original_anchor = self.status_label.cget("anchor")
        positions = ["e", "w", "e", "w", original_anchor]
        
        def animate(index=0):
            if index < len(positions):
                self.status_label.config(anchor=positions[index])
                self.after(50, lambda: animate(index + 1))
        
        animate()
    
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
        self._log(f"╔═══════════════════════════════════╗", tag="header")
        self._log(f"║  Downloading YouTube Channel  ║", tag="header")
        self._log(f"╚═══════════════════════════════════╝", tag="header")
        self._log(f"🔗 URL: {channel_url}", tag="info")
        self._log("")
        
        # Check for ffmpeg
        if not shutil.which("ffmpeg"):
            self._log("⚠️  ffmpeg not found - videos will be lower quality", tag="warning")
            self._log("   💡 Install ffmpeg for best quality: brew install ffmpeg")
            self._log("   📖 See YOUTUBE_SETUP.md for details")
        
        # Check for aria2c
        if not shutil.which("aria2c"):
            self._log("📦 aria2c not installed - will auto-install for faster downloads", tag="info")
        else:
            self._log("✅ aria2c detected - using 16 connections for faster downloads", tag="success")
        
        # Submit async task
        def progress_callback(stage, current, total, message):
            # Schedule UI update on main thread
            self.after(0, self._update_progress, stage, current, total, message)
        
        # Create download controller
        self.controller = DownloadController()
        
        coro = self.service.download_youtube_channel(channel_url, progress_callback, self.controller)
        self.current_future = self.async_executor.submit(coro)
        
        # Show control buttons
        self._show_control_buttons()
        
        # Poll for completion
        self._check_future_status()
    
    def _start_linkedin_fetch(self, profile_url: str) -> None:
        """Start fetching LinkedIn profile in background."""
        self.is_fetching = True
        self.fetch_button.config(state=tk.DISABLED)
        self.username_entry.config(state=tk.DISABLED)
        
        self.progress_bar["value"] = 0
        self._set_status(f"🚀 Starting LinkedIn download...", bootstyle=INFO)
        self._log(f"╔═══════════════════════════════════╗", tag="header")
        self._log(f"║  Downloading LinkedIn Profile  ║", tag="header")
        self._log(f"╚═══════════════════════════════════╝", tag="header")
        self._log(f"🔗 URL: {profile_url}", tag="info")
        self._log("")
        self._log("📊 Fetching profile data...", tag="info")
        self._log("   💼 LinkedIn API rate limits apply")
        self._log("   📖 See LINKEDIN_SETUP.md for details")
        
        # Submit async task
        def progress_callback(stage, current, total, message):
            # Schedule UI update on main thread
            self.after(0, self._update_progress, stage, current, total, message)
        
        # Create download controller
        self.controller = DownloadController()
        
        coro = self.service.download_linkedin_profile(profile_url, progress_callback, self.controller)
        self.current_future = self.async_executor.submit(coro)
        
        # Show control buttons
        self._show_control_buttons()
        
        # Poll for completion
        self._check_future_status()
    
    def _start_fetch(self, username: str) -> None:
        """Start fetching Instagram profile in background."""
        self.is_fetching = True
        self.fetch_button.config(state=tk.DISABLED)
        self.username_entry.config(state=tk.DISABLED)
        
        self.progress_bar["value"] = 0
        self._set_status(f"🚀 Starting fetch for @{username}...", bootstyle=INFO)
        self._log(f"╔═══════════════════════════════════╗", tag="header")
        self._log(f"║  Fetching @{username}  ║", tag="header")
        self._log(f"╚═══════════════════════════════════╝", tag="header")
        self._log(f"📸 Instagram profile: @{username}", tag="info")
        self._log("")
        
        # Submit async task
        def progress_callback(stage, current, total, message):
            #Schedule UI update on main thread
            self.after(0, self._update_progress, stage, current, total, message)
        
        # Create download controller
        self.controller = DownloadController()
        
        coro = self.service.fetch_and_save_profile(username, progress_callback, self.controller)
        self.current_future = self.async_executor.submit(coro)
        
        # Show control buttons
        self._show_control_buttons()
        
        # Poll for completion
        self._check_future_status()
    
    def _show_control_buttons(self) -> None:
        """Show pause/resume/cancel control buttons."""
        self.pause_button.pack(side=LEFT, padx=2)
        self.cancel_button.pack(side=LEFT, padx=2)
    
    def _hide_control_buttons(self) -> None:
        """Hide all control buttons."""
        self.pause_button.pack_forget()
        self.resume_button.pack_forget()
        self.cancel_button.pack_forget()
    
    def _on_pause_clicked(self) -> None:
        """Handle pause button click."""
        if self.controller and self.controller.is_running():
            self.controller.pause()
            self._set_status("\u23f8 Download paused", bootstyle=WARNING)
            self._log("⏸️  Download paused by user")
            
            # Swap pause button with resume button
            self.pause_button.pack_forget()
            self.resume_button.pack(side=LEFT, padx=2)
    
    def _on_resume_clicked(self) -> None:
        """Handle resume button click."""
        if self.controller and self.controller.is_paused():
            self.controller.resume()
            self._set_status("\u25b6\ufe0f Download resumed", bootstyle=INFO)
            self._log("▶️  Download resumed")
            
            # Swap resume button with pause button
            self.resume_button.pack_forget()
            self.pause_button.pack(side=LEFT, padx=2)
    
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        if self.controller:
            self.controller.cancel()
            self._set_status("\u274c Download cancelled", bootstyle=DANGER)
            self._log("❌ Download cancelled byuser")
            
            # Hide control buttons
            self._hide_control_buttons()
    
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
        """Update progress bar, percentage, and status (called from main thread)."""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar["value"] = progress
            self.progress_percentage.config(text=f"{progress}%")
        else:
            self.progress_bar["value"] = current
            self.progress_percentage.config(text=f"{current}%")
        
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
        
        # Hide control buttons
        self._hide_control_buttons()
        
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
                    if summary.skipped_posts > 0:
                        self._log(f"   ⏭️  {summary.skipped_posts} videos skipped (already exist)")
                    self._log(f"   📁 Saved to: {summary.download_path}")
                else:
                    status = "✅ YouTube download complete"
                    self._set_status(status, bootstyle=SUCCESS)
                    if summary.skipped_posts > 0:
                        self._log(f"✅ All {summary.skipped_posts} videos already downloaded")
                    else:
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
    
    def _log(self, message: str, error: bool = False, warning: bool = False, tag: str = None) -> None:
        """Add message to log output with optional color tagging."""
        self.log_text.config(state=tk.NORMAL)
        
        # Determine tag
        if tag:
            # Use provided tag
            display_tag = tag
        elif error:
            display_tag = "error"
        elif warning:
            display_tag = "warning"
        elif message.startswith("╔") or message.startswith("║") or message.startswith("═"):
            display_tag = "header"
        elif "✅" in message or "Success" in message:
            display_tag = "success"
        elif "⚠️" in message or "❌" in message:
            display_tag = "warning"
        elif "🚀" in message or "📊" in message:
            display_tag = "info"
        else:
            display_tag = None
        
        # Insert with tag
        if display_tag:
            self.log_text.insert(tk.END, message + "\n", display_tag)
        else:
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
