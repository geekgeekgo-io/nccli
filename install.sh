#!/bin/bash

# NC CLI Installer
# Downloads and installs the latest version of nc_cli

set -e

# Configuration
GITHUB_REPO="${NCCLI_GITHUB_REPO:-geekgeekgo-io/nccli}"
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"
BINARY_NAME="nccli"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================"
echo "NC CLI Installer"
echo "================================"
echo ""

# Detect platform
SYSTEM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m | tr '[:upper:]' '[:lower:]')

# Normalize architecture
case "$ARCH" in
    x86_64|amd64)
        ARCH="amd64"
        ;;
    arm64|aarch64)
        ARCH="arm64"
        ;;
    *)
        echo -e "${RED}Error: Unsupported architecture: $ARCH${NC}"
        exit 1
        ;;
esac

# Check supported platform
case "$SYSTEM" in
    darwin|linux)
        ;;
    *)
        echo -e "${RED}Error: Unsupported operating system: $SYSTEM${NC}"
        exit 1
        ;;
esac

PLATFORM="${SYSTEM}-${ARCH}"
ASSET_NAME="nccli-${PLATFORM}"

echo "Platform: $PLATFORM"
echo "Repository: $GITHUB_REPO"
echo ""

# Get latest release info
echo "Fetching latest release..."
RELEASE_INFO=$(curl -sL "https://api.github.com/repos/${GITHUB_REPO}/releases/latest")

if echo "$RELEASE_INFO" | grep -q "Not Found"; then
    echo -e "${RED}Error: No releases found for repository: $GITHUB_REPO${NC}"
    echo "Make sure the repository exists and has at least one release."
    exit 1
fi

VERSION=$(echo "$RELEASE_INFO" | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')
DOWNLOAD_URL="https://github.com/${GITHUB_REPO}/releases/download/${VERSION}/${ASSET_NAME}"

echo "Latest version: $VERSION"
echo "Download URL: $DOWNLOAD_URL"
echo ""

# Create temp directory
TMP_DIR=$(mktemp -d)
TMP_FILE="${TMP_DIR}/${BINARY_NAME}"

# Download binary
echo "Downloading..."
if ! curl -fsSL "$DOWNLOAD_URL" -o "$TMP_FILE"; then
    echo -e "${RED}Error: Failed to download binary${NC}"
    echo "URL: $DOWNLOAD_URL"
    rm -rf "$TMP_DIR"
    exit 1
fi

# Make executable
chmod +x "$TMP_FILE"

# Test binary
echo "Verifying binary..."
if ! "$TMP_FILE" --version &>/dev/null; then
    echo -e "${RED}Error: Downloaded binary is not valid${NC}"
    rm -rf "$TMP_DIR"
    exit 1
fi

# Install
echo ""
echo "Installing to ${INSTALL_DIR}/${BINARY_NAME}..."

# Check if we need sudo
if [ -w "$INSTALL_DIR" ]; then
    mv "$TMP_FILE" "${INSTALL_DIR}/${BINARY_NAME}"
else
    echo -e "${YELLOW}Requires sudo to install to ${INSTALL_DIR}${NC}"
    sudo mv "$TMP_FILE" "${INSTALL_DIR}/${BINARY_NAME}"
    sudo chmod +x "${INSTALL_DIR}/${BINARY_NAME}"
fi

# Cleanup
rm -rf "$TMP_DIR"

# Verify installation
echo ""
if command -v "$BINARY_NAME" &>/dev/null; then
    echo -e "${GREEN}Installation successful!${NC}"
    echo ""
    "$BINARY_NAME" --version
    echo ""
    echo "Run 'nccli --help' to get started."
    echo "Run 'nccli upgrade' to update to the latest version."
else
    echo -e "${YELLOW}Binary installed to ${INSTALL_DIR}/${BINARY_NAME}${NC}"
    echo "Add ${INSTALL_DIR} to your PATH if it's not already there:"
    echo "  export PATH=\"${INSTALL_DIR}:\$PATH\""
fi
