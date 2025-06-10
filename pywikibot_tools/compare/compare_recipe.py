import os
import sys
import time
import mwparserfromhell

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pywikibot_tools.core import recipe_core
from utils import file_utils, recipe_utils
from config import constants
from config.skip_items import SKIP_ITEMS, SKIP_FIELDS

json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "recipe_compare.txt")
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "recipe_compare_debug.txt")

file_utils.ensure_dir_exists(os.path.dirname(output_file))
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

mismatches = []
json_only = list(data.keys())
debug_lines = []

total = len(pages)
processed = 0

for i in range(0, total, BATCH_SIZE):
    batch = pages[i:i + BATCH_SIZE]
    page_texts = recipe_core.fetch_pages(batch)

    for title in batch:
        processed += 1
        if title in SKIP_ITEMS:
            continue

        text = page_texts.get(title, "")
        parsed = mwparserfromhell.parse(text)
        templates = [tpl for tpl in parsed.filter_templates() if tpl.name.strip().lower() == "recipe"]

        if not templates:
            debug_lines.append(f"[SKIP] {title} - No recipe templates found")
            continue

        for template in templates:
            matched_json, logs = recipe_core.match_json_recipe(template, title, data, len(templates))
            debug_lines.extend(logs)

            if not matched_json:
                continue

            diffs, wiki_params = recipe_core.compare_page_to_json(
                title,
                str(template),
                matched_json,
                KEYS_TO_CHECK,
                skip_fields_map=SKIP_FIELDS
            )

            clean_diffs = []
            seen_fields = set()
            for field, expected, actual in diffs:
                field_lc = field.lower()
                if field_lc in seen_fields:
                    continue
                seen_fields.add(field_lc)

                norm_expected = normalize_field(field, expected)
                norm_actual = normalize_field(field, actual)
                if norm_expected != norm_actual:
                    clean_diffs.append((field, expected, actual))

            rid = matched_json.get("recipeID")
            if clean_diffs:
                mismatch_msg = f"[MISMATCH] {title} - Recipe ID {rid}"
                debug_lines.append(mismatch_msg)
                for field, exp, act in clean_diffs:
                    debug_lines.append(f"    - {field}: expected '{exp}' but found '{act}'")
                mismatches.append((title, rid, clean_diffs))
            else:
                debug_lines.append(f"[MATCH] {title} - Recipe ID {rid}")

            key = matched_json.get("productName") or matched_json.get("output", {}).get("name")
            if key and key in json_only:
                json_only.remove(key)

    if processed % 500 == 0:
        percent = round((processed / total) * 100, 1)
        print(f"     🔄 Reviewed {processed} of {total} pages ({percent}% complete). Sleeping {SLEEP_INTERVAL} seconds.")
        time.sleep(SLEEP_INTERVAL)

# Write main output
with open(output_file, "w", encoding="utf-8") as out:
    if mismatches:
        out.write("### MISMATCHES\n")
        for title, rid, diffs in mismatches:
            out.write(f"{title} - Recipe ID {rid}\n")
            for field, exp, act in diffs:
                out.write(f"    - {field}: expected '{exp}' but found '{act}'\n")
            out.write("\n")
    if json_only:
        out.write("### JSON ONLY\n")
        for key in json_only:
            rid = data[key].get("recipeID")
            name = data[key].get("output", {}).get("name", "")
            if rid and name:
                out.write(f"recipe {rid} - {name}.asset\n")

# Write debug log
with open(debug_log_path, "w", encoding="utf-8") as f:
    f.write("\n".join(debug_lines))
    f.write("\n")

print(f"✅ Comparison complete. {len(mismatches)} mismatches, {len(json_only)} unmatched JSON entries.")
