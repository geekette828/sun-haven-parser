import os
import sys
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pywikibot
import mwparserfromhell
from config import constants
from utils import file_utils, json_utils, text_utils
from utils.wiki_utils import get_pages_with_template, get_site, fetch_pages
from mappings.item_infobox_mapping import FIELD_MAP, FIELD_COMPUTATIONS

# Configuration
json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "item_infobox_compare.txt")
debug_log_path = os.path.join(".hidden", "debug_output", "pywikibot", "item_infobox_compare_debug.txt")

file_utils.ensure_dir_exists(os.path.dirname(output_file_path))
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

# Toggle for testing mode
testing = False
test_pages = [
    "Golden Peach",
    "Iron Ring",
    "Candy Corn Fruit Pop",
    "Watery Protector's Potion"
]

site = get_site()

# Load JSON
data = json_utils.load_json(json_file_path)
data = {text_utils.normalize_apostrophe(k.lower()): v for k, v in data.items()}

# Get wiki pages
if testing:
    pages = test_pages  # use real titles, no lowercase
else:
    pages = get_pages_with_template("Item infobox", namespace=0)

matches = []
mismatches = []
wikionly = []
jsononly = list(data.keys())
debug_lines = []

def extract_template_params(wikitext):
    parsed = mwparserfromhell.parse(wikitext)
    for template in parsed.filter_templates():
        if template.name.strip().lower() == "item infobox":
            return {
                p.name.strip(): text_utils.clean_text(str(p.value)).strip()
                for p in template.params
            }
    return {}

def normalize_comparison_value(key, expected, actual):
    expected = expected.strip() if expected else ""
    actual = actual.strip() if actual else ""

    if key == "requirement":
        expected = extract_required_level(expected)
        actual = extract_required_level(actual)
        return expected, actual

    if key in {"selltype", "name", "sell"}:
        return expected.lower(), actual.lower()

    if key == "statInc":
        expected = expected.replace("+", "").lower()
        actual = actual.replace("+", "").lower()
        return expected, actual

    if key in {"dlc", "organic"}:
        expected = text_utils.normalize_bool(expected)
        actual = text_utils.normalize_bool(actual)
        return expected, actual

    return expected, actual

def extract_required_level(value: str) -> str:
    if not value:
        return ""
    import re
    match = re.search(r"\|\s*(\d+)\s*\}\}", value)
    if match:
        return match.group(1)
    return value

# Batch process
batch_size = 50
total = len(pages)
processed = 0

for i in range(0, total, batch_size):
    batch = pages[i:i + batch_size]

    page_texts = fetch_pages(batch)  # batch = list of titles

    if not testing:
        time.sleep(1)

    for title in batch:
        page = pywikibot.Page(site, title)
        processed += 1

        if not testing and processed % 500 == 0:
            pct = int((processed / total) * 100)
            print(f"  🔄 Item infobox compare: {pct}% complete ({processed}/{total})")

        real_title = page.title()
        normalized_title = text_utils.normalize_apostrophe(real_title).lower()
        text = page_texts.get(real_title, "")

        wiki_params = extract_template_params(text)

        if normalized_title not in data:
            wikionly.append(real_title)
            debug_lines.append(f"[WIKI ONLY] {real_title}")
            continue

        item = data[normalized_title]
        expected_values = {}

        for field, (json_key, normalize) in FIELD_MAP.items():
            raw_val = item.get(json_key)
            expected_values[field] = normalize(raw_val)

        for comp_field, compute_fn in FIELD_COMPUTATIONS.items():
            expected_values[comp_field] = compute_fn(item)

        differences = []
        keys_to_check = [
            "name", "sell", "selltype", "stack", "rarity", "hearts", "dlc",
            "restores", "statInc", "season", "exp", "requirement", "organic"
        ]

        for key in keys_to_check:
            if key == "name":
                actual = wiki_params.get(key, "").strip() or real_title.strip()
            else:
                actual = wiki_params.get(key, "").strip()

            # Special handling for "sell" if canSell = 0
            if key == "sell":
                can_sell = item.get("canSell", 1)
                if not can_sell:
                    expected = "no"
                else:
                    expected = expected_values.get(key, "")
            else:
                expected = expected_values.get(key, "")

            norm_expected, norm_actual = normalize_comparison_value(key, expected, actual)

            if norm_expected != norm_actual:
                differences.append(f"    - {key}: expected '{expected}' but found '{actual}'")

        if differences:
            mismatches.append(f"[MISMATCH] {real_title}\n" + "\n".join(differences) + "\n")
            debug_lines.append(f"[MISMATCH] {real_title}")
            for diff in differences:
                debug_lines.append(diff)
        else:
            matches.append(f"[MATCH] {real_title}")
            debug_lines.append(f"[MATCH] {real_title}")

        if normalized_title in jsononly:
            jsononly.remove(normalized_title)

# Process leftover JSON-only entries
for leftover in jsononly:
    debug_lines.append(f"[JSON ONLY] {leftover}")

# Write main output (only mismatches)
with open(output_file_path, "w", encoding="utf-8") as out:
    out.write("=== Mismatches ===\n" + "\n".join(mismatches) + "\n\n")
    out.write("=== Wiki Only ===\n" + "\n".join(wikionly) + "\n\n")
    out.write("=== JSON Only ===\n" + "\n".join(jsononly) + "\n")

# Write debug log (in order)
with open(debug_log_path, "w", encoding="utf-8") as dbg:
    for line in debug_lines:
        dbg.write(line + "\n")

print(f"✅ Item infobox comparison complete: see report at {output_file_path}")
