import os
import re
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import mwparserfromhell
from pywikibot_tools.core import recipe_core
from utils import file_utils, text_utils, recipe_utils
from config import constants
from config.skip_items import SKIP_ITEMS, SKIP_FIELDS

json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot")
output_file = os.path.join(output_directory, "recipe_compare.txt")
debug_log_path = os.path.join(".hidden", "debug_output", "pywikibot", "recipe_compare_debug.txt")

file_utils.ensure_dir_exists(output_directory)
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

KEYS_TO_CHECK = ["product", "workbench", "ingredients", "time", "yield", "id"]

BATCH_SIZE = constants.PWB_SETTINGS["BATCH_SIZE"]
SLEEP_INTERVAL = constants.PWB_SETTINGS["SLEEP_INTERVAL"]

def normalize_field(field, value):
    if field == "ingredients":
        parts = [x.strip().lower().replace(" ", "") for x in value.split(";") if x.strip()]
        return ";".join(sorted(parts))
    if field == "time":
        try:
            return recipe_utils.format_time(float(value.strip()))
        except ValueError:
            try:
                parsed = recipe_utils.parse_time(value.strip())
                return recipe_utils.format_time(parsed)
            except Exception:
                return value.strip().lower()
    return value.strip().lower()

pages = recipe_core.get_recipe_pages()
data = recipe_core.load_normalized_json(json_file_path)

matches = []
mismatches = []
jsononly = list(data.keys())
wikionly = []
debug_lines = []

total = len(pages)
processed = 0

for i in range(0, total, BATCH_SIZE):
    batch = pages[i:i + BATCH_SIZE]
    page_texts = recipe_core.fetch_pages(batch)

    for title in batch:
        processed += 1
        text = page_texts.get(title, "")
        parsed = mwparserfromhell.parse(text)
        templates = [tpl for tpl in parsed.filter_templates() if tpl.name.strip().lower() == "recipe"]

        if title in SKIP_ITEMS:
            continue

        if not templates:
            debug_lines.append(f"[SKIP] {title} - No recipe templates found")
            wikionly.append(title)
            continue

        for template in templates:
            if len(templates) == 1:
                product = template.get("product").value.strip() if template.has("product") else title
                json_key, json_entry = recipe_core.find_json_by_product_name(data, product)
            else:
                template_id = template.get("id").value.strip() if template.has("id") else None
                if not template_id:
                    debug_lines.append(f"[SKIP] {title} - Template with no ID")
                    continue
                json_entry = next((v for v in data.values() if str(v.get("recipeID")) == template_id), None)
                json_key = json_entry.get("productName") if json_entry else None

            if not json_entry:
                debug_lines.append(f"[SKIP] {title} - Could not match template")
                continue

            if not json_entry.get("output"):
                debug_lines.append(f"[SKIP] {title} - Missing output block in JSON")
                continue

            diffs, wiki_params = recipe_core.compare_page_to_json(
                title,
                str(template),
                json_entry,
                KEYS_TO_CHECK,
                skip_fields_map=SKIP_FIELDS
            )

            seen = set()
            clean_diffs = []
            for field, expected, actual in diffs:
                key = field.lower()
                if key in seen:
                    continue
                seen.add(key)
                norm_expected = normalize_field(field, expected)
                norm_actual = normalize_field(field, actual)
                if norm_expected != norm_actual:
                    clean_diffs.append((field, expected, actual))

            if clean_diffs:
                mismatches.append((title, clean_diffs))
                for field, exp, act in clean_diffs:
                    debug_lines.append(f"[MISMATCH] {title}    {field}: {exp}/{act}")
            else:
                matches.append(title)
                debug_lines.append(f"[MATCH] {title}")

            if json_key in jsononly:
                jsononly.remove(json_key)

    if i // BATCH_SIZE % 10 == 0:
        percent = round((processed / total) * 100, 1)
        print(f"     🔄 Reviewed {processed} of {total} pages ({percent}% complete). Sleeping {SLEEP_INTERVAL} seconds.")
        time.sleep(SLEEP_INTERVAL)

with open(output_file, "w", encoding="utf-8") as out:
    out.write("=== Mismatches ===\n")
    for title, diffs in mismatches:
        out.write(f"{title}\n")
        for field, exp, act in diffs:
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

print(f"✅ Recipe template comparison complete. See: {output_file}")
