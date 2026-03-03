"""Upgrade command for nccli using GitHub Releases."""

import click
import json
import os
import platform
import sys
import stat
import ssl
import tempfile
import urllib.request
import urllib.error
from pathlib import Path


# Default GitHub repository (owner/repo format)
DEFAULT_GITHUB_REPO = "geekgeekgo-io/nccli"


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


def get_platform_asset_name():
    """Get the asset name for the current platform."""
    system = platform.system().lower()  # darwin, linux, windows
    machine = platform.machine().lower()  # arm64, x86_64, amd64

    # Normalize architecture names
    if machine in ('x86_64', 'amd64'):
        arch = 'amd64'
    elif machine in ('arm64', 'aarch64'):
        arch = 'arm64'
    else:
        arch = machine

    return f"nccli-{system}-{arch}"


def fetch_latest_release(repo, base_url=None):
    """Fetch the latest release info from GitHub API or custom URL."""
    ssl_context = get_ssl_context()

    if base_url:
        # Custom URL mode: fetch version.txt and binary directly
        version_url = f"{base_url.rstrip('/')}/version.txt"
        try:
            with urllib.request.urlopen(version_url, timeout=10, context=ssl_context) as response:
                version = response.read().decode('utf-8').strip()
            return {
                'tag_name': f'v{version}' if not version.startswith('v') else version,
                'version': version.lstrip('v'),
                'assets': [],
                'base_url': base_url,
            }
        except urllib.error.URLError as e:
            raise Exception(f"Failed to fetch version from {version_url}: {e}")

    # GitHub API mode
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    headers = {'Accept': 'application/vnd.github.v3+json'}

    request = urllib.request.Request(api_url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=10, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
            return {
                'tag_name': data['tag_name'],
                'version': data['tag_name'].lstrip('v'),
                'assets': data.get('assets', []),
                'html_url': data.get('html_url', ''),
            }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise Exception(f"No releases found for repository: {repo}")
        raise Exception(f"GitHub API error: {e}")
    except urllib.error.URLError as e:
        raise Exception(f"Failed to connect to GitHub: {e}")


def find_asset_url(release_info, asset_name):
    """Find the download URL for the specified asset."""
    # Custom URL mode
    if 'base_url' in release_info:
        return f"{release_info['base_url'].rstrip('/')}/nccli"

    # GitHub mode
    for asset in release_info.get('assets', []):
        if asset['name'] == asset_name:
            return asset['browser_download_url']

    # Try without extension
    for asset in release_info.get('assets', []):
        if asset['name'].startswith(asset_name):
            return asset['browser_download_url']

    return None


def download_binary(url, dest_path):
    """Download binary from URL."""
    try:
        click.echo(f"Downloading from {url}...")

        ssl_context = get_ssl_context()
        request = urllib.request.Request(url)
        request.add_header('Accept', 'application/octet-stream')

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            with urllib.request.urlopen(request, timeout=120, context=ssl_context) as response:
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
                        click.echo(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", nl=False)

                click.echo()  # New line after progress

            tmp_path = tmp_file.name

        return tmp_path

    except urllib.error.URLError as e:
        raise Exception(f"Failed to download binary: {e}")


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
    '--repo',
    envvar='NCCLI_GITHUB_REPO',
    default=DEFAULT_GITHUB_REPO,
    help='GitHub repository (owner/repo format)'
)
@click.option(
    '--url',
    envvar='NCCLI_UPGRADE_BASE_URL',
    help='Custom base URL for upgrades (overrides GitHub)'
)
def upgrade(check, force, repo, url):
    """
    Upgrade nccli to the latest version.

    Downloads the latest binary from GitHub Releases (or custom URL)
    and replaces the current executable.

    \b
    Examples:
        nccli upgrade              # Upgrade from default GitHub repo
        nccli upgrade --check      # Check for updates only
        nccli upgrade --force      # Force reinstall current version

    \b
    Environment variables:
        NCCLI_GITHUB_REPO       - GitHub repository (default: geekgeekgo-io/nccli)
        NCCLI_UPGRADE_BASE_URL  - Custom URL (overrides GitHub)
    """
    current_version = get_current_version()
    click.echo(f"Current version: {current_version}")

    # Get platform info
    asset_name = get_platform_asset_name()
    click.echo(f"Platform: {asset_name}")

    # Fetch latest release
    try:
        click.echo("Checking for updates...")
        if url:
            click.echo(f"Using custom URL: {url}")
            release_info = fetch_latest_release(repo, base_url=url)
        else:
            click.echo(f"Checking GitHub: {repo}")
            release_info = fetch_latest_release(repo)

        remote_version = release_info['version']
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
        click.echo("", err=True)
        click.echo("To install the compiled binary, run:", err=True)
        click.echo(f"  curl -fsSL https://github.com/{repo}/releases/latest/download/{asset_name} -o /usr/local/bin/nccli", err=True)
        click.echo("  chmod +x /usr/local/bin/nccli", err=True)
        sys.exit(1)

    click.echo(f"Executable path: {exe_path}")

    # Find download URL
    download_url = find_asset_url(release_info, asset_name)
    if not download_url:
        click.echo(f"Error: No binary found for platform: {asset_name}", err=True)
        click.echo("Available assets:", err=True)
        for asset in release_info.get('assets', []):
            click.echo(f"  - {asset['name']}", err=True)
        sys.exit(1)

    # Confirm upgrade
    if not force:
        if not click.confirm("Do you want to proceed with the upgrade?"):
            click.echo("Upgrade cancelled.")
            return

    # Download new binary
    try:
        tmp_path = download_binary(download_url, exe_path)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Replace current binary
    backup_path = f"{exe_path}.backup"
    try:
        click.echo("Installing new version...")

        # Backup current binary
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
        click.echo("Please restart nccli to use the new version.")

    except Exception as e:
        click.echo(f"Error during installation: {e}", err=True)

        # Try to restore backup
        if os.path.exists(backup_path):
            click.echo("Restoring backup...")
            try:
                os.rename(backup_path, exe_path)
            except Exception:
                pass

        # Clean up temp file
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        sys.exit(1)
