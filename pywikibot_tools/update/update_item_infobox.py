import os
import re
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pywikibot
import mwparserfromhell
from pywikibot_tools.core import item_infobox_core
from utils import file_utils, text_utils
from config import constants
from config.skip_items import SKIP_ITEMS, SKIP_FIELDS

SKIP_VARIANTS_BASE = False       # Skip pages that are base names of variant groups
DRY_RUN = True                  # No actual edits
ADD_HISTORY = False              # Add a history bullet if changes were made

TEST_RUN = False                # Only process test pages
TEST_PAGES = ["Leaf Wrapped Tiger Trout"]

json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "item_infobox_update_debug.txt")

file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

BATCH_SIZE = constants.PWB_SETTINGS["BATCH_SIZE"]
SLEEP_INTERVAL = constants.PWB_SETTINGS["SLEEP_INTERVAL"]
KEYS_TO_CHECK = item_infobox_core.KEYS_TO_CHECK

site = pywikibot.Site()
pages = item_infobox_core.get_infobox_pages(TEST_RUN, TEST_PAGES)
data = item_infobox_core.load_normalized_json(json_file_path)

json_keys_set = set(data.keys())
debug_lines = []
updated = []
skipped = []

def apply_diffs_with_regex(text, diffs):
    parsed = mwparserfromhell.parse(text)
    infobox = None

    for template in parsed.filter_templates():
        if template.name.strip().lower() == "item infobox":
            infobox = template
            break

    if not infobox:
        return text

    template_str = str(infobox)
    lines = template_str.strip().splitlines()

    # Track whether we saw '}}' as a standalone line or merged
    closing_line_index = -1
    closing_inline = False

    for i, line in enumerate(lines):
        if line.strip() == "}}":
            closing_line_index = i
            break
        elif line.strip().endswith("}}"):
            closing_line_index = i
            closing_inline = True
            break

    existing_fields = {param.name.strip(): i for i, param in enumerate(infobox.params)}

    for field, expected, _ in diffs:
        if field == "name":
            continue

        if field == "dlc" and expected.lower() in ["false", "no", "0"]:
            continue

        line_value = f"|{field} = {expected}"

        if field in existing_fields:
            idx = existing_fields[field]
            for i, line in enumerate(lines):
                if re.match(rf"^\|\s*{re.escape(field)}\s*=", line):
                    lines[i] = line_value
                    break
        else:
            insert_idx = closing_line_index if closing_line_index != -1 else len(lines)
            lines.insert(insert_idx, line_value)
            if closing_inline:
                # Fix split closing brace line
                lines[insert_idx + 1:] = ["}}"]

    # Final fix to ensure we have a closing }}
    if not any(line.strip() == "}}" or line.strip().endswith("}}") for line in lines):
        lines.append("}}")

    # Rebuild infobox and substitute back into full page text
    updated_template = "\n".join(lines)
    text = text.replace(template_str, updated_template)
    return text


for i in range(0, len(pages), BATCH_SIZE):
    batch = pages[i:i + BATCH_SIZE]
    page_texts = item_infobox_core.fetch_pages(batch)

    for title in batch:
        text = page_texts.get(title, "")
        normalized_title = text_utils.normalize_apostrophe(title).lower()

        if normalized_title in SKIP_ITEMS:
            continue

        subtype = item_infobox_core.extract_subtype(text)
        item_key = None
        classification = ""

        if normalized_title in data:
            item_key = normalized_title
        else:
            item_key, classification = item_infobox_core.get_base_variant_key(normalized_title, data, subtype)

        if SKIP_VARIANTS_BASE and classification == "VARIANTS":
            debug_lines.append(f"[SKIPPED BASE] {title} (has JSON variants)")
            continue

        if not item_key:
            skipped.append(title)
            debug_lines.append(f"[NO JSON] {title}")
            continue

        diffs, wiki_params = item_infobox_core.compare_page_to_json(
            title, text, data[item_key], KEYS_TO_CHECK, skip_fields_map=SKIP_FIELDS
        )
        if not diffs:
            debug_lines.append(f"[NO CHANGE] {title}")
            continue

        new_text = apply_diffs_with_regex(text, diffs)
        page = pywikibot.Page(site, title)

        try:
            if not DRY_RUN:
                if ADD_HISTORY:
                    from utils.history_utils import append_history_entry
                    changed_fields = [field for field, _, _ in diffs]
                    summary = f"Updated infobox fields: {', '.join(changed_fields)}"
                    patch = constants.PATCH_VERSION
                    new_text = append_history_entry(new_text, summary, patch)

                page.text = new_text
                page.save(summary="Updating item infobox from JSON data")

                if not TEST_RUN:
                    time.sleep(SLEEP_INTERVAL)
            updated.append(title)
            status = "DRY RUN" if DRY_RUN else "UPDATED"
            debug_lines.append(f"[{status}] {title}")
            for field, expected, actual in diffs:
                debug_lines.append(f"    - {field} expected: '{expected}' but found: '{actual}'")
        except Exception as e:
            skipped.append(title)
            debug_lines.append(f"[FAILED] {title} - {str(e)}")

    if i // BATCH_SIZE % 10 == 0:
        percent = round(((i + BATCH_SIZE) / len(pages)) * 100, 1)
        print(f"     🔄 Updated {i + BATCH_SIZE} of {len(pages)} pages ({percent}% complete). Sleeping {SLEEP_INTERVAL} seconds.")
        if not TEST_RUN:
            time.sleep(SLEEP_INTERVAL)

with open(debug_log_path, "w", encoding="utf-8") as dbg:
    dbg.write("\n".join(debug_lines))

print(f"✅ Infobox update complete. {len(updated)} updated, {len(skipped)} skipped.")