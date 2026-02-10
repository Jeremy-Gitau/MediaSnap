"""Authentication helpers for Instagram and LinkedIn."""

import asyncio
from pathlib import Path
import pickle
from typing import Optional, Tuple

from mediasnap.utils.config import SESSION_DIR
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


async def authenticate_instagram(username: str, password: str) -> bool:
    """
    Authenticate with Instagram and save session.
    
    Args:
        username: Instagram username/email
        password: Instagram password
    
    Returns:
        True if authentication successful
    """
    try:
        import instaloader
        
        # Create Instaloader instance
        loader = instaloader.Instaloader()
        
        # Login
        loader.login(username, password)
        
        # Save session to centralized location
        session_file = SESSION_DIR / f"{username}_session"
        loader.save_session_to_file(str(session_file))
        
        logger.info(f"✅ Instagram authentication successful for {username}")
        logger.info(f"📁 Session saved to: {session_file}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Instagram authentication failed: {e}")
        return False


async def authenticate_linkedin(email: str, password: str) -> bool:
    """
    Authenticate with LinkedIn and save session.
    
    Args:
        email: LinkedIn email
        password: LinkedIn password
    
    Returns:
        True if authentication successful
    """
    try:
        from linkedin_api import Linkedin
        
        # Authenticate
        api = Linkedin(email, password)
        
        # Save session to centralized location
        session_file = SESSION_DIR / "linkedin_session.pkl"
        
        # Save credentials (encrypted by linkedin-api)
        with open(session_file, "wb") as f:
            pickle.dump({"username": email, "password": password}, f)
        
        # Set secure permissions (Unix-like systems only)
        try:
            session_file.chmod(0o600)
        except Exception:
            pass  # Windows doesn't support chmod
        
        logger.info(f"✅ LinkedIn authentication successful for {email}")
        logger.info(f"📁 Session saved to: {session_file}")
        return True
        
    except Exception as e:
        logger.error(f"❌ LinkedIn authentication failed: {e}")
        return False


def check_instagram_auth() -> bool:
    """Check if Instagram session exists."""
    if not SESSION_DIR.exists():
        return False
    
    # Check if any session files exist
    session_files = list(SESSION_DIR.glob("*_session"))
    if session_files:
        logger.debug(f"Found {len(session_files)} Instagram session file(s)")
        return True
    
    return False


def check_linkedin_auth() -> bool:
    """Check if LinkedIn session exists."""
    session_file = SESSION_DIR / "linkedin_session.pkl"
    return session_file.exists()
