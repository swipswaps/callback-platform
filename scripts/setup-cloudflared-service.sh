#!/bin/bash
# Setup Cloudflare Tunnel as a systemd service
# This ensures the tunnel auto-starts on boot and runs in background

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}━━━ Cloudflare Tunnel Service Setup ━━━${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Do NOT run this script as root${NC}"
    echo -e "${YELLOW}Run as regular user: ./scripts/setup-cloudflared-service.sh${NC}"
    exit 1
fi

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}❌ cloudflared not found${NC}"
    echo -e "${YELLOW}Install with: curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared${NC}"
    exit 1
fi

# Check if tunnel exists
TUNNEL_ID="b6d4e755-b6b6-475a-bcb0-389a23194873"
TUNNEL_NAME="callback-platform"

if [ ! -f "$HOME/.cloudflared/$TUNNEL_ID.json" ]; then
    echo -e "${RED}❌ Tunnel credentials not found at $HOME/.cloudflared/$TUNNEL_ID.json${NC}"
    exit 1
fi

if [ ! -f "$HOME/.cloudflared/config.yml" ]; then
    echo -e "${RED}❌ Tunnel config not found at $HOME/.cloudflared/config.yml${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Tunnel credentials found"
echo -e "${GREEN}✓${NC} Tunnel config found"
echo ""

# Copy config to system location
echo -e "${BLUE}Copying config to /etc/cloudflared/...${NC}"
sudo mkdir -p /etc/cloudflared
sudo cp "$HOME/.cloudflared/config.yml" /etc/cloudflared/config.yml
sudo cp "$HOME/.cloudflared/$TUNNEL_ID.json" /etc/cloudflared/$TUNNEL_ID.json

# Update config to use absolute path for credentials
sudo sed -i "s|/home/owner/.cloudflared/|/etc/cloudflared/|g" /etc/cloudflared/config.yml

echo ""
echo -e "${GREEN}✓${NC} Config copied to /etc/cloudflared/"
echo ""

# Fix SELinux context (required on SELinux-enabled systems)
if command -v getenforce &> /dev/null && [ "$(getenforce)" = "Enforcing" ]; then
    echo -e "${BLUE}Fixing SELinux context...${NC}"
    sudo semanage fcontext -a -t bin_t /usr/local/bin/cloudflared 2>/dev/null || true
    sudo restorecon -v /usr/local/bin/cloudflared
    echo ""
    echo -e "${GREEN}✓${NC} SELinux context fixed"
    echo ""
fi

# Install cloudflared as a service
echo -e "${BLUE}Installing cloudflared service...${NC}"
sudo cloudflared --config /etc/cloudflared/config.yml service install

echo ""
echo -e "${GREEN}✓${NC} Service installed"
echo ""

# Enable service to start on boot
echo -e "${BLUE}Enabling service to start on boot...${NC}"
sudo systemctl enable cloudflared

echo ""
echo -e "${GREEN}✓${NC} Service enabled"
echo ""

# Start service now
echo -e "${BLUE}Starting service...${NC}"
sudo systemctl start cloudflared

echo ""
echo -e "${GREEN}✓${NC} Service started"
echo ""

# Wait for tunnel to connect
echo -e "${BLUE}Waiting for tunnel to connect...${NC}"
sleep 5

# Check service status
echo ""
echo -e "${BLUE}━━━ Service Status ━━━${NC}"
sudo systemctl status cloudflared --no-pager | head -20

echo ""
echo -e "${GREEN}━━━ Tunnel is now running as a service ━━━${NC}"
echo ""
echo -e "  ${GREEN}✓${NC} Auto-starts on boot"
echo -e "  ${GREEN}✓${NC} Auto-restarts if it crashes"
echo -e "  ${GREEN}✓${NC} Runs in background"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo -e "  ${YELLOW}sudo systemctl status cloudflared${NC}  - Check status"
echo -e "  ${YELLOW}sudo systemctl restart cloudflared${NC} - Restart tunnel"
echo -e "  ${YELLOW}sudo systemctl stop cloudflared${NC}    - Stop tunnel"
echo -e "  ${YELLOW}sudo journalctl -u cloudflared -f${NC}  - View logs"
echo ""

# Test the tunnel
echo -e "${BLUE}Testing tunnel...${NC}"
if curl -sf https://api.swipswaps.com/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Tunnel is working! https://api.swipswaps.com is reachable"
else
    echo -e "${YELLOW}⚠${NC} Tunnel may still be connecting. Wait 30 seconds and test:"
    echo -e "  ${YELLOW}curl https://api.swipswaps.com/health${NC}"
fi

echo ""

