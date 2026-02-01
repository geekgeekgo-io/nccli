# NC CLI

A command-line tool for uploading DNS entries from `/etc/hosts` to MongoDB.

## Features

- Parse and extract DNS entries from `/etc/hosts` file
- Upload DNS entries to MongoDB database
- Support for custom hosts files
- Replace or append mode for database uploads
- Clean error handling and user-friendly messages

## Requirements

- Python 3.8 or higher
- MongoDB instance (local or remote)

## Installation

### Quick Install (Recommended)

**macOS (Apple Silicon):**
```bash
curl -fsSL https://github.com/geekgeekgo-io/nccli/releases/latest/download/nccli-darwin-arm64 -o /usr/local/bin/nccli && chmod +x /usr/local/bin/nccli
```

**Linux (x86_64):**
```bash
curl -fsSL https://github.com/geekgeekgo-io/nccli/releases/latest/download/nccli-linux-amd64 -o /usr/local/bin/nccli && chmod +x /usr/local/bin/nccli
```

**Or use the install script:**
```bash
curl -fsSL https://raw.githubusercontent.com/geekgeekgo-io/nccli/main/install.sh | sudo bash
```

See [INSTALL.md](INSTALL.md) for detailed installation instructions including:
- macOS Intel and ARM64
- Linux ARM64
- Installing from source
- Custom install locations
- Troubleshooting

### From Source

```bash
git clone https://github.com/geekgeekgo-io/nccli.git
cd nccli
pip install -e .
```

## Configuration

Set the MongoDB connection URI as an environment variable:

```bash
export NCCLI_MONGODB_URI="mongodb://localhost:27017"
```

For MongoDB with authentication:
```bash
export NCCLI_MONGODB_URI="mongodb://username:password@localhost:27017"
```

For MongoDB Atlas:
```bash
export NCCLI_MONGODB_URI="mongodb+srv://username:password@cluster.mongodb.net"
```

## Usage

### Upload DNS Entries

Basic usage (reads from `/etc/hosts`):
```bash
nc uploadDns
```

**Note:** You may need to run with `sudo` to read `/etc/hosts`:
```bash
sudo -E nc uploadDns
```
The `-E` flag preserves environment variables including `NCCLI_MONGODB_URI`.

### Advanced Options

Specify a custom hosts file:
```bash
nc uploadDns --hosts-file /path/to/custom/hosts
```

Use a custom database name:
```bash
nc uploadDns --database my_dns_db
```

Use a custom collection name:
```bash
nc uploadDns --collection dns_entries
```

Replace existing entries in the database:
```bash
nc uploadDns --replace
```

Combine multiple options:
```bash
sudo -E nc uploadDns --hosts-file /etc/hosts --database dns_registry --collection hosts --replace
```

### View Help

```bash
nc --help
nc uploadDns --help
```

## Data Structure

Each DNS entry is stored in MongoDB with the following structure:

```json
{
  "ip": "127.0.0.1",
  "hostname": "localhost",
  "source": "/etc/hosts",
  "line_number": 1
}
```

## Example /etc/hosts File

```
127.0.0.1       localhost
127.0.1.1       mycomputer.local mycomputer
192.168.1.100   server1.local server1
192.168.1.101   server2.local server2

# IPv6 entries
::1             ip6-localhost ip6-loopback
```

This will create separate entries for each hostname associated with an IP address.

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black nccli/
```

### Linting

```bash
flake8 nccli/
```

## Project Structure

```
geek_cli/
├── nccli/
│   ├── __init__.py
│   ├── cli.py                  # Main CLI entry point
│   ├── commands/
│   │   ├── __init__.py
│   │   └── upload_dns.py       # uploadDns command
│   └── utils/
│       ├── __init__.py
│       ├── hosts_parser.py     # /etc/hosts parser
│       └── mongodb.py          # MongoDB client
├── pyproject.toml              # Project configuration
└── README.md
```

## Troubleshooting

### Permission Denied Error

If you get a permission denied error when reading `/etc/hosts`, run with sudo:
```bash
sudo -E nc uploadDns
```

### MongoDB Connection Error

Verify your MongoDB URI is set correctly:
```bash
echo $NCCLI_MONGODB_URI
```

Test MongoDB connection:
```bash
mongosh "$NCCLI_MONGODB_URI"
```

### No DNS Entries Found

Ensure your hosts file contains valid entries. Each line should have the format:
```
IP_ADDRESS    hostname1 hostname2 ...
```

Lines starting with `#` are treated as comments and ignored.
