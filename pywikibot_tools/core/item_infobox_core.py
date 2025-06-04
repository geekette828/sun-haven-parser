import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pywikibot
import mwparserfromhell
from utils import text_utils
from mappings.item_infobox_mapping import FIELD_MAP, FIELD_COMPUTATIONS
from utils.compare_utils import compare_instance_generic
from utils.wiki_utils import get_pages_with_template, fetch_pages, parse_template_params

def load_normalized_json(json_file_path):   # Load and normalize the item JSON data.
    from utils import json_utils
    data = json_utils.load_json(json_file_path)
    return {text_utils.normalize_apostrophe(k.lower()): v for k, v in data.items()}

def get_infobox_param_map(wikitext, page_title): # Extract template parameters and inject fallback for name if missing.
    params = parse_template_params(wikitext, "Item infobox")
    if "name" not in params or not params["name"].strip():
        params["name"] = page_title.lower()

    # Strip HTML comments from all values
    for key, val in params.items():
        params[key] = re.sub(r"<!--.*?-->", "", val).strip()

    return params

def compare_page_to_json(title, text, item_data, keys_to_check, skip_fields_map=None):  # Compare a wiki page's infobox to a JSON item.
    wiki_params = get_infobox_param_map(text, title)
    diffs = compare_instance_generic(
        item_data,
        wiki_params,
        keys_to_check,
        FIELD_MAP,
        FIELD_COMPUTATIONS,
        text_utils.normalize_bool,
        skip_fields_map=skip_fields_map or {}
    )
    return diffs, wiki_params

def update_template_fields(template, diffs):    # Apply updated values to a mwparserfromhell template object.
    for field, expected, _ in diffs:
        expected = f" {expected}"  # Ensure space after '='

        if template.has(field):
            param = template.get(field)
            param.value = expected
            if not str(param.value).endswith("\n"):
                param.value = str(param.value) + "\n"
        elif field == "name":
            continue  # Don't add 'name' if not already present
        else:
            # Add with newline to ensure separate line
            template.add(field, expected + "\n")


def update_infobox_text(text, diffs):   # Return modified wikitext with applied diffs.
    parsed = mwparserfromhell.parse(text)
    for template in parsed.filter_templates():
        if template.name.strip().lower() == "item infobox":
            update_template_fields(template, diffs)
            result = str(parsed)
            result = re.sub(r"\n+\}\}$", "\n}}", result)        # Collapse multiple newlines before the end
            result = re.sub(r"(?<!\n)([^\n\S]*)(\n}})$", r"  }}", result)   # Move final '}}' up to the last field line with double space
            return result
    return text  # fallback

def get_infobox_pages(TEST_RUN=False, test_list=None):  # Return list of pages to process, filtered by test mode.
    return test_list if TEST_RUN and test_list else get_pages_with_template("Item infobox", namespace=0)

def extract_subtype(wikitext):
    """
    Parses the wikitext and returns the value of the `subtype` field from the item infobox.
    """
    parsed = mwparserfromhell.parse(wikitext)
    for template in parsed.filter_templates():
        if template.name.strip().lower() == "item infobox":
            if template.has("subtype"):
                return str(template.get("subtype").value).strip()
    return ""

def get_base_variant_key(normalized_title, data, subtype=None):
    """
    Returns a matching base key from the JSON data for a variant item.
    Handles color suffixes (e.g., "Item (Red)") and subtype-based logic (e.g., Mounts, Pets).
    """
    # Case 1: Color in parentheses at the end, e.g., "diner dress (red)"
    base_match = re.match(r"^(.*) \(([^)]+)\)$", normalized_title)
    if base_match:
        base_title = base_match.group(1)
        if base_title in data:
            return base_title, "VARIANTS"

    # Case 2: Subtype match for Mounts or Pets (e.g., "red dragon mount whistle" → "dragon mount whistle")
    if subtype in ["Mount", "Pet"]:
        # Try removing first word as color
        parts = normalized_title.split(" ", 1)
        if len(parts) == 2 and parts[1] in data:
            return parts[1], "VARIANTS"

    return None, ""

