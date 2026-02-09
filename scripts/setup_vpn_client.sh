#!/bin/bash
#
# MediaSnap - macOS VPN Client Setup
# Installs WireGuard and prepares VPN client configuration
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   MediaSnap VPN Client Setup (macOS)  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo -e "${RED}Homebrew is not installed!${NC}"
    echo ""
    echo "Install Homebrew first:"
    echo -e "${BLUE}/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"${NC}"
    exit 1
fi

echo -e "${GREEN}[1/4] Checking WireGuard installation...${NC}"

if command -v wg &> /dev/null; then
    echo -e "${YELLOW}WireGuard is already installed ✓${NC}"
    wg --version
else
    echo -e "${BLUE}Installing WireGuard...${NC}"
    brew install wireguard-tools
    echo -e "${GREEN}✓ WireGuard installed${NC}"
fi

echo ""
echo -e "${GREEN}[2/4] Creating VPN config directory...${NC}"

VPN_CONFIG_DIR="$HOME/.mediasnap/vpn"
mkdir -p "$VPN_CONFIG_DIR"
chmod 700 "$VPN_CONFIG_DIR"

echo -e "${GREEN}✓ Config directory: ${BLUE}$VPN_CONFIG_DIR${NC}"

echo ""
echo -e "${GREEN}[3/4] Making VPN scripts executable...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "$SCRIPT_DIR/connect_vpn.sh"

echo -e "${GREEN}✓ Scripts ready${NC}"

echo ""
echo -e "${GREEN}[4/4] Testing installation...${NC}"

if wg --version &> /dev/null; then
    echo -e "${GREEN}✓ WireGuard is working correctly${NC}"
else
    echo -e "${RED}✗ WireGuard installation may have issues${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   VPN Client Setup Complete! ✓         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "${BLUE}1. Set up your VPN server:${NC}"
echo -e "   • Get a Ubuntu VPS (DigitalOcean, AWS, Linode, etc.)"
echo -e "   • SSH into your server"
echo -e "   • Run: ${YELLOW}curl -O <this repo>/scripts/setup_vpn_server.sh${NC}"
echo -e "   • Run: ${YELLOW}sudo bash setup_vpn_server.sh${NC}"
echo ""
echo -e "${BLUE}2. Create client config on server:${NC}"
echo -e "   ${YELLOW}sudo /root/add_vpn_client.sh mediasnap${NC}"
echo ""
echo -e "${BLUE}3. Copy config to your Mac:${NC}"
echo -e "   ${YELLOW}scp root@YOUR_SERVER:/root/vpn_clients/mediasnap.conf $VPN_CONFIG_DIR/${NC}"
echo ""
echo -e "${BLUE}4. Connect to VPN:${NC}"
echo -e "   ${YELLOW}sudo $SCRIPT_DIR/connect_vpn.sh connect mediasnap.conf${NC}"
echo ""
echo -e "${BLUE}5. Test connection:${NC}"
echo -e "   ${YELLOW}sudo $SCRIPT_DIR/connect_vpn.sh test${NC}"
echo ""
echo -e "${RED}Note: VPN connection requires sudo privileges${NC}"
echo ""
