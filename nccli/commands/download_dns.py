"""Download DNS command."""

import click
import sys
import os
from nccli.utils.hosts_writer import merge_hosts_entries
from nccli.utils.mongodb import MongoDBClient


@click.command()
@click.option(
    '--hosts-file',
    default='/etc/hosts',
    help='Path to hosts file to merge into (default: /etc/hosts)',
    type=click.Path()
)
@click.option(
    '--database',
    default='nc_cli',
    help='MongoDB database name (default: nc_cli)'
)
@click.option(
    '--collection',
    default='dns_hosts',
    help='MongoDB collection name (default: dns_hosts)'
)
@click.option(
    '--backup',
    is_flag=True,
    help='Create a backup of the hosts file before modifying'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be changed without actually modifying the file'
)
def download_dns(hosts_file, database, collection, backup, dry_run):
    """
    Download DNS entries from MongoDB and merge into /etc/hosts.

    Reads DNS entries from MongoDB and merges them with the existing hosts file.
    If a hostname already exists, it will be overwritten with the MongoDB version.

    Example:
        export NCCLI_MONGODB_URI="mongodb://localhost:27017"
        nc downloadDns --backup
    """
    try:
        # Connect to MongoDB and download entries
        click.echo("Connecting to MongoDB...")
        with MongoDBClient() as mongo_client:
            mongo_client.connect(database_name=database, collection_name=collection)
            click.echo(f"Connected to database '{database}', collection '{collection}'")

            entries = mongo_client.download_entries()

            if not entries:
                click.echo("No DNS entries found in MongoDB.", err=True)
                sys.exit(1)

            click.echo(f"Downloaded {len(entries)} DNS entries from MongoDB")

        # Create backup if requested
        if backup and not dry_run:
            backup_file = f"{hosts_file}.backup"
            try:
                import shutil
                shutil.copy2(hosts_file, backup_file)
                click.echo(f"Created backup at {backup_file}")
            except Exception as e:
                click.echo(f"Warning: Failed to create backup: {e}", err=True)

        # Dry run mode
        if dry_run:
            click.echo("\n=== DRY RUN MODE ===")
            click.echo(f"Would merge {len(entries)} entries into {hosts_file}")
            click.echo("\nSample entries to be merged:")
            for entry in entries[:5]:
                click.echo(f"  {entry.get('ip'):<16} {entry.get('hostname')}")
            if len(entries) > 5:
                click.echo(f"  ... and {len(entries) - 5} more")
            click.echo("\nNo changes were made (dry run).")
            return

        # Check write permissions
        if not os.access(hosts_file, os.W_OK):
            if os.path.exists(hosts_file):
                click.echo(
                    f"Error: No write permission for {hosts_file}",
                    err=True
                )
                click.echo("Hint: You may need to run with sudo", err=True)
                sys.exit(1)

        # Merge entries
        click.echo(f"Merging entries into {hosts_file}...")
        added, updated = merge_hosts_entries(hosts_file, entries)

        click.echo(f"\nSuccessfully merged DNS entries:")
        click.echo(f"  - Added: {added} new entries")
        click.echo(f"  - Updated: {updated} existing entries")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    except PermissionError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Hint: You may need to run with sudo to modify /etc/hosts", err=True)
        sys.exit(1)

    except ValueError as e:
        click.echo(f"Configuration Error: {e}", err=True)
        click.echo("Hint: Set NCCLI_MONGODB_URI environment variable", err=True)
        sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
