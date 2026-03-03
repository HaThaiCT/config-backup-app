#!/bin/bash
#
# Uninstall script for Ubuntu Backup Service
#
# Usage: sudo ./uninstall.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/backup-service"
CONFIG_DIR="/etc/backup-service"
LOG_DIR="/var/log/backup-service"
SERVICE_NAME="backup-service"

echo -e "${RED}================================${NC}"
echo -e "${RED}Ubuntu Backup Service Uninstaller${NC}"
echo -e "${RED}================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root (sudo ./uninstall.sh)${NC}"
    exit 1
fi

# Confirm uninstallation
read -p "Are you sure you want to uninstall? (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Uninstallation cancelled"
    exit 0
fi

# Stop and disable service
echo "Stopping service..."
systemctl stop $SERVICE_NAME 2>/dev/null || true
systemctl disable $SERVICE_NAME 2>/dev/null || true

# Remove systemd service file
echo "Removing systemd service..."
rm -f /etc/systemd/system/backup-service.service
systemctl daemon-reload

# Remove installation directory
echo "Removing installation files..."
rm -rf "$INSTALL_DIR"

# Ask about config and logs
read -p "Remove configuration files? (y/N): " remove_config
if [ "$remove_config" = "y" ] || [ "$remove_config" = "Y" ]; then
    rm -rf "$CONFIG_DIR"
    echo "Configuration removed"
else
    echo -e "${YELLOW}Configuration kept at: $CONFIG_DIR${NC}"
fi

read -p "Remove log files? (y/N): " remove_logs
if [ "$remove_logs" = "y" ] || [ "$remove_logs" = "Y" ]; then
    rm -rf "$LOG_DIR"
    echo "Logs removed"
else
    echo -e "${YELLOW}Logs kept at: $LOG_DIR${NC}"
fi

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Uninstallation completed!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${YELLOW}Note: Backup files in /backups were NOT removed${NC}"
echo "Remove manually if needed: sudo rm -rf /backups"
