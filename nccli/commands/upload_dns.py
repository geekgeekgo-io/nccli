"""Upload DNS command."""

import click
import sys
from nccli.utils.hosts_parser import parse_hosts_file
from nccli.utils.mongodb import MongoDBClient


@click.command()
@click.option(
    '--hosts-file',
    default='/etc/hosts',
    help='Path to hosts file (default: /etc/hosts)',
    type=click.Path(exists=True)
)
@click.option(
    '--database',
    default='geekgeekgo',
    help='MongoDB database name (default: dns_registry)'
)
@click.option(
    '--collection',
    default='dns_hosts',
    help='MongoDB collection name (default: hosts)'
)
@click.option(
    '--replace',
    is_flag=True,
    help='Replace all existing entries in the collection'
)
def upload_dns(hosts_file, database, collection, replace):
    """
    Upload DNS entries from /etc/hosts to MongoDB.

    Reads the hosts file, parses DNS entries, and uploads them to
    a MongoDB database. The MongoDB connection URI must be set in
    the NCCLI_MONGODB_URI environment variable.

    Example:
        export NCCLI_MONGODB_URI="mongodb://localhost:27017"
        nc uploadDns
    """
    try:
        # Parse hosts file
        click.echo(f"Reading hosts file from: {hosts_file}")
        entries = parse_hosts_file(hosts_file)

        if not entries:
            click.echo("No DNS entries found in hosts file.", err=True)
            sys.exit(1)

        click.echo(f"Found {len(entries)} DNS entries")

        # Connect to MongoDB and upload
        click.echo("Connecting to MongoDB...")
        with MongoDBClient() as mongo_client:
            mongo_client.connect(database_name=database, collection_name=collection)
            click.echo(f"Connected to database '{database}', collection '{collection}'")

            if replace:
                click.echo("Replacing existing entries...")

            inserted_count = mongo_client.upload_entries(entries, replace=replace)
            click.echo(f"Successfully uploaded {inserted_count} DNS entries")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    except PermissionError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Hint: You may need to run with sudo to read /etc/hosts", err=True)
        sys.exit(1)

    except ValueError as e:
        click.echo(f"Configuration Error: {e}", err=True)
        click.echo("Hint: Set NCCLI_MONGODB_URI environment variable", err=True)
        sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
