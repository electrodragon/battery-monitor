#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/battery-monitor"
BIN_LINK="/usr/local/bin/battery-monitor"
SERVICE_SRC="battery-monitor.service"
SERVICE_DST="/etc/systemd/system/battery-monitor.service"
PYTHON_SCRIPT="battery_monitor.py"
CLI_SCRIPT="battery-monitor"
SERVICE_NAME="battery-monitor"

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)." >&2
    exit 1
fi

REAL_USER="${SUDO_USER:-$(whoami)}"

echo "[1/6] Creating install directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

echo "[2/6] Copying scripts to $INSTALL_DIR"
cp "$(dirname "$0")/$PYTHON_SCRIPT" "$INSTALL_DIR/"
chmod 755 "$INSTALL_DIR/$PYTHON_SCRIPT"
cp "$(dirname "$0")/$CLI_SCRIPT" "$INSTALL_DIR/"
chmod 755 "$INSTALL_DIR/$CLI_SCRIPT"
cp "$(dirname "$0")/install.sh" "$INSTALL_DIR/"
cp "$(dirname "$0")/uninstall.sh" "$INSTALL_DIR/"

echo "[3/6] Creating symlink: $BIN_LINK"
ln -sf "$INSTALL_DIR/$CLI_SCRIPT" "$BIN_LINK"

echo "[4/6] Installing systemd service: $SERVICE_DST"
sed "s|ExecStart=.*|ExecStart=/usr/bin/python3 $INSTALL_DIR/$PYTHON_SCRIPT|" "$(dirname "$0")/$SERVICE_SRC" > "$SERVICE_DST"
sed -i "s|%USER%|$REAL_USER|g" "$SERVICE_DST"

echo "[5/6] Copying assets..."
for asset in battery_full_wallpaper.jpg battery_full_alert.wav; do
    if [[ -f "$(dirname "$0")/$asset" ]]; then
        cp "$(dirname "$0")/$asset" "$INSTALL_DIR/"
        echo "  Copied $asset"
    fi
done

echo "[6/6] Enabling and restarting service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo ""
echo "=== Installation complete ==="
echo ""
echo "Commands:"
echo "  battery-monitor help      Show help"
echo "  battery-monitor status    Check service status"
echo "  battery-monitor logs      Follow logs"
echo ""
echo "Place custom assets in:"
echo "  $INSTALL_DIR/battery_full_wallpaper.jpg"
echo "  $INSTALL_DIR/battery_full_alert.wav"
echo "Then run: sudo systemctl restart $SERVICE_NAME"
