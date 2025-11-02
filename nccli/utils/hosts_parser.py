"""Parser for /etc/hosts file."""

import re
from typing import List, Dict


def parse_hosts_file(file_path: str = "/etc/hosts") -> List[Dict[str, str]]:
    """
    Parse /etc/hosts file and return list of DNS entries.

    Args:
        file_path: Path to hosts file (defaults to /etc/hosts)

    Returns:
        List of dictionaries containing IP and hostname mappings
        Format: [{"ip": "127.0.0.1", "hostname": "localhost"}, ...]
    """
    entries = []

    try:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                # Strip whitespace and skip empty lines and comments
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Remove inline comments
                line = line.split('#')[0].strip()

                # Split by whitespace
                parts = re.split(r'\s+', line)
                if len(parts) < 2:
                    continue

                ip_address = parts[0]
                hostnames = parts[1:]

                # Create an entry for each hostname associated with this IP
                for hostname in hostnames:
                    entries.append({
                        "ip": ip_address,
                        "hostname": hostname,
                        "source": file_path,
                        "line_number": line_num
                    })

    except FileNotFoundError:
        raise FileNotFoundError(f"Hosts file not found at {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied reading {file_path}")

    return entries
