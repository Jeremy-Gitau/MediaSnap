#!/bin/bash
# Quick setup script for MediaSnap YouTube support

echo "🎬 MediaSnap YouTube Setup"
echo "=========================="
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "📦 Homebrew not found. Installing Homebrew first..."
    echo ""
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH (for Apple Silicon Macs)
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    
    echo "✅ Homebrew installed!"
    echo ""
else
    echo "✅ Homebrew is already installed"
    echo ""
fi

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "📹 Installing ffmpeg (required for best video quality)..."
    brew install ffmpeg
    echo ""
    echo "✅ ffmpeg installed!"
else
    echo "✅ ffmpeg is already installed"
fi

echo ""

# Optional: Install deno for better YouTube extraction
read -p "❓ Install deno for better YouTube support? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if ! command -v deno &> /dev/null; then
        echo "🦕 Installing deno..."
        brew install deno
        echo "✅ deno installed!"
    else
        echo "✅ deno is already installed"
    fi
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Close MediaSnap if it's running"
echo "2. Restart: python app.py"
echo "3. Try downloading a YouTube channel!"
echo ""
echo "You'll now get the best quality videos! 🚀"
