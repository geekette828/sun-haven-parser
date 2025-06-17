import re
from utils import text_utils

def format_time(hours):
    """
    Convert a fractional hour value to a wiki-friendly time string with h/m suffixes.
    Examples:
      0.25 → "15m"
      1.5  → "1h30m"
      2    → "2h"
    """
    try:
        h = float(hours)
    except Exception:
        return str(hours).strip()

    if h < 1:
        minutes = int(round(h * 60))
        return f"{minutes}m"
    hours_part = int(h)
    minutes_part = int(round((h - hours_part) * 60))
    if minutes_part:
        return f"{hours_part}h{minutes_part}m"
    return f"{hours_part}h"


def normalize_time_wiki(value):
    """
    Converts wiki-side time like '1h30m' or '5m' into total minutes for comparison.
    Returns a string of total minutes.
    """
    value = str(value).lower().strip()
    total = 0
    match = re.search(r"(\\d+)h", value)
    if match:
        total += int(match.group(1)) * 60
    match = re.search(r"(\\d+)m", value)
    if match:
        total += int(match.group(1))
    if total == 0:
        try:
            total = int(value)
        except ValueError:
            total = 0
    return str(total)

def parse_time(s):
    s = s.strip().lower().replace(" ", "")
    if "h" in s or "m" in s:
        hours = 0
        minutes = 0
        h_match = re.search(r"(\\d+(\\.\\d+)?)h", s)
        m_match = re.search(r"(\\d+(\\.\\d+)?)m", s)
        if h_match:
            hours = float(h_match.group(1))
        if m_match:
            minutes = float(m_match.group(1))
        return hours + (minutes / 60)
    try:
        return float(s)
    except ValueError:
        return 0

def normalize_ingredient_list(s: str) -> str:
    return text_utils.normalize_list_string(s.replace('Inputs:', ''))

def format_json_ingredients(inputs):
    return "; ".join(f"{item['name']}*{item['amount']}" for item in inputs if item.get("name") and item.get("amount"))