#!/bin/bash

# NC CLI Installation Script
# Downloads and installs nc_cli from GitHub releases

set -e

# Configuration
GITHUB_REPO="geekgeekgo-io/nc_cli_artifactory"
INSTALL_DIR="/usr/local/bin"
BINARY_NAME="nc_cli"
CONFIG_DIR="$HOME/.nc_cli"
CONFIG_FILE="$CONFIG_DIR/config"
DOWNLOAD_URL="https://github.com/${GITHUB_REPO}/releases/latest/download/${BINARY_NAME}"
UPGRADE_URL="https://github.com/${GITHUB_REPO}/releases/latest/download"

echo "=========================================="
echo "NC CLI Installer"
echo "=========================================="
echo ""

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This installer is for macOS only."
    exit 1
fi

# Check architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Create install directory if it doesn't exist
if [[ ! -d "$INSTALL_DIR" ]]; then
    echo "Creating $INSTALL_DIR..."
    sudo mkdir -p "$INSTALL_DIR"
fi

# Download the binary (with -L to follow redirects)
echo ""
echo "Downloading nc_cli from GitHub..."
TEMP_FILE=$(mktemp)
if ! curl -fsSL "$DOWNLOAD_URL" -o "$TEMP_FILE"; then
    echo "Error: Failed to download nc_cli from $DOWNLOAD_URL"
    rm -f "$TEMP_FILE"
    exit 1
fi

# Check if download was successful (file size > 0)
if [[ ! -s "$TEMP_FILE" ]]; then
    echo "Error: Downloaded file is empty"
    rm -f "$TEMP_FILE"
    exit 1
fi

# Install the binary
echo "Installing to $INSTALL_DIR/$BINARY_NAME..."
sudo mv "$TEMP_FILE" "$INSTALL_DIR/$BINARY_NAME"
sudo chmod +x "$INSTALL_DIR/$BINARY_NAME"

# Remove quarantine flag for faster startup
echo "Removing quarantine flag..."
sudo xattr -cr "$INSTALL_DIR/$BINARY_NAME" 2>/dev/null || true

# Create config directory and file
echo ""
echo "Setting up configuration..."
mkdir -p "$CONFIG_DIR"

# Create config file if it doesn't exist
if [[ ! -f "$CONFIG_FILE" ]]; then
    cat > "$CONFIG_FILE" << EOF
# NC CLI Configuration
# This file is auto-loaded on startup

# MongoDB connection URI (required for uploadDns/downloadDns)
# Example: mongodb://user:pass@host:27017/database?authSource=admin
NCCLI_MONGODB_URI=

# Upgrade URL for auto-updates (do not modify unless you have a custom release server)
NCCLI_UPGRADE_BASE_URL=${UPGRADE_URL}
EOF
    echo "Config file created at: $CONFIG_FILE"
else
    echo "Config file already exists at: $CONFIG_FILE"
fi

# Verify installation
echo ""
echo "Verifying installation..."
if command -v nc_cli &> /dev/null; then
    VERSION=$(nc_cli --version 2>/dev/null || echo "unknown")
    echo "Installed: $VERSION"
else
    echo "Warning: nc_cli not found in PATH"
    echo "You may need to add $INSTALL_DIR to your PATH"
fi

# Post-installation steps
echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "============================================"
echo "POST-INSTALLATION STEPS"
echo "============================================"
echo ""
echo "Step 1: Configure MongoDB connection"
echo "-------------------------------------"
echo "Edit the config file to add your MongoDB URI:"
echo ""
echo "  nano $CONFIG_FILE"
echo ""
echo "Or run:"
echo ""
echo "  nc_cli config --init --mongodb-uri \"mongodb://user:pass@host:27017/db?authSource=admin\""
echo ""
echo ""
echo "Step 2: Verify configuration"
echo "----------------------------"
echo "  nc_cli config --show"
echo ""
echo ""
echo "============================================"
echo "USAGE EXAMPLES"
echo "============================================"
echo ""
echo "# Show help"
echo "nc_cli --help"
echo ""
echo "# Show/manage configuration"
echo "nc_cli config --show"
echo ""
echo "# Upload /etc/hosts to MongoDB"
echo "sudo -E nc_cli uploadDns"
echo ""
echo "# Download from MongoDB to /etc/hosts"
echo "sudo -E nc_cli downloadDns --backup"
echo ""
echo "# Check for updates"
echo "nc_cli upgrade --check"
echo ""
echo "# Upgrade to latest version"
echo "nc_cli upgrade"
echo ""
echo "============================================"
echo "CONFIGURATION FILE"
echo "============================================"
echo ""
echo "Location: $CONFIG_FILE"
echo ""
echo "Current contents:"
echo "---"
cat "$CONFIG_FILE"
echo "---"
echo ""
