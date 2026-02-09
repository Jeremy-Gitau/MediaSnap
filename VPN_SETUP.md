# VPN Setup Guide for MediaSnap

## Overview

MediaSnap includes VPN integration to help avoid rate limiting and IP blocking from Instagram, LinkedIn, and other platforms. This guide will help you set up your own WireGuard VPN server and connect MediaSnap through it.

## Why Use a VPN?

- **Avoid IP blocking**: Instagram and LinkedIn may block IPs that make too many requests
- **Rate limiting protection**: Distribute requests across different IPs
- **Privacy**: Keep your scraping activity separate from your personal IP
- **Geographic flexibility**: Access content from different regions

## Architecture

```
MediaSnap (macOS) → WireGuard VPN Client → VPN Server (Cloud) → Instagram/LinkedIn
```

## Quick Start

### 1. Server Setup (One-time)

You'll need a cloud VPS running Ubuntu 20.04+. Recommended providers:
- [DigitalOcean](https://www.digitalocean.com/) - $5-10/month
- [Linode](https://www.linode.com/) - $5-10/month  
- [Vultr](https://www.vultr.com/) - $5-10/month
- AWS EC2 (t2.micro) - May qualify for free tier

**Steps:**

1. **Create a VPS**:
   - Choose Ubuntu 20.04 or 22.04
   - Minimum: 1GB RAM, 1 CPU
   - Note the IP address

2. **SSH into your server**:
   ```bash
   ssh root@YOUR_SERVER_IP
   ```

3. **Download and run the server setup script**:
   ```bash
   # Download from your MediaSnap repository
   curl -O https://raw.githubusercontent.com/YOUR_USERNAME/MediaSnap/main/scripts/setup_vpn_server.sh
   
   # Or if you have the repo locally, scp it:
   # scp scripts/setup_vpn_server.sh root@YOUR_SERVER_IP:/root/
   
   # Run the setup script
   sudo bash setup_vpn_server.sh
   ```

4. **Open firewall port** (if applicable):
   ```bash
   # UFW (Ubuntu)
   sudo ufw allow 51820/udp
   sudo ufw enable
   ```

5. **Create a client configuration**:
   ```bash
   sudo /root/add_vpn_client.sh mediasnap
   ```
   
   This creates a config file: `/root/vpn_clients/mediasnap.conf`

### 2. Client Setup (macOS)

1. **Run the client setup script**:
   ```bash
   cd /path/to/MediaSnap
   chmod +x scripts/setup_vpn_client.sh
   ./scripts/setup_vpn_client.sh
   ```

2. **Copy the VPN config from your server**:
   ```bash
   scp root@YOUR_SERVER_IP:/root/vpn_clients/mediasnap.conf ~/.mediasnap/vpn/
   ```

3. **Connect to VPN**:
   ```bash
   sudo scripts/connect_vpn.sh connect mediasnap.conf
   ```

4. **Test the connection**:
   ```bash
   sudo scripts/connect_vpn.sh test
   ```

## Usage

### Manual VPN Connection

Connect before running MediaSnap:

```bash
# Connect
sudo scripts/connect_vpn.sh connect mediasnap.conf

# Run MediaSnap
python app.py

# Disconnect when done
sudo scripts/connect_vpn.sh disconnect
```

### Using the VPN Helper (Python)

```bash
# Connect
python scripts/vpn_helper.py connect

# Check status
python scripts/vpn_helper.py status

# Test connection
python scripts/vpn_helper.py test

# Disconnect
python scripts/vpn_helper.py disconnect
```

### VPN Commands Reference

#### connect_vpn.sh

```bash
# Connect to VPN
sudo scripts/connect_vpn.sh connect <config_file>
sudo scripts/connect_vpn.sh connect mediasnap.conf

# Disconnect
sudo scripts/connect_vpn.sh disconnect

# Show status
sudo scripts/connect_vpn.sh status

# Test connection
sudo scripts/connect_vpn.sh test
```

#### vpn_helper.py

```bash
# Connect (uses default config)
python scripts/vpn_helper.py connect

# Connect with specific config
python scripts/vpn_helper.py connect other-vpn.conf

# Get status
python scripts/vpn_helper.py status

# Test connection
python scripts/vpn_helper.py test

# Disconnect
python scripts/vpn_helper.py disconnect
```

## Advanced Configuration

### Multiple VPN Servers

You can set up multiple VPN servers in different regions and switch between them:

1. **Create configs on different servers**:
   ```bash
   # Server 1 (US)
   ssh root@us-server
   sudo /root/add_vpn_client.sh mediasnap-us
   
   # Server 2 (EU)
   ssh root@eu-server
   sudo /root/add_vpn_client.sh mediasnap-eu
   ```

2. **Copy all configs**:
   ```bash
   scp root@us-server:/root/vpn_clients/mediasnap-us.conf ~/.mediasnap/vpn/
   scp root@eu-server:/root/vpn_clients/mediasnap-eu.conf ~/.mediasnap/vpn/
   ```

3. **Switch between them**:
   ```bash
   sudo scripts/connect_vpn.sh connect mediasnap-us.conf
   # Or
   sudo scripts/connect_vpn.sh connect mediasnap-eu.conf
   ```

### Split Tunneling

If you only want Instagram/LinkedIn traffic through VPN (not all traffic):

Edit your client config (`~/.mediasnap/vpn/mediasnap.conf`):

```ini
[Interface]
PrivateKey = YOUR_PRIVATE_KEY
Address = 10.8.0.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = SERVER_PUBLIC_KEY
Endpoint = YOUR_SERVER_IP:51820
# Instead of 0.0.0.0/0, route only specific IPs:
AllowedIPs = 157.240.0.0/16, 31.13.0.0/16  # Instagram IP ranges
PersistentKeepalive = 25
```

### Managing Multiple Clients

On the server, you can add as many clients as needed:

```bash
# Add more clients
sudo /root/add_vpn_client.sh laptop
sudo /root/add_vpn_client.sh phone
sudo /root/add_vpn_client.sh tablet

# Each gets a unique IP: 10.8.0.2, 10.8.0.3, etc.
```

## Troubleshooting

### "Permission denied" when connecting

VPN operations require sudo privileges. Make sure you're using `sudo`:

```bash
sudo scripts/connect_vpn.sh connect mediasnap.conf
```

### Connection fails / No internet after connecting

1. **Check server is running**:
   ```bash
   ssh root@YOUR_SERVER_IP
   sudo systemctl status wg-quick@wg0
   ```

2. **Verify firewall allows UDP port 51820**:
   ```bash
   sudo ufw status
   ```

3. **Check IP forwarding on server**:
   ```bash
   sysctl net.ipv4.ip_forward
   # Should return: net.ipv4.ip_forward = 1
   ```

### Can't find WireGuard command

Install WireGuard:

```bash
brew install wireguard-tools
```

### VPN connects but still getting 403 errors

1. **Test your VPN IP**:
   ```bash
   # Before VPN
   curl ifconfig.me
   
   # After VPN
   sudo scripts/connect_vpn.sh connect mediasnap.conf
   curl ifconfig.me  # Should show different IP
   ```

2. **Wait between download attempts**: Instagram may still rate-limit even with VPN
3. **Try a different VPN server location**: Set up in a different region
4. **Use residential VPN**: Cloud VPS IPs may still be blocked; consider residential proxies

### Config file not found

Ensure you copied the config to the correct location:

```bash
ls -la ~/.mediasnap/vpn/
# Should show mediasnap.conf
```

### Server setup script fails

Common issues:

1. **Not running as root**: Use `sudo bash setup_vpn_server.sh`
2. **Firewall blocking**: Open UDP port 51820
3. **Old Ubuntu version**: Use Ubuntu 20.04 or newer

## Security Considerations

### Server Security

1. **Use SSH keys** instead of passwords:
   ```bash
   ssh-copy-id root@YOUR_SERVER_IP
   ```

2. **Disable password authentication** in `/etc/ssh/sshd_config`:
   ```
   PasswordAuthentication no
   ```

3. **Keep the server updated**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

4. **Consider fail2ban**:
   ```bash
   sudo apt install fail2ban
   ```

### Config File Security

Config files contain private keys. Protect them:

```bash
# Correct permissions
chmod 600 ~/.mediasnap/vpn/*.conf

# Backup securely
tar -czf vpn-configs-backup.tar.gz ~/.mediasnap/vpn/
gpg -c vpn-configs-backup.tar.gz  # Encrypt with password
rm vpn-configs-backup.tar.gz
```

### VPN Server Logs

Monitor your VPN server for unusual activity:

```bash
# On server
sudo journalctl -u wg-quick@wg0 -f

# Check connected clients
sudo wg show
```

## Cost Estimates

| Provider | Server Type | Cost/Month | Best For |
|----------|-------------|------------|----------|
| DigitalOcean | Basic Droplet (1GB) | $6 | General use |
| Linode | Nanode (1GB) | $5 | Budget |
| Vultr | Cloud Compute (1GB) | $5 | Performance |
| AWS EC2 | t2.micro | Free tier* | Testing |

*AWS free tier: 750 hours/month for 12 months

### Data Transfer Costs

Most MediaSnap downloads are small:
- Profile data: ~1-10MB
- Images: ~100KB-2MB each
- Videos: ~5-50MB each

Example: 1000 posts/month ≈ 2-5GB transfer (well within most free tiers)

## Alternative: Commercial VPN Services

If you don't want to manage your own server, commercial VPNs work too:

1. **NordVPN, ExpressVPN, etc.** - Get OpenVPN/WireGuard configs
2. **Download their config file**
3. **Use with MediaSnap**:
   ```bash
   sudo scripts/connect_vpn.sh connect nordvpn-us.conf
   ```

**Pros**: Easy, multiple locations, better IPs
**Cons**: Recurring cost ($10-15/month), shared IPs may still be blocked

## FAQ

**Q: Do I need a VPN to use MediaSnap?**  
A: No, but it helps avoid IP blocking, especially for heavy usage.

**Q: Can I use MediaSnap without connecting to VPN every time?**  
A: Yes, VPN is optional. Connect only when needed.

**Q: Will VPN slow down MediaSnap?**  
A: Slightly, but the overhead is minimal for downloading posts/images. Expect <10% slowdown.

**Q: Can I use the same VPN for browsing?**  
A: Yes, your entire internet traffic goes through VPN when connected.

**Q: How many downloads can I do before getting blocked?**  
A: Varies by platform. Instagram typically allows 100-200 posts/hour. With VPN, you can rotate IPs.

**Q: Is this legal?**  
A: Running a VPN server is legal. However, using it to bypass rate limits may violate platform ToS. See [README.md](../README.md) for terms of service warnings.

## Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review server logs: `sudo journalctl -u wg-quick@wg0`
3. Test without VPN to isolate the issue
4. Open a GitHub issue with detailed error messages

## Additional Resources

- [WireGuard Official Docs](https://www.wireguard.com/)
- [DigitalOcean VPN Tutorial](https://www.digitalocean.com/community/tutorials/how-to-set-up-wireguard-on-ubuntu-20-04)
- [macOS WireGuard Guide](https://www.wireguard.com/install/)
