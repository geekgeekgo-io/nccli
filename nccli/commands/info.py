"""Version and about commands for nccli."""

import platform
import sys
import click
from nccli import __version__


# ASCII art for nccli
ASCII_LOGO = r"""
 ███╗   ██╗ ██████╗ ██████╗██╗     ██╗
 ████╗  ██║██╔════╝██╔════╝██║     ██║
 ██╔██╗ ██║██║     ██║     ██║     ██║
 ██║╚██╗██║██║     ██║     ██║     ██║
 ██║ ╚████║╚██████╗╚██████╗███████╗██║
 ╚═╝  ╚═══╝ ╚═════╝ ╚═════╝╚══════╝╚═╝
"""

# Metadata
DESCRIPTION = "A CLI tool for managing DNS entries and system configurations"
AUTHOR = "GeekGeekGo"
REPO_URL = "https://github.com/geekgeekgo-io/nccli"
LICENSE = "MIT"


@click.command()
def version():
    """Show the version of nccli."""
    click.echo(f"nccli version {__version__}")


@click.command()
@click.option('--short', '-s', is_flag=True, help='Show short version only')
def about(short):
    """Show information about nccli."""
    if short:
        click.echo(f"nccli v{__version__}")
        return

    # Print ASCII logo
    click.echo(click.style(ASCII_LOGO, fg='cyan'))

    # Print metadata
    click.echo(click.style("NCCLI", fg='green', bold=True))
    click.echo(f"  {DESCRIPTION}")
    click.echo()

    # Version info
    click.echo(click.style("Version Info:", fg='yellow', bold=True))
    click.echo(f"  Version:     {__version__}")
    click.echo(f"  Python:      {platform.python_version()}")
    click.echo(f"  Platform:    {platform.system()} {platform.machine()}")
    click.echo()

    # Links
    click.echo(click.style("Links:", fg='yellow', bold=True))
    click.echo(f"  Repository:  {REPO_URL}")
    click.echo(f"  Releases:    {REPO_URL}/releases")
    click.echo()

    # Author
    click.echo(click.style("Author:", fg='yellow', bold=True))
    click.echo(f"  {AUTHOR}")
    click.echo()

    # License
    click.echo(click.style("License:", fg='yellow', bold=True))
    click.echo(f"  {LICENSE}")
