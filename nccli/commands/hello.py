"""Hello command."""

import click


@click.command()
def hello():
    """Print hello world."""
    click.echo("hello world!")
