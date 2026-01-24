#!/bin/bash

# NC CLI Build Script
# Builds platform-specific binaries for distribution

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Extract version from pyproject.toml
VERSION=$(grep 'version = ' pyproject.toml | head -1 | sed 's/.*"\(.*\)".*/\1/')
if [ -z "$VERSION" ]; then
    VERSION="0.1.0"
fi

# Detect platform
SYSTEM=$(uname -s | tr '[:upper:]' '[:lower:]')  # darwin, linux
ARCH=$(uname -m | tr '[:upper:]' '[:lower:]')    # arm64, x86_64

# Normalize architecture
case "$ARCH" in
    x86_64|amd64)
        ARCH="amd64"
        ;;
    arm64|aarch64)
        ARCH="arm64"
        ;;
esac

BUILD_DIR="$SCRIPT_DIR/build"
BINARY_NAME="nccli"
PLATFORM_BINARY="${BINARY_NAME}-${SYSTEM}-${ARCH}"

echo "=========================================="
echo "NC CLI Build Script"
echo "Version: $VERSION"
echo "Platform: ${SYSTEM}-${ARCH}"
echo "=========================================="

# Function to build the binary
build() {
    echo ""
    echo "[1/4] Setting up build environment..."

    # Activate virtual environment if it exists
    if [ -d ".cli_env" ]; then
        source .cli_env/bin/activate
    fi

    # Ensure dependencies are installed
    pip install pyinstaller certifi -q

    echo "[2/4] Building binary..."

    # Clean previous builds
    rm -rf "$BUILD_DIR" pyinstaller_build *.spec

    # Build the binary with hidden imports for lazy-loaded modules
    pyinstaller --onefile \
        --name "$PLATFORM_BINARY" \
        --distpath "$BUILD_DIR" \
        --workpath ./pyinstaller_build \
        --hidden-import=nccli.commands.upload_dns \
        --hidden-import=nccli.commands.download_dns \
        --hidden-import=nccli.commands.upgrade \
        --hidden-import=nccli.commands.config_cmd \
        --hidden-import=nccli.commands.commit \
        --hidden-import=nccli.utils.hosts_parser \
        --hidden-import=nccli.utils.hosts_writer \
        --hidden-import=nccli.utils.mongodb \
        --hidden-import=nccli.utils.config \
        --hidden-import=nccli.commands.info \
        --hidden-import=certifi \
        -y nccli/cli.py

    echo "[3/4] Post-processing..."

    # Remove macOS quarantine flag for faster startup (macOS only)
    if [ "$SYSTEM" = "darwin" ]; then
        xattr -cr "$BUILD_DIR/$PLATFORM_BINARY" 2>/dev/null || true
    fi

    # Clean up build artifacts
    rm -rf pyinstaller_build *.spec

    # Create version file
    echo "$VERSION" > "$BUILD_DIR/version.txt"

    # Also create a copy without platform suffix for backward compatibility
    cp "$BUILD_DIR/$PLATFORM_BINARY" "$BUILD_DIR/$BINARY_NAME"

    echo "[4/4] Build complete!"
    echo ""
    echo "Output files:"
    ls -la "$BUILD_DIR/"
    echo ""
    echo "Binary: $BUILD_DIR/$PLATFORM_BINARY"
    echo "Size: $(du -h "$BUILD_DIR/$PLATFORM_BINARY" | cut -f1)"
}

# Function to create GitHub release using gh CLI
release_github() {
    echo ""
    echo "Creating GitHub release v${VERSION}..."

    REPO="${NCCLI_GITHUB_REPO:-}"
    if [ -z "$REPO" ]; then
        # Try to detect from git remote
        REPO=$(git remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | sed 's/.*github.com[:/]\(.*\)/\1/')
    fi

    if [ -z "$REPO" ]; then
        echo "Error: Could not determine GitHub repository"
        echo "Set NCCLI_GITHUB_REPO environment variable or add GitHub remote"
        exit 1
    fi

    echo "Repository: $REPO"

    # Check if gh CLI is installed
    if ! command -v gh &> /dev/null; then
        echo "Error: GitHub CLI (gh) is not installed"
        echo "Install with: brew install gh"
        exit 1
    fi

    # Check if already authenticated
    if ! gh auth status &>/dev/null; then
        echo "Error: Not authenticated with GitHub CLI"
        echo "Run: gh auth login"
        exit 1
    fi

    # Check if release already exists
    if gh release view "v${VERSION}" --repo "$REPO" &>/dev/null; then
        echo "Release v${VERSION} already exists. Uploading assets..."
        gh release upload "v${VERSION}" \
            --repo "$REPO" \
            --clobber \
            "$BUILD_DIR/$PLATFORM_BINARY" \
            "$BUILD_DIR/version.txt"
    else
        echo "Creating new release v${VERSION}..."
        gh release create "v${VERSION}" \
            --repo "$REPO" \
            --title "NCCLI v${VERSION}" \
            --notes "## NCCLI v${VERSION}

### Installation

\`\`\`bash
# macOS (Apple Silicon)
curl -fsSL https://github.com/${REPO}/releases/download/v${VERSION}/nccli-darwin-arm64 -o /usr/local/bin/nccli
chmod +x /usr/local/bin/nccli

# macOS (Intel)
curl -fsSL https://github.com/${REPO}/releases/download/v${VERSION}/nccli-darwin-amd64 -o /usr/local/bin/nccli
chmod +x /usr/local/bin/nccli

# Linux (x86_64)
curl -fsSL https://github.com/${REPO}/releases/download/v${VERSION}/nccli-linux-amd64 -o /usr/local/bin/nccli
chmod +x /usr/local/bin/nccli
\`\`\`

### Upgrade

If you already have nccli installed:
\`\`\`bash
nccli upgrade
\`\`\`
" \
            "$BUILD_DIR/$PLATFORM_BINARY" \
            "$BUILD_DIR/version.txt"
    fi

    echo ""
    echo "Release complete!"
    echo "URL: https://github.com/${REPO}/releases/tag/v${VERSION}"
}

# Function to test the binary
test_binary() {
    echo ""
    echo "Testing binary..."

    if [ ! -f "$BUILD_DIR/$PLATFORM_BINARY" ]; then
        echo "Error: Binary not found. Run './build.sh build' first."
        exit 1
    fi

    echo "Running: $BUILD_DIR/$PLATFORM_BINARY --version"
    "$BUILD_DIR/$PLATFORM_BINARY" --version

    echo ""
    echo "Running: $BUILD_DIR/$PLATFORM_BINARY --help"
    "$BUILD_DIR/$PLATFORM_BINARY" --help
}

# Main script
case "${1:-build}" in
    build)
        build
        ;;
    release)
        release_github
        ;;
    all)
        build
        release_github
        ;;
    test)
        test_binary
        ;;
    version)
        echo "$VERSION"
        ;;
    platform)
        echo "${SYSTEM}-${ARCH}"
        ;;
    *)
        echo "Usage: $0 {build|release|all|test|version|platform}"
        echo ""
        echo "Commands:"
        echo "  build    - Build the binary for current platform (default)"
        echo "  release  - Create/update GitHub release with current binary"
        echo "  all      - Build and release"
        echo "  test     - Test the built binary"
        echo "  version  - Print current version"
        echo "  platform - Print current platform identifier"
        echo ""
        echo "Current platform: ${SYSTEM}-${ARCH}"
        echo "Output binary: ${PLATFORM_BINARY}"
        exit 1
        ;;
esac
