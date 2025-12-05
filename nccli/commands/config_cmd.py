"""Config command for nc_cli."""

import click
import os


@click.command()
@click.option(
    '--init',
    is_flag=True,
    help='Initialize config file with default values'
)
@click.option(
    '--show',
    is_flag=True,
    help='Show current configuration'
)
@click.option(
    '--mongodb-uri',
    default='',
    help='MongoDB connection URI to set in config'
)
def config(init, show, mongodb_uri):
    """
    Manage nc_cli configuration.

    Config file location: ~/.nc_cli/config

    Example:
        nc_cli config --init
        nc_cli config --init --mongodb-uri "mongodb://localhost:27017"
        nc_cli config --show
    """
    from nccli.utils.config import get_config_path, init_config, find_config_file

    if init:
        config_path = init_config(mongodb_uri=mongodb_uri)
        click.echo(f"Config file created at: {config_path}")
        click.echo("")
        click.echo("Edit this file to set your MongoDB URI:")
        click.echo(f"  nano {config_path}")
        return

    if show:
        config_file = find_config_file()
        click.echo("Current Configuration:")
        click.echo("=" * 40)
        click.echo(f"Config file: {config_file or 'Not found'}")
        click.echo("")
        click.echo("Environment Variables:")
        click.echo(f"  NCCLI_MONGODB_URI: {os.environ.get('NCCLI_MONGODB_URI', '(not set)')}")
        click.echo(f"  NCCLI_UPGRADE_BASE_URL: {os.environ.get('NCCLI_UPGRADE_BASE_URL', '(not set)')}")

        if config_file:
            click.echo("")
            click.echo("Config file contents:")
            click.echo("-" * 40)
            with open(config_file, 'r') as f:
                click.echo(f.read())
        return

    # Default: show help
    ctx = click.get_current_context()
    click.echo(ctx.get_help())
