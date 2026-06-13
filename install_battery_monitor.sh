#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="electrodragon"
REPO_NAME="battery-monitor"
REPO_BRANCH="main"

INSTALL_DIR="/opt/battery-monitor"
BIN_LINK="/usr/local/bin/battery-monitor"
SERVICE_DST="/etc/systemd/system/battery-monitor.service"
SERVICE_NAME="battery-monitor"

PYTHON_SCRIPT="battery_monitor.py"
CLI_SCRIPT="battery-monitor"
SERVICE_SRC="battery-monitor.service"

if [[ $EUID -ne 0 ]]; then
    echo "[!] This script must be run as root." >&2
    echo "    Try: curl -fsSL 'https://electrodragon.github.io/battery-monitor/install_battery_monitor.sh' | sudo bash" >&2
    exit 1
fi

REAL_USER="${SUDO_USER:-$(whoami)}"
REAL_HOME="$(eval "echo ~$REAL_USER")"

echo "[1/6] Downloading $REPO_OWNER/$REPO_NAME..."
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
curl -fsSL "https://github.com/$REPO_OWNER/$REPO_NAME/archive/refs/heads/$REPO_BRANCH.tar.gz" | tar xz -C "$TMPDIR"
REPO_DIR="$TMPDIR/$REPO_NAME-$REPO_BRANCH"

echo "[2/6] Creating install directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

echo "[3/6] Copying files..."
cp "$REPO_DIR/$PYTHON_SCRIPT" "$INSTALL_DIR/"
chmod 755 "$INSTALL_DIR/$PYTHON_SCRIPT"
cp "$REPO_DIR/$CLI_SCRIPT" "$INSTALL_DIR/"
chmod 755 "$INSTALL_DIR/$CLI_SCRIPT"

echo "[4/6] Creating symlink: $BIN_LINK"
ln -sf "$INSTALL_DIR/$CLI_SCRIPT" "$BIN_LINK"

echo "[5/6] Installing systemd service..."
sed "s|ExecStart=.*|ExecStart=/usr/bin/python3 $INSTALL_DIR/$PYTHON_SCRIPT|" "$REPO_DIR/$SERVICE_SRC" > "$SERVICE_DST"
sed -i "s|%USER%|$REAL_USER|g" "$SERVICE_DST"

echo "[6/6] Enabling and starting service..."
systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

for asset in battery_full_wallpaper.jpg battery_full_alert.wav; do
    if [[ -f "$REPO_DIR/$asset" ]]; then
        cp "$REPO_DIR/$asset" "$INSTALL_DIR/"
        echo "  Copied $asset"
    fi
done

echo ""
echo "=== Installation complete ==="
echo ""
echo "Commands:"
echo "  battery-monitor help      Show help"
echo "  battery-monitor status    Check service status"
echo "  battery-monitor logs      Follow logs"
echo "  battery-monitor stop      Stop monitoring"
echo "  battery-monitor start     Start monitoring"
echo ""
echo "Place custom assets in:"
echo "  $INSTALL_DIR/battery_full_wallpaper.jpg"
echo "  $INSTALL_DIR/battery_full_alert.wav"
echo "Then run: sudo systemctl restart $SERVICE_NAME"
