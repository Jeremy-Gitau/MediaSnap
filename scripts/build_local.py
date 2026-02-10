#!/usr/bin/env python3
"""
Local build script for MediaSnap.
Creates a standalone executable for the current platform.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} found")
        return True
    except ImportError:
        print("❌ PyInstaller not found")
        print("📦 Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
        return True


def build_windows():
    """Build Windows executable using spec file."""
    print("\n🏗️  Building Windows executable...")
    print("=" * 50)
    
    spec_file = Path("build_windows.spec")
    if not spec_file.exists():
        print(f"❌ Spec file not found: {spec_file}")
        return False
    
    cmd = ["pyinstaller", str(spec_file), "--clean"]
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        exe_path = Path("dist/MediaSnap.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n✅ Build successful!")
            print(f"📦 Executable: {exe_path}")
            print(f"📊 Size: {size_mb:.1f} MB")
            return True
        else:
            print("\n❌ Build completed but executable not found")
            return False
    else:
        print("\n❌ Build failed")
        return False


def build_linux():
    """Build Linux executable using spec file."""
    print("\n🏗️  Building Linux executable...")
    print("=" * 50)
    
    spec_file = Path("build_linux.spec")
    if not spec_file.exists():
        print(f"❌ Spec file not found: {spec_file}")
        return False
    
    cmd = ["pyinstaller", str(spec_file), "--clean"]
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        exe_path = Path("dist/MediaSnap")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n✅ Build successful!")
            print(f"📦 Executable: {exe_path}")
            print(f"📊 Size: {size_mb:.1f} MB")
            
            # Make executable
            os.chmod(exe_path, 0o755)
            print("✅ Made executable")
            return True
        else:
            print("\n❌ Build completed but executable not found")
            return False
    else:
        print("\n❌ Build failed")
        return False


def build_macos():
    """Build macOS executable using simple approach."""
    print("\n🏗️  Building macOS executable...")
    print("=" * 50)
    
    app_name = "MediaSnap"
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", app_name,
        "app.py",
        "--clean",
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        exe_path = Path(f"dist/{app_name}")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n✅ Build successful!")
            print(f"📦 Executable: {exe_path}")
            print(f"📊 Size: {size_mb:.1f} MB")
            
            # Make executable
            os.chmod(exe_path, 0o755)
            print("✅ Made executable")
            return True
        else:
            print("\n❌ Build completed but executable not found")
            return False
    else:
        print("\n❌ Build failed")
        return False


def main():
    """Main build function."""
    print("🎬 MediaSnap Build Script")
    print("=" * 50)
    print(f"Platform: {platform.system()}")
    print(f"Python: {sys.version.split()[0]}")
    print("=" * 50)
    
    # Check PyInstaller
    if not check_pyinstaller():
        print("❌ Failed to install PyInstaller")
        sys.exit(1)
    
    # Build based on platform
    system = platform.system()
    
    if system == "Windows":
        success = build_windows()
    elif system == "Linux":
        success = build_linux()
    elif system == "Darwin":
        success = build_macos()
    else:
        print(f"❌ Unsupported platform: {system}")
        sys.exit(1)
    
    if success:
        print("\n" + "=" * 50)
        print("🎉 Build complete!")
        print("\nNext steps:")
        
        if system == "Windows":
            print("  1. Test: dist/MediaSnap.exe")
            print("  2. Distribute the executable")
        else:
            print("  1. Test: ./dist/MediaSnap")
            print("  2. Distribute the executable")
        
        print("=" * 50)
        sys.exit(0)
    else:
        print("\n❌ Build failed - check errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()
