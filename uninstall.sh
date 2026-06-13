#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/battery-monitor"
BIN_LINK="/usr/local/bin/battery-monitor"
SERVICE_DST="/etc/systemd/system/battery-monitor.service"
SERVICE_NAME="battery-monitor"

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)." >&2
    exit 1
fi

echo "[1/3] Stopping and disabling service"
systemctl disable --now "$SERVICE_NAME" 2>/dev/null || true

echo "[2/3] Removing systemd service file"
rm -f "$SERVICE_DST"
systemctl daemon-reload

echo "[3/3] Removing installed files"
rm -f "$BIN_LINK"
rm -rf "$INSTALL_DIR"

echo ""
echo "=== Uninstallation complete ==="
