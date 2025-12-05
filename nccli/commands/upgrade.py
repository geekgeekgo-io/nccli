"""Upgrade command for nc_cli."""

import click
import os
import sys
import stat
import ssl
import tempfile
import urllib.request
import urllib.error
from pathlib import Path


def get_ssl_context():
    """Create SSL context that works on macOS with PyInstaller."""
    try:
        # Try to use certifi certificates if available
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass

    # Try default context
    try:
        ctx = ssl.create_default_context()
        return ctx
    except Exception:
        pass

    # Fallback: disable verification (not recommended for production)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def get_current_version():
    """Get the current version from package."""
    try:
        from nccli import __version__
        return __version__
    except (ImportError, AttributeError):
        return "0.1.0"


def fetch_remote_version(base_url):
    """Fetch the latest version from remote server."""
    version_url = f"{base_url.rstrip('/')}/version.txt"
    try:
        ssl_context = get_ssl_context()
        with urllib.request.urlopen(version_url, timeout=10, context=ssl_context) as response:
            return response.read().decode('utf-8').strip()
    except urllib.error.URLError as e:
        raise Exception(f"Failed to fetch version from {version_url}: {e}")


def download_binary(base_url, dest_path):
    """Download the latest binary from remote server."""
    binary_url = f"{base_url.rstrip('/')}/nc_cli"
    try:
        click.echo(f"Downloading from {binary_url}...")

        # Download to temp file first
        ssl_context = get_ssl_context()
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            with urllib.request.urlopen(binary_url, timeout=60, context=ssl_context) as response:
                total_size = response.headers.get('Content-Length')
                if total_size:
                    total_size = int(total_size)

                downloaded = 0
                block_size = 8192

                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    tmp_file.write(buffer)

                    if total_size:
                        percent = (downloaded / total_size) * 100
                        click.echo(f"\rProgress: {percent:.1f}%", nl=False)

                click.echo()  # New line after progress

            tmp_path = tmp_file.name

        return tmp_path

    except urllib.error.URLError as e:
        raise Exception(f"Failed to download binary from {binary_url}: {e}")


def get_executable_path():
    """Get the path of the currently running executable."""
    if getattr(sys, 'frozen', False):
        # Running as compiled binary (PyInstaller)
        return sys.executable
    else:
        # Running as Python script - return None
        return None


def compare_versions(current, remote):
    """Compare version strings. Returns True if remote is newer."""
    def parse_version(v):
        # Remove 'v' prefix if present
        v = v.lstrip('v')
        parts = v.split('.')
        return [int(p) for p in parts if p.isdigit()]

    try:
        current_parts = parse_version(current)
        remote_parts = parse_version(remote)

        # Pad shorter version with zeros
        max_len = max(len(current_parts), len(remote_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        remote_parts.extend([0] * (max_len - len(remote_parts)))

        return remote_parts > current_parts
    except (ValueError, AttributeError):
        # If parsing fails, assume remote is newer
        return True


@click.command()
@click.option(
    '--check',
    is_flag=True,
    help='Only check for updates, do not download'
)
@click.option(
    '--force',
    is_flag=True,
    help='Force upgrade even if already on latest version'
)
@click.option(
    '--url',
    envvar='NCCLI_UPGRADE_BASE_URL',
    help='Base URL for upgrades (default: from NCCLI_UPGRADE_BASE_URL env var)'
)
def upgrade(check, force, url):
    """
    Upgrade nc_cli to the latest version.

    Downloads the latest binary from the configured URL and replaces
    the current executable.

    Example:
        export NCCLI_UPGRADE_BASE_URL="https://your-server.com/nc_cli/releases"
        nc_cli upgrade
    """
    if not url:
        click.echo("Error: No upgrade URL configured.", err=True)
        click.echo("Set NCCLI_UPGRADE_BASE_URL environment variable or use --url option.", err=True)
        sys.exit(1)

    current_version = get_current_version()
    click.echo(f"Current version: {current_version}")

    # Fetch remote version
    try:
        click.echo("Checking for updates...")
        remote_version = fetch_remote_version(url)
        click.echo(f"Latest version: {remote_version}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Compare versions
    is_newer = compare_versions(current_version, remote_version)

    if not is_newer and not force:
        click.echo("You are already on the latest version.")
        return

    if is_newer:
        click.echo(f"New version available: {remote_version}")
    elif force:
        click.echo("Forcing upgrade...")

    if check:
        click.echo("Run without --check to upgrade.")
        return

    # Get current executable path
    exe_path = get_executable_path()

    if not exe_path:
        click.echo("Error: Cannot upgrade when running as Python script.", err=True)
        click.echo("Upgrade is only supported for compiled binaries.", err=True)
        sys.exit(1)

    click.echo(f"Executable path: {exe_path}")

    # Confirm upgrade
    if not force:
        if not click.confirm("Do you want to proceed with the upgrade?"):
            click.echo("Upgrade cancelled.")
            return

    # Download new binary
    try:
        tmp_path = download_binary(url, exe_path)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Replace current binary
    try:
        click.echo("Installing new version...")

        # Backup current binary
        backup_path = f"{exe_path}.backup"
        if os.path.exists(exe_path):
            os.rename(exe_path, backup_path)

        # Move new binary to target location
        os.rename(tmp_path, exe_path)

        # Make executable
        st = os.stat(exe_path)
        os.chmod(exe_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        # Remove backup
        if os.path.exists(backup_path):
            os.remove(backup_path)

        click.echo(f"Successfully upgraded to version {remote_version}")
        click.echo("Please restart nc_cli to use the new version.")

    except Exception as e:
        click.echo(f"Error during installation: {e}", err=True)

        # Try to restore backup
        if os.path.exists(backup_path):
            click.echo("Restoring backup...")
            os.rename(backup_path, exe_path)

        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        sys.exit(1)
