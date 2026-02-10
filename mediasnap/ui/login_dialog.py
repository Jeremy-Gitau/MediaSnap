"""Modern login dialogs for MediaSnap."""

import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from typing import Optional, Tuple
import asyncio
from pathlib import Path


class LoginDialog(ttkb.Toplevel):
    """Base login dialog with modern design."""
    
    def __init__(self, parent, title: str, platform: str):
        """Initialize login dialog."""
        super().__init__(parent)
        
        self.title(title)
        self.platform = platform
        self.result = None
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        # Center on screen
        self.geometry("500x400")
        self.resizable(False, False)
        
        # Build UI
        self._build_ui()
        
        # Focus on first entry
        self.username_entry.focus()
    
    def _build_ui(self):
        """Build the login dialog UI."""
        # Main container with gradient effect
        main_frame = ttk.Frame(self, padding=30)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # Header with icon
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, 20))
        
        platform_icons = {
            "instagram": "📸",
            "linkedin": "💼"
        }
        
        icon_label = ttk.Label(
            header_frame,
            text=platform_icons.get(self.platform, "🔐"),
            font=("Helvetica", 48)
        )
        icon_label.pack()
        
        title_label = ttk.Label(
            header_frame,
            text=f"{self.platform.title()} Login",
            font=("Helvetica", 20, "bold"),
            bootstyle="primary"
        )
        title_label.pack(pady=(10, 5))
        
        subtitle_label = ttk.Label(
            header_frame,
            text="Your credentials are stored securely",
            font=("Helvetica", 10),
            bootstyle="secondary"
        )
        subtitle_label.pack()
        
        # Warning banner
        warning_frame = ttk.Frame(main_frame, bootstyle="warning")
        warning_frame.pack(fill=X, pady=(0, 20))
        
        warning_label = ttk.Label(
            warning_frame,
            text="⚠️  Your password is encrypted and never stored in plain text",
            font=("Helvetica", 9),
            bootstyle="warning",
            padding=10
        )
        warning_label.pack()
        
        # Input fields
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=X, pady=(0, 20))
        
        # Username/Email
        ttk.Label(
            input_frame,
            text="Email / Username",
            font=("Helvetica", 11, "bold")
        ).pack(anchor=W, pady=(0, 5))
        
        self.username_entry = ttk.Entry(
            input_frame,
            font=("Helvetica", 12),
            bootstyle="primary"
        )
        self.username_entry.pack(fill=X, ipady=8)
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        
        # Password
        ttk.Label(
            input_frame,
            text="Password",
            font=("Helvetica", 11, "bold")
        ).pack(anchor=W, pady=(15, 5))
        
        self.password_entry = ttk.Entry(
            input_frame,
            show="•",
            font=("Helvetica", 12),
            bootstyle="primary"
        )
        self.password_entry.pack(fill=X, ipady=8)
        self.password_entry.bind("<Return>", lambda e: self._on_login())
        
        # Show password checkbox
        self.show_password_var = tk.BooleanVar(value=False)
        show_password_check = ttk.Checkbutton(
            input_frame,
            text="Show password",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
            bootstyle="primary-round-toggle"
        )
        show_password_check.pack(anchor=W, pady=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=X, pady=(10, 0))
        
        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            bootstyle="secondary-outline",
            width=15
        )
        cancel_btn.pack(side=RIGHT, padx=(10, 0))
        
        # Login button
        login_btn = ttk.Button(
            button_frame,
            text="🔐 Login",
            command=self._on_login,
            bootstyle="success",
            width=15
        )
        login_btn.pack(side=RIGHT)
        
        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="",
            font=("Helvetica", 10),
            bootstyle="danger"
        )
        self.status_label.pack(pady=(10, 0))
    
    def _toggle_password_visibility(self):
        """Toggle password visibility."""
        if self.show_password_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="•")
    
    def _on_login(self):
        """Handle login button click."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            self.status_label.config(text="❌ Please enter both email and password")
            return
        
        self.result = (username, password)
        self.destroy()
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy()
    
    def get_credentials(self) -> Optional[Tuple[str, str]]:
        """Get the entered credentials."""
        self.wait_window()
        return self.result


class InstagramLoginDialog(LoginDialog):
    """Instagram-specific login dialog."""
    
    def __init__(self, parent):
        """Initialize Instagram login dialog."""
        super().__init__(parent, "Instagram Login", "instagram")


class LinkedInLoginDialog(LoginDialog):
    """LinkedIn-specific login dialog."""
    
    def __init__(self, parent):
        """Initialize LinkedIn login dialog."""
        super().__init__(parent, "LinkedIn Login", "linkedin")
        
        # Add LinkedIn-specific warning
        warning_text = (
            "⚠️  Using unofficial APIs may violate LinkedIn's Terms of Service.\n"
            "Your account could be restricted. Use at your own risk."
        )
        
        warning_label = ttk.Label(
            self.winfo_children()[0],  # main_frame
            text=warning_text,
            font=("Helvetica", 9),
            bootstyle="danger",
            justify=CENTER,
            wraplength=400
        )
        warning_label.pack(after=self.winfo_children()[0].winfo_children()[1], pady=(0, 10))


def show_login_prompt(parent, platform: str) -> Optional[Tuple[str, str]]:
    """
    Show login dialog and return credentials.
    
    Args:
        parent: Parent window
        platform: 'instagram' or 'linkedin'
    
    Returns:
        Tuple of (username, password) or None if cancelled
    """
    if platform == "instagram":
        dialog = InstagramLoginDialog(parent)
    elif platform == "linkedin":
        dialog = LinkedInLoginDialog(parent)
    else:
        raise ValueError(f"Unknown platform: {platform}")
    
    return dialog.get_credentials()
