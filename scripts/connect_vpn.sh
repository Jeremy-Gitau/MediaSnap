#!/bin/bash
#
# MediaSnap VPN Connection Manager (macOS)
# Connects/disconnects WireGuard VPN for MediaSnap usage
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

VPN_CONFIG_DIR="$HOME/.mediasnap/vpn"
VPN_INTERFACE="utun99"

# Check if WireGuard is installed
check_wireguard() {
    if ! command -v wg &> /dev/null && ! command -v wireguard-go &> /dev/null; then
        echo -e "${RED}WireGuard is not installed!${NC}"
        echo ""
        echo "Install WireGuard on macOS:"
        echo -e "  ${BLUE}brew install wireguard-tools${NC}"
        echo "  OR download from: https://www.wireguard.com/install/"
        exit 1
    fi
}

# Show usage
show_usage() {
    echo -e "${BLUE}MediaSnap VPN Connection Manager${NC}"
    echo ""
    echo "Usage:"
    echo -e "  ${GREEN}$0 connect <config_file>${NC}    - Connect to VPN"
    echo -e "  ${GREEN}$0 disconnect${NC}               - Disconnect from VPN"
    echo -e "  ${GREEN}$0 status${NC}                   - Show VPN status"
    echo -e "  ${GREEN}$0 test${NC}                     - Test VPN connection"
    echo ""
    echo "Examples:"
    echo -e "  ${BLUE}$0 connect mediasnap.conf${NC}"
    echo -e "  ${BLUE}$0 connect ~/.mediasnap/vpn/mediasnap.conf${NC}"
}

# Connect to VPN
vpn_connect() {
    local CONFIG_FILE="$1"
    
    # Find config file
    if [ ! -f "$CONFIG_FILE" ]; then
        # Try in VPN config dir
        if [ -f "$VPN_CONFIG_DIR/$CONFIG_FILE" ]; then
            CONFIG_FILE="$VPN_CONFIG_DIR/$CONFIG_FILE"
        else
            echo -e "${RED}Config file not found: $CONFIG_FILE${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}Connecting to VPN...${NC}"
    echo -e "Config: ${BLUE}$CONFIG_FILE${NC}"
    
    # Check if already connected
    if sudo wg show $VPN_INTERFACE &> /dev/null; then
        echo -e "${YELLOW}VPN is already connected. Disconnecting first...${NC}"
        vpn_disconnect
        sleep 2
    fi
    
    # Create VPN interface and connect
    sudo wg-quick up "$CONFIG_FILE"
    
    echo ""
    echo -e "${GREEN}✓ VPN Connected!${NC}"
    vpn_status
}

# Disconnect from VPN
vpn_disconnect() {
    echo -e "${YELLOW}Disconnecting from VPN...${NC}"
    
    # Find active WireGuard interfaces
    ACTIVE_INTERFACES=$(sudo wg show interfaces 2>/dev/null || echo "")
    
    if [ -z "$ACTIVE_INTERFACES" ]; then
        echo -e "${YELLOW}No active VPN connections${NC}"
        return 0
    fi
    
    # Disconnect each interface
    for iface in $ACTIVE_INTERFACES; do
        echo -e "Disconnecting ${BLUE}$iface${NC}..."
        sudo wg-quick down "$iface" 2>/dev/null || true
    done
    
    echo -e "${GREEN}✓ VPN Disconnected${NC}"
}

# Show VPN status
vpn_status() {
    echo ""
    echo -e "${BLUE}═══ VPN Status ═══${NC}"
    
    if ! sudo wg show &> /dev/null; then
        echo -e "${YELLOW}VPN is not connected${NC}"
        return 0
    fi
    
    sudo wg show
    
    echo ""
    echo -e "${BLUE}═══ Public IP ═══${NC}"
    curl -s -4 ifconfig.me
    echo ""
}

# Test VPN connection
vpn_test() {
    echo -e "${BLUE}Testing VPN connection...${NC}"
    echo ""
    
    # Check if connected
    if ! sudo wg show &> /dev/null; then
        echo -e "${RED}✗ VPN is not connected${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ VPN interface is active${NC}"
    
    # Test connectivity
    echo -e "\n${BLUE}Testing connectivity...${NC}"
    if ping -c 3 1.1.1.1 &> /dev/null; then
        echo -e "${GREEN}✓ Internet connectivity OK${NC}"
    else
        echo -e "${RED}✗ No internet connectivity${NC}"
        exit 1
    fi
    
    # Show current IP
    echo -e "\n${BLUE}Current public IP:${NC}"
    CURRENT_IP=$(curl -s -4 ifconfig.me)
    echo -e "${GREEN}${CURRENT_IP}${NC}"
    
    # Test Instagram connectivity
    echo -e "\n${BLUE}Testing Instagram access...${NC}"
    if curl -s -o /dev/null -w "%{http_code}" https://www.instagram.com/ | grep -q "200"; then
        echo -e "${GREEN}✓ Instagram is accessible${NC}"
    else
        echo -e "${YELLOW}⚠ Instagram returned non-200 status${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}VPN test complete!${NC}"
}

# Setup VPN config directory
setup_config_dir() {
    if [ ! -d "$VPN_CONFIG_DIR" ]; then
        mkdir -p "$VPN_CONFIG_DIR"
        chmod 700 "$VPN_CONFIG_DIR"
        echo -e "${GREEN}Created VPN config directory: ${BLUE}$VPN_CONFIG_DIR${NC}"
    fi
}

# Main
main() {
    check_wireguard
    setup_config_dir
    
    case "${1:-}" in
        connect)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Config file required${NC}"
                echo ""
                show_usage
                exit 1
            fi
            vpn_connect "$2"
            ;;
        disconnect)
            vpn_disconnect
            ;;
        status)
            vpn_status
            ;;
        test)
            vpn_test
            ;;
        *)
            show_usage
            ;;
    esac
}

main "$@"
