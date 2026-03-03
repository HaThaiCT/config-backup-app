#!/bin/bash
#
# Install script for Ubuntu Backup Service
#
# Usage: sudo ./install.sh
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
BACKUP_DIR="/backups"
SERVICE_NAME="backup-service"
PYTHON_VERSION="python3"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Ubuntu Backup Service Installer${NC}"
echo -e "${GREEN}================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root (sudo ./install.sh)${NC}"
    exit 1
fi

# Check Python 3
if ! command -v $PYTHON_VERSION &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed${NC}"
    echo "Install with: apt install python3 python3-venv python3-pip"
    exit 1
fi

echo -e "${YELLOW}Installing to: ${INSTALL_DIR}${NC}"

# Create directories
echo "Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$BACKUP_DIR"

# Copy application files
echo "Copying application files..."
cp -r src "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"

# Copy config if not exists
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    echo "Creating default configuration..."
    cp config/config.example.yaml "$CONFIG_DIR/config.yaml"
    echo -e "${YELLOW}Please edit ${CONFIG_DIR}/config.yaml to configure your backup sources${NC}"
else
    echo "Configuration file already exists, keeping existing config"
fi

# Create virtual environment
echo "Creating Python virtual environment..."
$PYTHON_VERSION -m venv "$INSTALL_DIR/venv"

# Install dependencies
echo "Installing Python dependencies..."
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Install systemd service
echo "Installing systemd service..."
cp systemd/backup-service.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Set permissions
echo "Setting permissions..."
chmod 755 "$INSTALL_DIR"
chmod 600 "$CONFIG_DIR/config.yaml"
chmod 755 "$LOG_DIR"
chmod 755 "$BACKUP_DIR"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Installation completed!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit configuration: sudo nano $CONFIG_DIR/config.yaml"
echo "2. Enable service: sudo systemctl enable $SERVICE_NAME"
echo "3. Start service: sudo systemctl start $SERVICE_NAME"
echo "4. Check status: sudo systemctl status $SERVICE_NAME"
echo "5. View logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Manual backup: sudo $INSTALL_DIR/venv/bin/python -m src.main --backup"
