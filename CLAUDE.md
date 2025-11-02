# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NC CLI is a Python command-line tool for uploading DNS entries from `/etc/hosts` to MongoDB. The project uses modern Python packaging with `pyproject.toml` and the Click framework for CLI functionality.

## Commands

### Installation and Setup

```bash
# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Install from requirements.txt
pip install -r requirements.txt
```

### Running the CLI

```bash
# Basic usage (may require sudo)
sudo -E nc uploadDns

# With custom options
nc uploadDns --hosts-file /path/to/hosts --database dns_registry --collection hosts

# View help
nc --help
nc uploadDns --help
```

### Development Commands

```bash
# Format code
black nccli/

# Lint code
flake8 nccli/

# Run tests
pytest
```

## Architecture

### Project Structure

- **nccli/cli.py**: Main CLI entry point using Click's group command pattern
- **nccli/commands/**: Individual CLI commands (currently only `upload_dns.py`)
- **nccli/utils/hosts_parser.py**: Parser for /etc/hosts file format
- **nccli/utils/mongodb.py**: MongoDB client with connection management and data upload

### Key Design Patterns

**Command Registration**: Commands are defined as Click command functions and registered with the main CLI group in `cli.py`. To add new commands:
1. Create a new file in `nccli/commands/`
2. Define a Click command function
3. Import and register it in `cli.py` using `main.add_command()`

**Context Managers**: The `MongoDBClient` class implements context manager protocol (`__enter__`/`__exit__`) for automatic connection cleanup.

**Configuration**: MongoDB connection URI is read from the `NCCLI_MONGODB_URI` environment variable, following 12-factor app configuration principles.

### Data Flow

1. `upload_dns` command is invoked via CLI
2. `parse_hosts_file()` reads and parses /etc/hosts
3. Returns list of dictionaries with structure: `{"ip": "...", "hostname": "...", "source": "...", "line_number": ...}`
4. `MongoDBClient` connects to MongoDB using URI from environment
5. Entries are inserted into specified database/collection using `insert_many()`

## Important Notes

- The `/etc/hosts` file typically requires root permissions to read, so commands may need `sudo -E` (the `-E` preserves environment variables)
- The hosts parser handles comments (lines starting with `#`), inline comments, and multiple hostnames per IP
- Each hostname associated with an IP gets its own database entry for easier querying
- MongoDB connection failures are caught and reported with helpful error messages
