"""Writer and merger for /etc/hosts file."""

import re
from typing import List, Dict, Tuple
from collections import OrderedDict


def merge_hosts_entries(
    existing_file_path: str,
    new_entries: List[Dict[str, str]],
    output_file_path: str = None
) -> Tuple[int, int]:
    """
    Merge new DNS entries with existing hosts file.

    Reads the existing hosts file, merges new entries from MongoDB,
    and overwrites entries with duplicate hostnames.

    Args:
        existing_file_path: Path to existing hosts file to read
        new_entries: List of DNS entries from MongoDB
        output_file_path: Path to write merged file (defaults to existing_file_path)

    Returns:
        Tuple of (added_count, updated_count)

    Raises:
        FileNotFoundError: If existing file doesn't exist
        PermissionError: If unable to read or write file
    """
    if output_file_path is None:
        output_file_path = existing_file_path

    # Read existing file
    try:
        with open(existing_file_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        raise FileNotFoundError(f"Hosts file not found at {existing_file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied reading {existing_file_path}")

    # Parse existing entries into hostname -> (ip, original_line, line_index) map
    existing_entries = OrderedDict()
    comments_and_empty = []

    for idx, line in enumerate(lines):
        stripped = line.strip()

        # Track comments and empty lines separately
        if not stripped or stripped.startswith('#'):
            comments_and_empty.append((idx, line))
            continue

        # Remove inline comments
        line_content = stripped.split('#')[0].strip()
        parts = re.split(r'\s+', line_content)

        if len(parts) < 2:
            comments_and_empty.append((idx, line))
            continue

        ip_address = parts[0]
        hostnames = parts[1:]

        # Store each hostname with its IP and original line
        for hostname in hostnames:
            if hostname not in existing_entries:
                existing_entries[hostname] = {
                    'ip': ip_address,
                    'line_idx': idx,
                    'all_hostnames': hostnames
                }

    # Create a map of new entries from MongoDB
    new_entries_map = {}
    for entry in new_entries:
        hostname = entry.get('hostname')
        ip = entry.get('ip')
        if hostname and ip:
            new_entries_map[hostname] = ip

    # Track statistics
    added_count = 0
    updated_count = 0

    # Update or add entries
    for hostname, new_ip in new_entries_map.items():
        if hostname in existing_entries:
            # Update existing entry
            old_entry = existing_entries[hostname]
            if old_entry['ip'] != new_ip:
                old_entry['ip'] = new_ip
                updated_count += 1
        else:
            # Add new entry
            existing_entries[hostname] = {
                'ip': new_ip,
                'line_idx': None,  # Will be added at the end
                'all_hostnames': [hostname]
            }
            added_count += 1

    # Reconstruct the hosts file
    # Group entries by IP address for cleaner output
    ip_to_hostnames = OrderedDict()
    entries_to_preserve = OrderedDict()

    # First, preserve existing structure where possible
    for hostname, entry_data in existing_entries.items():
        ip = entry_data['ip']
        line_idx = entry_data['line_idx']

        if line_idx is not None:
            # This was an existing entry, group by line
            if line_idx not in entries_to_preserve:
                entries_to_preserve[line_idx] = {'ip': ip, 'hostnames': []}
            if hostname not in entries_to_preserve[line_idx]['hostnames']:
                entries_to_preserve[line_idx]['hostnames'].append(hostname)
        else:
            # This is a new entry, group by IP
            if ip not in ip_to_hostnames:
                ip_to_hostnames[ip] = []
            ip_to_hostnames[ip].append(hostname)

    # Write the merged file
    try:
        with open(output_file_path, 'w') as f:
            # Write preserved entries and comments in original order
            written_indices = set()

            for idx, line in enumerate(lines):
                if idx in entries_to_preserve:
                    # Write updated entry
                    entry = entries_to_preserve[idx]
                    f.write(f"{entry['ip']:<16} {' '.join(entry['hostnames'])}\n")
                    written_indices.add(idx)
                elif any(comment_idx == idx for comment_idx, _ in comments_and_empty):
                    # Write original comment or empty line
                    f.write(line)
                elif idx not in written_indices:
                    # This line was removed or modified, skip it
                    pass

            # Add new entries at the end
            if ip_to_hostnames:
                f.write("\n# Entries added from MongoDB\n")
                for ip, hostnames in ip_to_hostnames.items():
                    f.write(f"{ip:<16} {' '.join(hostnames)}\n")

    except PermissionError:
        raise PermissionError(f"Permission denied writing to {output_file_path}")

    return added_count, updated_count
