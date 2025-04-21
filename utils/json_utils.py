import json
import os
import logging

logger = logging.getLogger(__name__)


def load_json(
    filepath,
    flatten_values=False,
    normalize_keys=False,
    normalize_values=False,
    encoding='utf-8'
):
    """
    Load JSON data from a file.

    Args:
        filepath (str): Path to the JSON file.
        flatten_values (bool): If True and data is dict, flatten list values into a single list.
        normalize_keys (bool): If True and data is dict, normalize keys by stripping and lowercasing.
        normalize_values (bool): If True and data is dict, normalize string values by stripping whitespace.
        encoding (str): File encoding.

    Returns:
        The loaded JSON object (dict, list, etc.), or None if load fails.
    """
    try:
        with open(filepath, 'r', encoding=encoding) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning("Failed to load JSON from %s: %s", filepath, e)
        return None

    if normalize_keys and isinstance(data, dict):
        data = {k.strip().lower(): v for k, v in data.items()}

    if normalize_values and isinstance(data, dict):
        def _norm(v):
            return v.strip() if isinstance(v, str) else v
        data = {k: _norm(v) for k, v in data.items()}

    if flatten_values and isinstance(data, dict):
        flat = []
        for val in data.values():
            if isinstance(val, list):
                flat.extend(val)
        return flat

    return data


def write_json(
    data,
    filepath,
    indent=4,
    ensure_ascii=False,
    encoding='utf-8'
):
    """
    Write JSON data to a file, creating parent directories as needed.

    Args:
        data (Any): JSON-serializable object.
        filepath (str): Destination file path.
        indent (int): Number of spaces for indentation.
        ensure_ascii (bool): Whether to escape non-ASCII characters.
        encoding (str): File encoding.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding=encoding) as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)


def safe_json_parse(json_string):
    """
    Safely parse a JSON string into an object. Returns None on failure.
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return None


def pretty_print_json(data):
    """
    Return a pretty-printed JSON string.
    """
    return json.dumps(data, indent=4, ensure_ascii=False)


def load_items(
    filepath,
    key_field=None,
    encoding='utf-8'
):
    """
    Load JSON as either dict-of-dicts or list-of-dicts and return a dict.

    Args:
        filepath (str): Path to JSON file.
        key_field (str): When data is a list of dicts, use this field as the dict key.
        encoding (str): File encoding.

    Returns:
        dict: If top-level is dict, returns it directly; if list and key_field is provided, index by that field.
    """
    data = load_json(filepath, encoding=encoding)
    if data is None:
        return {}

    if isinstance(data, dict):
        return data

    if isinstance(data, list) and key_field:
        return {item[key_field]: item for item in data if key_field in item}

    return {}
