#!/bin/bash

# Configuration: Use the current directory
BASE_DIR=$(pwd)
PROTO_PACKAGE_NAME="niri_protocols"
PROTO_DIR="$BASE_DIR/$PROTO_PACKAGE_NAME"

WAYLAND_XML="/usr/share/wayland/wayland.xml"
# Check common system paths for the idle protocol
IDLE_XML_SYSTEM="/usr/share/wayland-protocols/staging/ext-idle-notify/ext-idle-notify-v1.xml"

echo "[*] Initializing protocol package at $PROTO_DIR"
mkdir -p "$PROTO_DIR"

# 1. Resolve XML paths
if [ ! -f "$WAYLAND_XML" ]; then
  echo "[!] Error: core wayland.xml not found. Please install wayland-devel."
  exit 1
fi

if [ -f "$IDLE_XML_SYSTEM" ]; then
  IDLE_XML="$IDLE_XML_SYSTEM"
else
  echo "[*] ext-idle-notify-v1.xml not found on system. Downloading..."
  curl -L -o "$BASE_DIR/ext-idle-notify-v1.xml" "https://gitlab.freedesktop.org/wayland/wayland-protocols/-/raw/main/staging/ext-idle-notify/ext-idle-notify-v1.xml"
  IDLE_XML="$BASE_DIR/ext-idle-notify-v1.xml"
fi

# 2. Run the scanner
# We output directly into the niri_protocols directory
echo "[*] Scanning protocols into $PROTO_DIR..."
python3 -m pywayland.scanner -i "$WAYLAND_XML" "$IDLE_XML" -o "$PROTO_DIR"

# 3. Fix the package structure
# Scanner creates folders like 'wayland' and 'ext_idle_notify_v1' inside the output dir
touch "$PROTO_DIR/__init__.py"
find "$PROTO_DIR" -type d -exec touch "{}/__init__.py" \;

echo "[+] Done."
echo "[*] To use this in your script, add this to the top:"
echo "---------------------------------------------------"
echo "import sys"
echo "import os"
echo "sys.path.insert(0, '$BASE_DIR')"
echo "from $PROTO_PACKAGE_NAME.ext_idle_notify_v1.ext_idle_notifier_v1 import ExtIdleNotifierV1"
echo "---------------------------------------------------"
