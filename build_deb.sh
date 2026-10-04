#!/bin/bash
set -e

echo "Installing PyInstaller..."
source venv/bin/activate
pip install pyinstaller

echo "Building standalone executable..."
# --onefile packages it all into a single binary
# --windowed hides the terminal window when launched
pyinstaller --onefile --windowed --add-data "logo.jpg:." --name="daves-system-info" main.py

echo "Setting up package structure..."
PKG_DIR="daves-system-info_1.0_amd64"
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/applications"

# Create DEBIAN/control file
cat <<EOF > "$PKG_DIR/DEBIAN/control"
Package: daves-system-info
Version: 1.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Dave
Description: Dave's System Information
 A lightweight, real-time task manager and system performance monitor.
EOF

# Set correct permissions for control file
chmod 644 "$PKG_DIR/DEBIAN/control"

# Copy binary to the package
cp dist/daves-system-info "$PKG_DIR/usr/bin/"
chmod 755 "$PKG_DIR/usr/bin/daves-system-info"

# Create .desktop file so it appears in the app launcher (GNOME/KDE/etc)
cat <<EOF > "$PKG_DIR/usr/share/applications/daves-system-info.desktop"
[Desktop Entry]
Name=Dave's System Information
Comment=Monitor system performance and processes
Exec=/usr/bin/daves-system-info
Icon=utilities-system-monitor
Terminal=false
Type=Application
Categories=System;Monitor;
EOF
chmod 644 "$PKG_DIR/usr/share/applications/daves-system-info.desktop"

echo "Building .deb package..."
dpkg-deb --build "$PKG_DIR"

echo "Done! Package created: daves-system-info_1.0_amd64.deb"
