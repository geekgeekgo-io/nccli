"""Hello command."""

import click
from nccli import __version__


@click.command()
def hello():
    """Print hello world."""
    click.echo(f"hello world - {__version__}")
