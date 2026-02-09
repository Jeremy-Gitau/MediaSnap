# Building MediaSnap

## Automated Builds (GitHub Actions)

MediaSnap automatically builds Windows executables when you push to GitHub:

### On Every Push to `main`:
- ✅ Runs code quality checks (black, flake8, isort)
- ✅ Builds Windows executable
- ✅ Runs basic tests
- 📦 Uploads executable as artifact (available for 30 days)

### On Version Tags (e.g., `v1.0.0`):
- 🎉 Creates a GitHub Release
- 📦 Attaches Windows executable to the release
- 📝 Auto-generates release notes

## Creating a Release

To create a release with executable:

```bash
# Tag your version
git tag v1.0.0

# Push the tag
git push origin v1.0.0
```

GitHub Actions will automatically:
1. Build the Windows executable
2. Create a release page
3. Upload the executable as `MediaSnap.exe`

## Manual Building (Local)

### Prerequisites
```bash
pip install pyinstaller
```

### Build on Windows
```bash
python build_local.py
```

Or manually:
```bash
pyinstaller build_windows.spec
```

The executable will be in `dist/MediaSnap.exe`

### Build on macOS/Linux
```bash
pyinstaller --onefile --windowed --name MediaSnap app.py
```

## Code Quality

Run code formatting and checks locally:

```bash
# Install dev dependencies
pip install black flake8 isort

# Format code
black mediasnap/ app.py

# Sort imports
isort mediasnap/ app.py

# Lint code
flake8 mediasnap/ app.py
```

## Workflow Files

- `.github/workflows/build-release.yml` - Main CI/CD pipeline
- `build_windows.spec` - PyInstaller configuration
- `pyproject.toml` - Code formatting configuration
- `.gitignore` - Files to exclude from git

## Troubleshooting

### Build fails on GitHub Actions
- Check the Actions tab for error logs
- Ensure all dependencies are in `requirements.txt`
- Test the build locally first

### Executable doesn't run
- Make sure all hidden imports are in `build_windows.spec`
- Check that assets are included in `datas`
- Test on a clean Windows machine

### Code quality checks fail
- Run `black mediasnap/ app.py` to auto-format
- Run `isort mediasnap/ app.py` to fix imports
- Fix any flake8 errors manually
