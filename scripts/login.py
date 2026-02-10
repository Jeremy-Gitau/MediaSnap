#!/usr/bin/env python3
"""
Login to Instagram and save session for MediaSnap.

This creates a session file that allows MediaSnap to access Instagram
without getting 403 errors. You only need to run this once.
"""

import getpass
import sys
from pathlib import Path

# Add parent directory to path to import mediasnap
sys.path.insert(0, str(Path(__file__).parent.parent))

import instaloader
from mediasnap.utils.config import SESSION_DIR


def login():
    """Login to Instagram and save session."""
    print("\n" + "="*60)
    print("MediaSnap - Instagram Login")
    print("="*60)
    print("\nThis will save your Instagram session to avoid 403 errors.")
    print("Your password is NOT saved - only the session cookie.")
    print(f"\nSession will be saved to: {SESSION_DIR}")
    print("\n" + "="*60 + "\n")
    
    # Get credentials
    username = input("Instagram username: ").strip()
    if not username:
        print("❌ Username required")
        sys.exit(1)
    
    password = getpass.getpass("Instagram password: ")
    if not password:
        print("❌ Password required")
        sys.exit(1)
    
    print("\n🔄 Logging in...")
    
    try:
        # Create loader
        loader = instaloader.Instaloader(
            quiet=False,
        )
        
        # Login
        loader.login(username, password)
        
        # Save session
        session_file = SESSION_DIR / f"{username}_session"
        loader.save_session_to_file(str(session_file))
        
        print(f"\n✅ SUCCESS! Session saved to: {session_file}")
        print(f"\n📝 MediaSnap will now use this session automatically.")
        print(f"   Session file: {session_file}\n")
        
    except instaloader.exceptions.BadCredentialsException:
        print("\n❌ ERROR: Invalid username or password")
        sys.exit(1)
    
    except instaloader.exceptions.TwoFactorAuthRequiredException:
        print("\n🔐 Two-factor authentication required")
        code = input("Enter 2FA code: ").strip()
        
        try:
            loader.two_factor_login(code)
            session_file = SESSION_DIR / f"{username}_session"
            loader.save_session_to_file(str(session_file))
            print(f"\n✅ SUCCESS! Session saved to: {session_file}\n")
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    login()
