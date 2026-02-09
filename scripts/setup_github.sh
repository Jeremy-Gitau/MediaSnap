#!/bin/bash
# Setup script for preparing MediaSnap for GitHub

echo "🚀 MediaSnap GitHub Setup"
echo "=========================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo -e "${BLUE}📦 Initializing git repository...${NC}"
    git init
    echo -e "${GREEN}✅ Git initialized${NC}"
    echo ""
else
    echo -e "${GREEN}✅ Git repository already initialized${NC}"
    echo ""
fi

# Check for remote
if ! git remote get-url origin &> /dev/null; then
    echo -e "${YELLOW}❓ No remote repository configured${NC}"
    echo ""
    read -p "Enter your GitHub repository URL (e.g., https://github.com/username/MediaSnap.git): " repo_url
    
    if [ ! -z "$repo_url" ]; then
        git remote add origin "$repo_url"
        echo -e "${GREEN}✅ Remote repository added: $repo_url${NC}"
    fi
    echo ""
else
    origin_url=$(git remote get-url origin)
    echo -e "${GREEN}✅ Remote repository: $origin_url${NC}"
    echo ""
fi

# Install pre-commit hooks (optional)
read -p "❓ Install pre-commit hooks for automatic code quality checks? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v pre-commit &> /dev/null; then
        pre-commit install
        echo -e "${GREEN}✅ Pre-commit hooks installed${NC}"
    else
        echo -e "${BLUE}📦 Installing pre-commit...${NC}"
        pip install pre-commit
        pre-commit install
        echo -e "${GREEN}✅ Pre-commit hooks installed${NC}"
    fi
    echo ""
fi

# Create initial commit if needed
if ! git rev-parse HEAD &> /dev/null; then
    echo -e "${BLUE}📝 Creating initial commit...${NC}"
    
    # Stage all files
    git add .
    
    # Create commit
    git commit -m "Initial commit: MediaSnap - Instagram & YouTube archiver

Features:
- Instagram profile archiving with smart organization
- YouTube channel downloads
- Modern UI with statistics dashboard
- SQLite database for tracking
- Automated Windows builds via GitHub Actions"
    
    echo -e "${GREEN}✅ Initial commit created${NC}"
    echo ""
fi

# Summary
echo "=========================="
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo "=========================="
echo ""
echo "Next steps:"
echo ""
echo "1️⃣  Review files:"
echo "   git status"
echo ""
echo "2️⃣  Push to GitHub:"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3️⃣  Create a release:"
echo "   git tag v1.0.0"
echo "   git push origin v1.0.0"
echo ""
echo "📚 Documentation:"
echo "   - BUILD.md - Build and release instructions"
echo "   - GITHUB_README.md - Copy this to README.md for GitHub"
echo "   - YOUTUBE_SETUP.md - YouTube setup guide"
echo ""
echo "🤖 GitHub Actions will automatically:"
echo "   ✅ Run code quality checks"
echo "   ✅ Build Windows executable"
echo "   ✅ Create releases (on tags)"
echo ""
echo "=========================="
