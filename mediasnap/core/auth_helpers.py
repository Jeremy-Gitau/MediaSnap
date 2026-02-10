"""Authentication helpers for Instagram and LinkedIn."""

import asyncio
from pathlib import Path
import pickle
from typing import Optional, Tuple
import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from mediasnap.utils.config import SESSION_DIR
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


def _get_encryption_key() -> bytes:
    """
    Get or create encryption key for credential storage.
    
    Uses a machine-specific key derived from system identifiers.
    Stored in SESSION_DIR/.key for persistence.
    
    Returns:
        Encryption key bytes
    """
    key_file = SESSION_DIR / ".key"
    
    if key_file.exists():
        with open(key_file, "rb") as f:
            return f.read()
    
    # Generate new key using machine-specific salt
    # This ties encryption to this specific machine
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    # Use machine ID as password (machine-specific)
    import platform
    machine_id = f"{platform.node()}{platform.machine()}{platform.system()}".encode()
    key = base64.urlsafe_b64encode(kdf.derive(machine_id))
    
    # Save key and salt together
    with open(key_file, "wb") as f:
        f.write(key)
    
    # Set secure permissions
    try:
        key_file.chmod(0o600)
    except Exception:
        pass  # Windows doesn't support chmod
    
    return key


def _encrypt_data(data: bytes) -> bytes:
    """Encrypt data using Fernet symmetric encryption."""
    key = _get_encryption_key()
    fernet = Fernet(key)
    return fernet.encrypt(data)


def _decrypt_data(encrypted_data: bytes) -> bytes:
    """Decrypt data using Fernet symmetric encryption."""
    key = _get_encryption_key()
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data)


async def authenticate_instagram(username: str, password: str, two_factor_code: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Authenticate with Instagram and save session.
    
    Args:
        username: Instagram username/email
        password: Instagram password
        two_factor_code: Optional 2FA code if required
    
    Returns:
        Tuple of (success, error_message)
        error_message can be 'TWO_FACTOR_REQUIRED' for 2FA prompt
    """
    try:
        import instaloader
        
        # Create Instaloader instance
        loader = instaloader.Instaloader()
        
        # Try login
        try:
            loader.login(username, password)
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            if two_factor_code:
                # Try 2FA login
                loader.two_factor_login(two_factor_code)
            else:
                # Need 2FA code from user
                logger.warning(f"🔐 Two-factor authentication required for {username}")
                return (False, "TWO_FACTOR_REQUIRED")
        
        # Save session to centralized location
        session_file = SESSION_DIR / f"{username}_session"
        loader.save_session_to_file(str(session_file))
        
        # Encrypt and save credentials for future session refresh
        creds_file = SESSION_DIR / f"{username}_creds.enc"
        creds_data = pickle.dumps({"username": username, "password": password})
        encrypted_creds = _encrypt_data(creds_data)
        with open(creds_file, "wb") as f:
            f.write(encrypted_creds)
        
        # Set secure permissions
        try:
            creds_file.chmod(0o600)
            session_file.chmod(0o600)
        except Exception:
            pass
        
        logger.info(f"✅ Instagram authentication successful for {username}")
        logger.info(f"📁 Session saved to: {session_file}")
        return (True, None)
        
    except instaloader.exceptions.BadCredentialsException:
        error_msg = "Invalid username or password"
        logger.error(f"❌ Instagram authentication failed: {error_msg}")
        return (False, error_msg)
    except instaloader.exceptions.ConnectionException as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(f"❌ Instagram authentication failed: {error_msg}")
        return (False, error_msg)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Instagram authentication failed: {error_msg}")
        return (False, error_msg)


async def authenticate_linkedin(email: str, password: str) -> Tuple[bool, Optional[str]]:
    """
    Authenticate with LinkedIn and save encrypted session.
    
    Args:
        email: LinkedIn email
        password: LinkedIn password
    
    Returns:
        Tuple of (success, error_message)
    """
    try:
        from linkedin_api import Linkedin
        
        # Authenticate
        api = Linkedin(email, password)
        
        # Save encrypted credentials to centralized location
        session_file = SESSION_DIR / "linkedin_session.enc"
        
        # Encrypt credentials before saving
        creds_data = pickle.dumps({"username": email, "password": password})
        encrypted_creds = _encrypt_data(creds_data)
        
        with open(session_file, "wb") as f:
            f.write(encrypted_creds)
        
        # Set secure permissions (Unix-like systems only)
        try:
            session_file.chmod(0o600)
        except Exception:
            pass  # Windows doesn't support chmod
        
        logger.info(f"✅ LinkedIn authentication successful for {email}")
        logger.info(f"📁 Encrypted session saved to: {session_file}")
        return (True, None)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ LinkedIn authentication failed: {error_msg}")
        return (False, error_msg)


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
    """Check if LinkedIn encrypted session exists."""
    session_file = SESSION_DIR / "linkedin_session.enc"
    # Also check old format for backward compatibility
    old_session = SESSION_DIR / "linkedin_session.pkl"
    return session_file.exists() or old_session.exists()
