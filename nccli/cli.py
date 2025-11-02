"""Main CLI entry point."""

import click
from nccli.commands.upload_dns import upload_dns
from nccli.commands.download_dns import download_dns


@click.group()
@click.version_option()
def main():
    """NC CLI - A tool for managing DNS entries."""
    pass


# Register commands
main.add_command(upload_dns, name="uploadDns")
main.add_command(download_dns, name="downloadDns")


if __name__ == "__main__":
    main()
