#!/bin/bash
#
# MediaSnap VPN Server Setup
# Sets up WireGuard VPN server on Ubuntu 20.04+ (DigitalOcean, AWS, etc.)
# Run this on your VPN server after SSH'ing in
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   MediaSnap WireGuard VPN Server      ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Check if Ubuntu
if ! grep -qi ubuntu /etc/os-release; then
    echo -e "${YELLOW}Warning: This script is designed for Ubuntu. Continue at your own risk.${NC}"
    read -p "Continue? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}[1/7] Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

echo -e "${GREEN}[2/7] Installing WireGuard...${NC}"
apt-get install -y wireguard wireguard-tools qrencode

echo -e "${GREEN}[3/7] Enabling IP forwarding...${NC}"
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
echo "net.ipv6.conf.all.forwarding=1" >> /etc/sysctl.conf
sysctl -p

echo -e "${GREEN}[4/7] Generating server keys...${NC}"
cd /etc/wireguard
umask 077
wg genkey | tee server_privatekey | wg pubkey > server_publickey

SERVER_PRIVATE_KEY=$(cat server_privatekey)
SERVER_PUBLIC_KEY=$(cat server_publickey)

echo -e "${GREEN}[5/7] Detecting network interface...${NC}"
SERVER_INTERFACE=$(ip route | grep default | awk '{print $5}')
echo -e "   Detected interface: ${BLUE}${SERVER_INTERFACE}${NC}"

echo -e "${GREEN}[6/7] Creating WireGuard configuration...${NC}"

# Generate server config
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = ${SERVER_PRIVATE_KEY}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o ${SERVER_INTERFACE} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o ${SERVER_INTERFACE} -j MASQUERADE

# Client configurations will be added below
# [Peer] sections for each client
EOF

echo -e "${GREEN}[7/7] Starting WireGuard...${NC}"
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   VPN Server Setup Complete! ✓         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Server Information:${NC}"
echo -e "  Public Key: ${BLUE}${SERVER_PUBLIC_KEY}${NC}"
echo -e "  Listen Port: ${BLUE}51820${NC}"
echo -e "  Server IP: ${BLUE}10.8.0.1${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Get your server's public IP: ${BLUE}curl -4 ifconfig.me${NC}"
echo -e "  2. Open UDP port 51820 in your firewall"
echo -e "  3. Run the add_vpn_client.sh script to create client configs"
echo ""
echo -e "${RED}IMPORTANT:${NC} Save the server public key above!"
echo ""

# Create client addition script
cat > /root/add_vpn_client.sh << 'EOFCLIENT'
#!/bin/bash
# Add a new VPN client

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <client_name>"
    exit 1
fi

CLIENT_NAME=$1
cd /etc/wireguard

# Find next available IP
LAST_IP=$(grep "AllowedIPs = 10.8.0" wg0.conf | tail -1 | cut -d'.' -f4 | cut -d'/' -f1)
if [ -z "$LAST_IP" ]; then
    NEXT_IP=2
else
    NEXT_IP=$((LAST_IP + 1))
fi

CLIENT_IP="10.8.0.${NEXT_IP}"

# Generate client keys
wg genkey | tee ${CLIENT_NAME}_privatekey | wg pubkey > ${CLIENT_NAME}_publickey

CLIENT_PRIVATE_KEY=$(cat ${CLIENT_NAME}_privatekey)
CLIENT_PUBLIC_KEY=$(cat ${CLIENT_NAME}_publickey)
SERVER_PUBLIC_KEY=$(cat server_publickey)
SERVER_ENDPOINT=$(curl -4 -s ifconfig.me)

# Add peer to server config
cat >> wg0.conf << EOF

[Peer]
# ${CLIENT_NAME}
PublicKey = ${CLIENT_PUBLIC_KEY}
AllowedIPs = ${CLIENT_IP}/32
EOF

# Reload WireGuard
wg syncconf wg0 <(wg-quick strip wg0)

# Create client config
mkdir -p /root/vpn_clients
cat > /root/vpn_clients/${CLIENT_NAME}.conf << EOF
[Interface]
PrivateKey = ${CLIENT_PRIVATE_KEY}
Address = ${CLIENT_IP}/24
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = ${SERVER_PUBLIC_KEY}
Endpoint = ${SERVER_ENDPOINT}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
EOF

echo ""
echo "✓ Client '${CLIENT_NAME}' created successfully!"
echo ""
echo "Client IP: ${CLIENT_IP}"
echo "Config file: /root/vpn_clients/${CLIENT_NAME}.conf"
echo ""
echo "To use on macOS:"
echo "  1. Copy the config file to your Mac"
echo "  2. Run: sudo scripts/connect_vpn.sh ${CLIENT_NAME}.conf"
echo ""

# Generate QR code for mobile
qrencode -t ansiutf8 < /root/vpn_clients/${CLIENT_NAME}.conf
echo ""
echo "Scan QR code above with WireGuard mobile app"

EOFCLIENT

chmod +x /root/add_vpn_client.sh

echo -e "${YELLOW}Client management script created: ${BLUE}/root/add_vpn_client.sh${NC}"
echo -e "Usage: ${BLUE}sudo /root/add_vpn_client.sh mediasnap${NC}"
