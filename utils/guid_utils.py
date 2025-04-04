"""
This python utility pulls together functions around guid extraction.
"""

import re

def extract_guid(line):
    """Extract GUID from a string containing 'guid: <value>'."""
    match = re.search(r'guid:\s*([a-fA-F0-9]+)', line)
    return match.group(1) if match else None

def extract_icon_guid(text):
    """Extract the GUID used in an icon field."""
    match = re.search(r'icon: \{fileID: \d+, guid: ([a-fA-F0-9]+)', text)
    return match.group(1) if match else None

def resolve_guid_to_name(guid, lookup):
    """Resolve a GUID to its name using a lookup dictionary."""
    return lookup.get(guid, f'UNKNOWN({guid})')