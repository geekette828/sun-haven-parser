"""
This python utility pulls together functions around text clean up and parsing.
"""
import re
from html import unescape

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

def normalize_apostrophe(s):
    """Replace curly apostrophes (’) with straight ones (') for consistency."""
    if not s:
        return ""
    return s.replace("’", "'")

def normalize_value(val: str) -> str:
    """Basic normalization: strip, collapse spaces, remove redundant + in numbers."""
    if val is None:
        return ""
    return clean_whitespace(val).replace("+", "").strip()

def normalize_bool(val: str) -> str:
    """Normalize boolean-ish string to 'True' or 'False'."""
    if not val or str(val).strip().lower() in {"false", "0", "null", ""}:
        return "False"
    return "True"

def normalize_list_string(s: str, delimiter: str = ';') -> str:
    """
    Normalize and sort a delimited list of values.
    Lowercases, trims, sorts, and rejoins with the original delimiter.
    """
    items = [item.strip().lower() for item in (s or "").split(delimiter) if item.strip()]
    return delimiter.join(sorted(items))

# ---------------------------
# Modular text replacement utils
# ---------------------------

def replace_placeholders(text):
    """Replace known tokens like XX with {{PLAYER}}."""
    return text.replace("XX", "{{PLAYER}}") if text else ""

def replace_item_token(text):
    """Replace ITEM with wiki bolded item template."""
    return text.replace("ITEM", "[''item'']") if text else ""

def replace_linebreak_tokens(text):
    """Replace special linebreak tokens like [] or newlines with <br>."""
    if not text:
        return ""
    return text.replace("[]", "<br>").replace("\n", "<br>").strip()

def sanitize_text(text: str) -> str:
    """
    Remove Unity-specific tags from text:
    - <color=...> and </color>
    - <sprite=...>
    """
    if not isinstance(text, str):
        return text

    text = re.sub(r'<color=#[0-9A-Fa-f]{6}>', '', text)
    text = re.sub(r'<color=.*?>', '', text)
    text = text.replace('</color>', '')
    text = re.sub(r'<sprite=.*?>', '', text)

    return text.strip()

# ---------------------------
# Composed full cleaners
# ---------------------------

def format_for_chat(text):
    """
    Format generic text for chat-style output:
    - Replace XX
    - Handle [] and newline as <br>
    """
    if not text:
        return ""
    text = replace_placeholders(text)
    return replace_linebreak_tokens(text)

def clean_dialogue(text: str) -> str:
    """
    Full cleaning pipeline for in-game dialogue:
    - Removes color/sprite tags
    - Replaces ITEM, XX, []
    - Strips HTML
    Leaves formatting like ''' and [[ intact
    """
    if not text:
        return ""
    text = sanitize_text(text)
    text = replace_placeholders(text)
    text = replace_item_token(text)
    text = replace_linebreak_tokens(text)
    return strip_html(text).strip()
