import os
import re
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pywikibot_tools.core import item_infobox_core
from utils import file_utils, text_utils
from config import constants
from config.skip_items import SKIP_ITEMS, SKIP_FIELDS

TEST_RUN = False
TEST_PAGES = ["Golden Peach", "Iron Ring", "Candy Corn Fruit Pop", "Watery Protector's Potion"]

json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot")
output_file = os.path.join(output_directory, "item_infobox_compare.txt")
debug_log_path = os.path.join(".hidden", "debug_output", "pywikibot", "item_infobox_compare_debug.txt")

file_utils.ensure_dir_exists(output_directory)
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

KEYS_TO_CHECK = [
    "name", "sell", "currency", "stack", "rarity", "hearts", "dlc",
    "restores", "statInc", "season", "exp", "requirement", "organic"
]

BATCH_SIZE = constants.PWB_SETTINGS["BATCH_SIZE"]
SLEEP_INTERVAL = constants.PWB_SETTINGS["SLEEP_INTERVAL"]

pages = item_infobox_core.get_infobox_pages(TEST_RUN, TEST_PAGES)
data = item_infobox_core.load_normalized_json(json_file_path)

matches = []
mismatches = []
jsononly = list(data.keys())
wikionly = []
debug_lines = []

# Build variant map: base -> [variants]
variant_map = {}
for key in jsononly:
    base_match = re.match(r"^(.*) \(([^)]+)\)$", key)
    if base_match:
        base = base_match.group(1)
        variant_map.setdefault(base, []).append(key)
    elif any(key.endswith(" " + p) for p in ["mount whistle", "pet"]):
        parts = key.split(" ")
        for i in range(1, len(parts)):
            base = " ".join(parts[i:])
            variant_map.setdefault(base, []).append(key)


total = len(pages)
processed = 0

for i in range(0, total, BATCH_SIZE):
    batch = pages[i:i + BATCH_SIZE]
    page_texts = item_infobox_core.fetch_pages(batch)

    for title in batch:
        processed += 1
        text = page_texts.get(title, "")
        normalized_title = text_utils.normalize_apostrophe(title).lower()

        if normalized_title in SKIP_ITEMS:
            continue

        subtype = item_infobox_core.extract_subtype(text)

        # Exact match
        if normalized_title in data:
            diffs, _ = item_infobox_core.compare_page_to_json(
                title,
                text,
                data[normalized_title],
                KEYS_TO_CHECK,
                skip_fields_map=SKIP_FIELDS
            )
            if diffs:
                mismatches.append((title, diffs))
                for field, exp, act in diffs:
                    debug_lines.append(f"[MISMATCH] {title}    {field}: {exp}/{act}")
            else:
                matches.append(title)
                debug_lines.append(f"[MATCH] {title}")
            if normalized_title in jsononly:
                jsononly.remove(normalized_title)

        # Variant match
        elif normalized_title in variant_map:
            matching = []
            differing = []
            for variant in variant_map[normalized_title]:
                if not subtype in ["Mount", "Pet"] and not re.search(r" \([^)]+\)$", variant):
                    continue

                diffs, _ = item_infobox_core.compare_page_to_json(title, text, data[variant], KEYS_TO_CHECK)
                diffs = [
                    d for d in diffs 
                    if d[0] != "name" and not (d[0] == "statInc" and "»999" in str(d[1]))
                ]
                if diffs:
                    for field, exp, act in diffs:
                        differing.append((variant, field, exp, act))
                else:
                    matching.append(variant)
                if variant in jsononly:
                    jsononly.remove(variant)

            if differing:
                debug_lines.append(f"[VARIANT - MISMATCH] {title}")
                mismatch_entry = []
                for variant, field, exp, act in differing:
                    color = variant.replace(normalized_title, '').strip()
                    debug_lines.append(f"     - ({color}) {field}: expected '{exp}' but found '{act}'")
                    mismatch_entry.append((f"({color}) {field}", exp, act))
                if matching:
                    matched_colors = [f"({v.replace(normalized_title, '').strip()})" for v in matching]
                    mismatch_entry.append(("MATCH EXACTLY", ", ".join(matched_colors), ""))
                mismatches.append((title, mismatch_entry))

            if matching and not differing:
                variants = ", ".join(f"({v.replace(normalized_title, '').strip()})" for v in matching)
                debug_lines.append(f"[VARIANT - MATCH] {title} - {variants}")

        else:
            wikionly.append(title)
            debug_lines.append(f"[WIKI ONLY] {title}")

    if i // BATCH_SIZE % 10 == 0:
        percent = round((processed / total) * 100, 1)
        print(f"     🔄 Reviewed {processed} of {total} pages ({percent}% complete). Sleeping {SLEEP_INTERVAL} seconds.")
        if not TEST_RUN:
            time.sleep(SLEEP_INTERVAL)

with open(output_file, "w", encoding="utf-8") as out:
    out.write("=== Mismatches ===\n")
    for title, diffs in mismatches:
        out.write(f"{title}\n")
        for field, exp, act in diffs:
            if field == "MATCH EXACTLY":
                out.write(f"    - {exp} {field}\n")
            else:
                out.write(f"    - {field}: expected '{exp}' but found '{act}'\n")
        out.write("\n")

    out.write("=== JSON Only ===\n")
    for name in sorted(jsononly):
        out.write(f"{name}\n")

    out.write("\n=== WIKI Only ===\n")
    for name in sorted(wikionly):
        out.write(f"{name}\n")

with open(debug_log_path, "w", encoding="utf-8") as dbg:
    dbg.write("\n".join(debug_lines))

print(f"✅ Infobox comparison complete. See: {output_file}")