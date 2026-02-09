#!/usr/bin/env python3
"""
MediaSnap VPN Integration
Automatically manages VPN connection for MediaSnap downloads
"""

import os
import subprocess
import sys
from pathlib import Path


class VPNManager:
    """Manages VPN connection for MediaSnap."""

    def __init__(self):
        """Initialize VPN manager."""
        self.scripts_dir = Path(__file__).parent
        self.vpn_script = self.scripts_dir / "connect_vpn.sh"
        self.config_dir = Path.home() / ".mediasnap" / "vpn"
        self.default_config = "mediasnap.conf"

    def is_vpn_available(self) -> bool:
        """Check if VPN is configured."""
        try:
            result = subprocess.run(
                ["which", "wg"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def is_connected(self) -> bool:
        """Check if VPN is currently connected."""
        try:
            result = subprocess.run(
                ["sudo", "-n", "wg", "show"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False

    def connect(self, config_name: str = None) -> bool:
        """
        Connect to VPN.

        Args:
            config_name: VPN config file name (default: mediasnap.conf)

        Returns:
            True if connected successfully
        """
        if not self.is_vpn_available():
            print("⚠️  WireGuard not installed. Run: scripts/setup_vpn_client.sh")
            return False

        config_name = config_name or self.default_config
        config_path = self.config_dir / config_name

        if not config_path.exists():
            print(f"❌ VPN config not found: {config_path}")
            print("\nSetup instructions:")
            print("  1. Run: scripts/setup_vpn_client.sh")
            print("  2. Follow the steps to get your VPN config")
            return False

        try:
            print(f"🔐 Connecting to VPN ({config_name})...")
            result = subprocess.run(
                ["sudo", str(self.vpn_script), "connect", str(config_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print("✅ VPN connected successfully!")
                return True
            else:
                print(f"❌ VPN connection failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ VPN connection timed out")
            return False
        except Exception as e:
            print(f"❌ VPN connection error: {e}")
            return False

    def disconnect(self) -> bool:
        """
        Disconnect from VPN.

        Returns:
            True if disconnected successfully
        """
        if not self.is_connected():
            print("ℹ️  VPN is not connected")
            return True

        try:
            print("🔓 Disconnecting from VPN...")
            result = subprocess.run(
                ["sudo", str(self.vpn_script), "disconnect"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print("✅ VPN disconnected successfully")
                return True
            else:
                print(f"❌ VPN disconnection failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ VPN disconnection error: {e}")
            return False

    def status(self) -> dict:
        """
        Get VPN status.

        Returns:
            Dictionary with VPN status information
        """
        return {
            "available": self.is_vpn_available(),
            "connected": self.is_connected(),
            "config_dir": str(self.config_dir),
        }

    def test(self) -> bool:
        """
        Test VPN connection.

        Returns:
            True if VPN is working correctly
        """
        if not self.is_connected():
            print("❌ VPN is not connected")
            return False

        try:
            result = subprocess.run(
                ["sudo", str(self.vpn_script), "test"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            print(result.stdout)
            return result.returncode == 0

        except Exception as e:
            print(f"❌ VPN test error: {e}")
            return False


def main():
    """CLI interface for VPN manager."""
    vpn = VPNManager()

    if len(sys.argv) < 2:
        print("MediaSnap VPN Manager")
        print("\nUsage:")
        print("  python vpn_helper.py connect [config_name]  - Connect to VPN")
        print("  python vpn_helper.py disconnect             - Disconnect from VPN")
        print("  python vpn_helper.py status                 - Show VPN status")
        print("  python vpn_helper.py test                   - Test VPN connection")
        print("\nExamples:")
        print("  python vpn_helper.py connect")
        print("  python vpn_helper.py connect my_vpn.conf")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "connect":
        config = sys.argv[2] if len(sys.argv) > 2 else None
        success = vpn.connect(config)
        sys.exit(0 if success else 1)

    elif command == "disconnect":
        success = vpn.disconnect()
        sys.exit(0 if success else 1)

    elif command == "status":
        status = vpn.status()
        print("\n📊 VPN Status")
        print("─" * 40)
        print(f"WireGuard installed: {'✅' if status['available'] else '❌'}")
        print(f"VPN connected:       {'✅' if status['connected'] else '❌'}")
        print(f"Config directory:    {status['config_dir']}")
        sys.exit(0)

    elif command == "test":
        success = vpn.test()
        sys.exit(0 if success else 1)

    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
