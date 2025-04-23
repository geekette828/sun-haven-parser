"""
This python utility pulls together functions around text clean up and parsing.
"""
import re
import unicodedata
from html import unescape

def normalize_apostrophe(s):
    """
    Replaces curly apostrophes (’) with straight ones (') for consistent key comparison.
    """
    if not s:
        return ""
    return s.replace("’", "'")

def strip_html(text):
    """Remove HTML tags and unescape HTML entities."""
    text = re.sub(r'<[^>]+>', '', text)
    return unescape(text)

def clean_whitespace(text):
    """Collapse multiple spaces and trim the string."""
    return re.sub(r'\s+', ' ', text).strip()

def remove_tags(text, tag):
    """Remove specific HTML-style tags from text (e.g., <i>...</i>)."""
    return re.sub(rf'</?{tag}[^>]*>', '', text)

def clean_text(text):
    """Apply multiple cleaning steps: strip HTML, clean whitespace."""
    return clean_whitespace(strip_html(text))

def replace_placeholders(text):
    """Replace known tokens like XX with template-friendly values."""
    return text.replace("XX", "{{PLAYER}}") if text else ""

def format_for_chat(text):
    """Replace placeholders and format line breaks for chat display."""
    if not text:
        return ""
    text = replace_placeholders(text)
    return text.replace("\n", "<br>").replace("[]", "<br>").strip()

def normalize_list_string(s: str, delimiter: str = ';') -> str:
    """
    Normalize and sort a delimited list of values.
    - Lowercases each entry
    - Strips whitespace
    - Sorts the list
    - Joins back with the original delimiter

    Example: "Water Fruit*3; Mana*10" -> "mana*10;water fruit*3"
    """
    items = [item.strip().lower() for item in (s or "").split(delimiter) if item.strip()]
    return delimiter.join(sorted(items))

def sanitize_text(value: str) -> str:
    """
    Remove Unity-specific color and sprite tags from game-exported text.

    Examples removed:
    <color=#FFC332>...</color>
    <sprite="max_defense_icon" index=0>
    """
    if not isinstance(value, str):
        return value

    # Remove <color=...> and </color>
    value = re.sub(r'<color=#[0-9A-Fa-f]{6}>', '', value)
    value = value.replace('</color>', '')

    # Remove <sprite=...> including optional index
    value = re.sub(r'<sprite=.*?>', '', value)

    return value.strip()
