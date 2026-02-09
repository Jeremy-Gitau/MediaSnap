# 📸 MediaSnap

> Archive Instagram profiles and YouTube channels with style!

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)
![Build](https://img.shields.io/github/actions/workflow/status/YOUR_USERNAME/MediaSnap/build-release.yml?branch=main)

</div>

## ✨ Features

- 📸 **Instagram Archiving** - Download public profile posts with smart organization
  - Automatic categorization: `reels/`, `images/`, `carousel/`, `tagged/`
  - Incremental updates (only downloads new content)
  - Full metadata preservation

- 📺 **YouTube Channel Downloads** - Archive entire YouTube channels
  - High-quality video downloads
  - Organized by video title
  - Progress tracking for each video

- 🎨 **Beautiful Modern UI** - Built with ttkbootstrap
  - Real-time statistics dashboard
  - Animated progress bars
  - Completion dialogs with instant folder access

- 💾 **Smart Storage** - SQLite database tracking
  - Avoid duplicate downloads
  - Track download history
  - Efficient local storage

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/MediaSnap.git
cd MediaSnap

# Install dependencies
pip install -r requirements.txt

# (Optional) For YouTube best quality
brew install ffmpeg  # macOS
# or run: ./setup_youtube.sh

# (Required for Instagram) Login once
python login.py
```

### Run

```bash
python app.py
```

## 📦 Download Pre-built Executable

**Windows users** can download the ready-to-use executable:

1. Go to [Releases](https://github.com/YOUR_USERNAME/MediaSnap/releases)
2. Download `MediaSnap.exe`
3. Run it - no installation needed!

## 🛠️ Development

### Build from Source

```bash
# Build executable locally
python build_local.py

# Or manually with PyInstaller
pip install pyinstaller
pyinstaller build_windows.spec
```

### Code Quality

```bash
# Install development tools
pip install black flake8 isort pre-commit

# Set up pre-commit hooks
pre-commit install

# Format code
black mediasnap/ app.py
isort mediasnap/ app.py

# Lint
flake8 mediasnap/ app.py
```

### CI/CD Pipeline

The project uses GitHub Actions for:
- ✅ Automated code quality checks
- ✅ Building Windows executables
- ✅ Creating releases with executables
- ✅ Running tests

See [BUILD.md](BUILD.md) for details.

## 📂 Project Structure

```
MediaSnap/
├── mediasnap/           # Main application package
│   ├── core/           # Business logic
│   │   ├── scraper.py
│   │   ├── downloader.py
│   │   └── youtube_downloader.py
│   ├── ui/             # User interface
│   ├── storage/        # Database layer
│   ├── models/         # Data models
│   └── utils/          # Utilities
├── .github/
│   └── workflows/      # CI/CD pipelines
├── app.py              # Application entry point
├── requirements.txt    # Python dependencies
└── build_windows.spec  # PyInstaller configuration
```

## 🔧 Configuration

### Instagram Login

For Instagram downloads, you need to authenticate once:

```bash
python login.py
```

This saves a session file to avoid 403 errors. Safe and secure - your password is NOT stored.

### YouTube Setup

For best quality YouTube downloads (optional):

```bash
# macOS
brew install ffmpeg deno

# Or use our setup script
./setup_youtube.sh
```

See [YOUTUBE_SETUP.md](YOUTUBE_SETUP.md) for details.

## 🎯 Usage Examples

### Instagram Profile
```
Input: uber
       @uber
       https://instagram.com/uber
```

### YouTube Channel
```
Input: https://www.youtube.com/@MrBeast
       https://www.youtube.com/c/ChannelName
```

## 📊 Download Organization

```
downloads/
├── instagram_username/
│   ├── reels/           # Video reels
│   ├── images/          # Single images
│   ├── carousel/        # Multi-image posts
│   └── tagged/          # Posts with hashtags
└── youtube/
    └── channel_name/
        ├── Video Title 1.mp4
        └── Video Title 2.mp4
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run code quality checks
5. Submit a pull request

Code quality tools run automatically on push.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

- **Instagram**: Only works with public profiles. Respects Instagram's Terms of Service.
- **YouTube**: For personal archival use. Respect content creators' rights.
- **Rate Limits**: Instagram may rate-limit requests. Use responsibly.

## 🙏 Acknowledgments

- [instaloader](https://github.com/instaloader/instaloader) - Instagram scraping
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube downloading
- [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) - Beautiful UI
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM

## 📧 Support

For issues or questions:
- [Open an issue](https://github.com/YOUR_USERNAME/MediaSnap/issues)
- Check [BUILD.md](BUILD.md) for build troubleshooting
- See [YOUTUBE_SETUP.md](YOUTUBE_SETUP.md) for YouTube setup help

---

<div align="center">
Made with ❤️ by YOUR_NAME
</div>
