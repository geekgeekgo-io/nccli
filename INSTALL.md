# Installation Guide

This guide covers installing NCCLI on macOS and Linux systems.

## Quick Install (Recommended)

Run this one-liner to automatically detect your platform and install the latest version:

```bash
curl -fsSL https://raw.githubusercontent.com/geekgeekgo-io/nccli/main/install.sh | bash
```

If you need to install to `/usr/local/bin` (default), you may need sudo:
```bash
curl -fsSL https://raw.githubusercontent.com/geekgeekgo-io/nccli/main/install.sh | sudo bash
```

## Manual Installation

### macOS

#### Apple Silicon (M1/M2/M3/M4)

```bash
# Download the binary
curl -fsSL https://github.com/geekgeekgo-io/nccli/releases/latest/download/nccli-darwin-arm64 -o nccli

# Make it executable
chmod +x nccli

# Move to a directory in your PATH
sudo mv nccli /usr/local/bin/

# Verify installation
nccli --version
```

#### Intel Mac

```bash
# Download the binary
curl -fsSL https://github.com/geekgeekgo-io/nccli/releases/latest/download/nccli-darwin-amd64 -o nccli

# Make it executable
chmod +x nccli

# Move to a directory in your PATH
sudo mv nccli /usr/local/bin/

# Verify installation
nccli --version
```

#### Removing macOS Quarantine (if needed)

If macOS shows a security warning when running nccli for the first time:

```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine /usr/local/bin/nccli
```

Or allow it in System Preferences > Security & Privacy.

### Linux

#### x86_64 / AMD64

```bash
# Download the binary
curl -fsSL https://github.com/geekgeekgo-io/nccli/releases/latest/download/nccli-linux-amd64 -o nccli

# Make it executable
chmod +x nccli

# Move to a directory in your PATH
sudo mv nccli /usr/local/bin/

# Verify installation
nccli --version
```

#### ARM64 / AArch64

```bash
# Download the binary
curl -fsSL https://github.com/geekgeekgo-io/nccli/releases/latest/download/nccli-linux-arm64 -o nccli

# Make it executable
chmod +x nccli

# Move to a directory in your PATH
sudo mv nccli /usr/local/bin/

# Verify installation
nccli --version
```

### Custom Install Location

To install to a different directory (e.g., `~/.local/bin`):

```bash
# Create directory if it doesn't exist
mkdir -p ~/.local/bin

# Download and install (example for macOS Apple Silicon)
curl -fsSL https://github.com/geekgeekgo-io/nccli/releases/latest/download/nccli-darwin-arm64 -o ~/.local/bin/nccli
chmod +x ~/.local/bin/nccli

# Add to PATH (add this to your ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"
```

## Install from Source

If you prefer to install from source or need to modify the code:

### Prerequisites

- Python 3.8 or higher
- pip

### Steps

```bash
# Clone the repository
git clone https://github.com/geekgeekgo-io/nccli.git
cd nccli

# Install in development mode
pip install -e .

# Or install normally
pip install .

# Verify installation
nccli --version
```

### Build Your Own Binary

To build a standalone binary from source:

```bash
# Clone the repository
git clone https://github.com/geekgeekgo-io/nccli.git
cd nccli

# Install build dependencies
pip install pyinstaller certifi

# Build the binary
./build.sh build

# The binary will be in ./build/
./build/nccli --version
```

## Upgrading

If you already have nccli installed, you can upgrade to the latest version:

```bash
nccli upgrade
```

Or re-run the install script:

```bash
curl -fsSL https://raw.githubusercontent.com/geekgeekgo-io/nccli/main/install.sh | sudo bash
```

## Uninstalling

To remove nccli:

```bash
sudo rm /usr/local/bin/nccli
```

If installed in a custom location, remove it from there instead.

## Verifying Installation

After installation, verify everything works:

```bash
# Check version
nccli --version

# View available commands
nccli --help
```

## Troubleshooting

### "Command not found" error

Make sure the installation directory is in your PATH:

```bash
# Check if /usr/local/bin is in PATH
echo $PATH | grep -q '/usr/local/bin' && echo "OK" || echo "Not in PATH"

# Add to PATH if needed (add to ~/.bashrc or ~/.zshrc)
export PATH="/usr/local/bin:$PATH"
```

### Permission denied

If you get permission errors when installing:

```bash
# Use sudo for system-wide installation
sudo curl -fsSL https://github.com/geekgeekgo-io/nccli/releases/latest/download/nccli-darwin-arm64 -o /usr/local/bin/nccli
sudo chmod +x /usr/local/bin/nccli
```

Or install to a user directory instead (see Custom Install Location above).

### macOS security warning

macOS may block the binary on first run. Either:

1. Right-click the binary and select "Open", or
2. Go to System Preferences > Security & Privacy and click "Allow Anyway", or
3. Remove the quarantine attribute:
   ```bash
   xattr -d com.apple.quarantine /usr/local/bin/nccli
   ```

### Linux: GLIBC version error

If you see GLIBC version errors, you may need to:

1. Update your system's glibc, or
2. Install from source using `pip install .`
