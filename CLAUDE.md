# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NC CLI is a Python command-line tool for syncing DNS entries between `/etc/hosts` and MongoDB. The project uses modern Python packaging with `pyproject.toml` and the Click framework for CLI functionality.

## Commands

### Installation and Setup

```bash
# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running the CLI

```bash
# Upload hosts to MongoDB (may require sudo)
sudo -E nc uploadDns

# Download from MongoDB and merge into hosts file
sudo -E nc downloadDns --backup

# Dry run to preview changes
nc downloadDns --dry-run

# View help
nc --help
```

### Development Commands

```bash
black nccli/      # Format code
flake8 nccli/     # Lint code
pytest            # Run tests
```

## Architecture

### Key Design Patterns

**Command Registration**: Commands are defined as Click command functions and registered with the main CLI group in `cli.py`. To add new commands:
1. Create a new file in `nccli/commands/`
2. Define a Click command function
3. Import and register it in `cli.py` using `main.add_command()`

**Context Managers**: The `MongoDBClient` class implements context manager protocol (`__enter__`/`__exit__`) for automatic connection cleanup.

**Configuration**: MongoDB connection URI is read from the `NCCLI_MONGODB_URI` environment variable.

### Data Flow

**Upload (uploadDns)**:
1. `parse_hosts_file()` reads and parses /etc/hosts
2. Returns list of dicts: `{"ip": "...", "hostname": "...", "source": "...", "line_number": ...}`
3. `MongoDBClient.upload_entries()` inserts into MongoDB

**Download (downloadDns)**:
1. `MongoDBClient.download_entries()` retrieves entries from MongoDB
2. `merge_hosts_entries()` merges with existing hosts file, preserving comments and structure
3. New entries appended under `# Entries added from MongoDB` section

## Important Notes

- Commands typically require `sudo -E` (the `-E` preserves environment variables including `NCCLI_MONGODB_URI`)
- The hosts parser handles comments, inline comments, and multiple hostnames per IP
- Each hostname gets its own database entry for easier querying
- The merge writer preserves existing hosts file structure and only updates/adds entries from MongoDB
