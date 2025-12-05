#!/bin/bash

# NC CLI Build and Upload Script
# This script builds the nc_cli binary and optionally uploads it to a remote server

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

BUILD_DIR="$SCRIPT_DIR/build"
BINARY_NAME="nc_cli"
VERSIONED_BINARY="${BINARY_NAME}_v${VERSION}"

echo "=========================================="
echo "NC CLI Build Script"
echo "Version: $VERSION"
echo "=========================================="

# Function to build the binary
build() {
    echo ""
    echo "[1/3] Building binary..."

    # Activate virtual environment if it exists
    if [ -d ".cli_env" ]; then
        source .cli_env/bin/activate
    fi

    # Ensure pyinstaller is installed
    pip install pyinstaller -q

    # Clean previous builds
    rm -rf "$BUILD_DIR" pyinstaller_build *.spec

    # Build the binary with hidden imports for lazy-loaded modules
    pyinstaller --onefile \
        --name "$BINARY_NAME" \
        --distpath "$BUILD_DIR" \
        --workpath ./pyinstaller_build \
        --hidden-import=nccli.commands.upload_dns \
        --hidden-import=nccli.commands.download_dns \
        --hidden-import=nccli.commands.upgrade \
        --hidden-import=nccli.commands.config_cmd \
        --hidden-import=nccli.utils.hosts_parser \
        --hidden-import=nccli.utils.hosts_writer \
        --hidden-import=nccli.utils.mongodb \
        --hidden-import=nccli.utils.config \
        -y nccli/cli.py

    # Remove macOS quarantine flag for faster startup
    xattr -cr "$BUILD_DIR/$BINARY_NAME" 2>/dev/null || true

    # Clean up build artifacts
    rm -rf pyinstaller_build *.spec

    echo "[1/3] Binary built: $BUILD_DIR/$BINARY_NAME"

    # Create version file
    echo "$VERSION" > "$BUILD_DIR/version.txt"
    echo "[2/3] Version file created: $BUILD_DIR/version.txt"

    # Create versioned copy
    cp "$BUILD_DIR/$BINARY_NAME" "$BUILD_DIR/$VERSIONED_BINARY"
    echo "[3/3] Versioned binary created: $BUILD_DIR/$VERSIONED_BINARY"

    echo ""
    echo "Build complete!"
    ls -la "$BUILD_DIR/"
}

# Function to upload via SCP
upload_scp() {
    echo ""
    echo "Uploading via SCP..."

    if [ -z "$NCCLI_SCP_HOST" ] || [ -z "$NCCLI_SCP_USER" ] || [ -z "$NCCLI_SCP_PATH" ]; then
        echo "Error: SCP configuration missing in .env"
        echo "Required: NCCLI_SCP_HOST, NCCLI_SCP_USER, NCCLI_SCP_PATH"
        exit 1
    fi

    # Create remote directory if needed
    ssh "${NCCLI_SCP_USER}@${NCCLI_SCP_HOST}" "mkdir -p ${NCCLI_SCP_PATH}"

    # Upload files
    scp "$BUILD_DIR/$BINARY_NAME" "${NCCLI_SCP_USER}@${NCCLI_SCP_HOST}:${NCCLI_SCP_PATH}/${BINARY_NAME}"
    scp "$BUILD_DIR/$VERSIONED_BINARY" "${NCCLI_SCP_USER}@${NCCLI_SCP_HOST}:${NCCLI_SCP_PATH}/${VERSIONED_BINARY}"
    scp "$BUILD_DIR/version.txt" "${NCCLI_SCP_USER}@${NCCLI_SCP_HOST}:${NCCLI_SCP_PATH}/version.txt"

    echo "Upload complete!"
    echo "Binary URL: https://${NCCLI_SCP_HOST}${NCCLI_SCP_PATH}/${BINARY_NAME}"
}

# Function to upload to S3
upload_s3() {
    echo ""
    echo "Uploading to S3..."

    if [ -z "$NCCLI_S3_BUCKET" ]; then
        echo "Error: S3 configuration missing in .env"
        echo "Required: NCCLI_S3_BUCKET"
        exit 1
    fi

    PREFIX="${NCCLI_S3_PREFIX:-nc_cli/releases}"

    # Upload files
    aws s3 cp "$BUILD_DIR/$BINARY_NAME" "s3://${NCCLI_S3_BUCKET}/${PREFIX}/${BINARY_NAME}"
    aws s3 cp "$BUILD_DIR/$VERSIONED_BINARY" "s3://${NCCLI_S3_BUCKET}/${PREFIX}/${VERSIONED_BINARY}"
    aws s3 cp "$BUILD_DIR/version.txt" "s3://${NCCLI_S3_BUCKET}/${PREFIX}/version.txt"

    echo "Upload complete!"
    echo "Binary URL: https://${NCCLI_S3_BUCKET}.s3.amazonaws.com/${PREFIX}/${BINARY_NAME}"
}

# Function to create GitHub release
upload_github() {
    echo ""
    echo "Creating GitHub release..."

    if [ -z "$NCCLI_GITHUB_REPO" ] || [ -z "$NCCLI_GITHUB_TOKEN" ]; then
        echo "Error: GitHub configuration missing in .env"
        echo "Required: NCCLI_GITHUB_REPO, NCCLI_GITHUB_TOKEN"
        exit 1
    fi

    # Check if gh CLI is installed
    if ! command -v gh &> /dev/null; then
        echo "Error: GitHub CLI (gh) is not installed"
        echo "Install with: brew install gh"
        exit 1
    fi

    # Authenticate with token
    echo "$NCCLI_GITHUB_TOKEN" | gh auth login --with-token

    # Create release
    gh release create "v${VERSION}" \
        --repo "$NCCLI_GITHUB_REPO" \
        --title "NC CLI v${VERSION}" \
        --notes "Release v${VERSION}" \
        "$BUILD_DIR/$BINARY_NAME" \
        "$BUILD_DIR/$VERSIONED_BINARY" \
        "$BUILD_DIR/version.txt" \
        || echo "Release may already exist, uploading assets..."

    echo "Upload complete!"
    echo "Release URL: https://github.com/${NCCLI_GITHUB_REPO}/releases/tag/v${VERSION}"
}

# Function to upload based on configured method
upload() {
    METHOD="${NCCLI_UPLOAD_METHOD:-scp}"

    case "$METHOD" in
        scp)
            upload_scp
            ;;
        s3)
            upload_s3
            ;;
        github)
            upload_github
            ;;
        *)
            echo "Error: Unknown upload method: $METHOD"
            echo "Supported methods: scp, s3, github"
            exit 1
            ;;
    esac
}

# Main script
case "${1:-build}" in
    build)
        build
        ;;
    upload)
        upload
        ;;
    all)
        build
        upload
        ;;
    version)
        echo "$VERSION"
        ;;
    *)
        echo "Usage: $0 {build|upload|all|version}"
        echo ""
        echo "Commands:"
        echo "  build   - Build the binary (default)"
        echo "  upload  - Upload to configured remote"
        echo "  all     - Build and upload"
        echo "  version - Print current version"
        exit 1
        ;;
esac
