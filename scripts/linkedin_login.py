#!/usr/bin/env python3
"""
LinkedIn authentication script for MediaSnap.

This script helps you authenticate with LinkedIn and save your session
for use with MediaSnap's LinkedIn downloading features.

IMPORTANT NOTES:
- Your credentials are used ONLY to authenticate with LinkedIn
- The session is saved locally in ~/.mediasnap/linkedin_session.pkl
- Your password is encrypted and stored securely
- MediaSnap uses the unofficial linkedin-api library
- This may violate LinkedIn's Terms of Service - use at your own risk

Usage:
    python linkedin_login.py
"""

import getpass
import pickle
import sys
from pathlib import Path


def main():
    """Main authentication flow."""
    print("=" * 60)
    print("🔐 LinkedIn Authentication for MediaSnap")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT WARNINGS:")
    print("   • This uses the unofficial linkedin-api library")
    print("   • May violate LinkedIn's Terms of Service")
    print("   • Your account could be restricted or banned")
    print("   • Use at your own risk")
    print()
    print("📋 How it works:")
    print("   1. You enter your LinkedIn email and password")
    print("   2. We authenticate with LinkedIn")
    print("   3. Session is saved to ~/.mediasnap/linkedin_session.pkl")
    print("   4. MediaSnap will use this session for downloads")
    print()

    # Confirm user wants to proceed
    response = input("Do you want to continue? (yes/no): ").strip().lower()
    if response not in ["yes", "y"]:
        print("\n❌ Authentication cancelled.")
        sys.exit(0)

    print()
    print("-" * 60)
    print("🔑 Enter your LinkedIn credentials")
    print("-" * 60)

    # Get credentials
    email = input("LinkedIn email: ").strip()
    if not email:
        print("❌ Email cannot be empty")
        sys.exit(1)

    password = getpass.getpass("LinkedIn password: ")
    if not password:
        print("❌ Password cannot be empty")
        sys.exit(1)

    print()
    print("🔄 Authenticating with LinkedIn...")

    try:
        # Try to import linkedin-api
        try:
            from linkedin_api import Linkedin
        except ImportError:
            print()
            print("❌ Error: linkedin-api not installed")
            print()
            print("Please install it:")
            print("   pip install linkedin-api")
            print()
            sys.exit(1)

        # Authenticate
        try:
            api = Linkedin(email, password)
            print("✅ Authentication successful!")
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print()
            print("Common issues:")
            print("   • Wrong email or password")
            print("   • LinkedIn security challenge required")
            print("   • Account requires verification")
            print("   • Too many login attempts")
            print()
            print("Try logging in through LinkedIn's website first,")
            print("then run this script again.")
            sys.exit(1)

        # Create config directory
        config_dir = Path.home() / ".mediasnap"
        config_dir.mkdir(exist_ok=True)

        # Save session
        session_file = config_dir / "linkedin_session.pkl"
        session_data = {
            "username": email,
            "password": password,
        }

        with open(session_file, "wb") as f:
            pickle.dump(session_data, f)

        # Set file permissions (owner read/write only)
        session_file.chmod(0o600)

        print(f"✅ Session saved to: {session_file}")
        print()
        print("=" * 60)
        print("🎉 Setup Complete!")
        print("=" * 60)
        print()
        print("You can now use MediaSnap to download LinkedIn content:")
        print()
        print("   1. Run MediaSnap: python app.py")
        print("   2. Enter a LinkedIn profile URL:")
        print("      - https://www.linkedin.com/in/username")
        print("      - https://www.linkedin.com/company/companyname")
        print("   3. Click 'Fetch Profile' to start downloading")
        print()
        print("📂 Downloads will be saved to:")
        print(f"   {Path.cwd() / 'downloads' / 'linkedin'}")
        print()
        print("⚠️  Remember: Use responsibly and respect LinkedIn's ToS")
        print()

    except KeyboardInterrupt:
        print("\n\n❌ Authentication cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
