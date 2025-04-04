"""
This python utility pulls together functions around JSON parsing.
"""
import json
import os

def load_json(filepath, flatten_values=False, encoding='utf-8'):
    """Load JSON data from a file, optionally flattening nested lists in dicts."""
    with open(filepath, 'r', encoding=encoding) as f:
        data = json.load(f)
    if flatten_values and isinstance(data, dict):
        flat = []
        for val in data.values():
            if isinstance(val, list):
                flat.extend(val)
        return flat
    return data

def write_json(data, filepath, indent=4, encoding='utf-8'):
    """Write JSON data to a file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding=encoding) as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)

def safe_json_parse(json_string):
    """Safely parse a JSON string into a dictionary."""
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return None

def pretty_print_json(data):
    """Return a pretty-printed JSON string."""
    return json.dumps(data, indent=4, ensure_ascii=False)

