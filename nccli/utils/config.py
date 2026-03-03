"""Configuration loader for nccli."""

import os
from pathlib import Path


# Default config locations (in order of priority)
CONFIG_LOCATIONS = [
    Path.home() / ".nc_cli" / "config",
    Path("/etc/nc_cli/config"),
]

# Default configuration values
DEFAULT_CONFIG = {
    "NCCLI_MONGODB_URI": "",
    "NCCLI_UPGRADE_BASE_URL": "",
}


def find_config_file():
    """Find the first existing config file."""
    for config_path in CONFIG_LOCATIONS:
        if config_path.exists():
            return config_path
    return None


def load_config():
    """
    Load configuration from file and set environment variables.

    Config file format (same as .env):
        KEY=value
        # Comments are ignored
    """
    config_file = find_config_file()

    if config_file:
        try:
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    # Parse KEY=value
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
        except Exception:
            pass  # Silently ignore config file errors

    # Set defaults for any missing values
    for key, value in DEFAULT_CONFIG.items():
        if key not in os.environ and value:
            os.environ[key] = value


def get_config_path():
    """Get the user config path."""
    return CONFIG_LOCATIONS[0]


def init_config(mongodb_uri="", upgrade_url=""):
    """Initialize config file with given values."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    upgrade_url = upgrade_url or DEFAULT_CONFIG["NCCLI_UPGRADE_BASE_URL"]

    config_content = f"""# NC CLI Configuration
# This file is auto-loaded on startup

# MongoDB connection URI (required for uploadDns/downloadDns)
NCCLI_MONGODB_URI={mongodb_uri}

# Upgrade URL for auto-updates
NCCLI_UPGRADE_BASE_URL={upgrade_url}
"""

    with open(config_path, 'w') as f:
        f.write(config_content)

    return config_path
