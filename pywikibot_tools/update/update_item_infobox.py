import os
import re
import sys
import time
import pywikibot
import mwparserfromhell

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from config.skip_items import SKIP_ITEMS, SKIP_FIELDS
from pywikibot_tools.core import item_infobox_core
from utils import file_utils, text_utils

SKIP_VARIANTS_BASE = True       # Skip pages that are base names of variant groups
DRY_RUN = False                  # No actual edits
ADD_HISTORY = False              # Add a history bullet if changes were made

TEST_RUN = False                # Only process test pages
TEST_PAGES = ["Leaf Wrapped Tiger Trout"]

JSON_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
OUTPUT_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "pywikibot", "item_infobox_update.txt")
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "item_infobox_update_debug.txt")

file_utils.ensure_dir_exists(os.path.dirname(OUTPUT_FILE))
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

BATCH_SIZE = constants.PWB_SETTINGS["BATCH_SIZE"]
SLEEP_INTERVAL = constants.PWB_SETTINGS["SLEEP_INTERVAL"]

site = pywikibot.Site()


def fetch_pages(titles):
    page_texts = {}
    page_objs = [pywikibot.Page(site, t) for t in titles]
    for page in site.preloadpages(page_objs):
        page_texts[page.title()] = page.text or ""
    return page_texts


pages = item_infobox_core.get_infobox_pages(TEST_RUN, TEST_PAGES)
data = item_infobox_core.load_normalized_json(JSON_FILE)

debug_lines = []
updated = []
skipped = []
change_lines = []


def apply_diffs_with_regex(text, diffs):
    parsed = mwparserfromhell.parse(text)
    infobox = item_infobox_core.find_infobox_template(parsed)

    if not infobox:
        return text

    template_str = str(infobox)
    lines = template_str.strip().splitlines()

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

        if field == "dlc" and str(expected).lower() in ["false", "no", "0"]:
            continue

        if expected is None or str(expected).strip() == "": # will not overwrite if we don't have a value
            continue

        line_value = f"|{field} = {expected}"

        if field in existing_fields:
            for i, line in enumerate(lines):
                if re.match(rf"^\|\s*{re.escape(field)}\s*=", line):
                    lines[i] = line_value
                    break
        else:
            insert_idx = closing_line_index if closing_line_index != -1 else len(lines)
            lines.insert(insert_idx, line_value)
            if closing_inline:
                lines[insert_idx + 1:] = ["}}"]

    if not any(line.strip() == "}}" or line.strip().endswith("}}") for line in lines):
        lines.append("}}")

    updated_template = "\n".join(lines)
    text = text.replace(template_str, updated_template)
    return text


for i in range(0, len(pages), BATCH_SIZE):
    batch = pages[i:i + BATCH_SIZE]
    page_texts = fetch_pages(batch)

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
            title,
            text,
            data[item_key],
            None,
            skip_fields_map=SKIP_FIELDS,
            all_data=data,
        )

        def normalize_stat_plus(value):
            if value is None:
                return value
            value = str(value)
            # remove leading + inside stat brackets, keep -
            return re.sub(r'«\+', '«', value)

        effective_diffs = []
        for field, expected, actual in diffs:
            if field == "name":
                continue

            # skip dlc=false/no/0
            if field == "dlc" and str(expected).lower() in ["false", "no", "0"]:
                continue

            # skip overwriting wiki values when JSON is blank
            if expected is None or str(expected).strip() == "":
                debug_lines.append(f"[SKIP BLANK EXPECTED] {title} - {field} (wiki='{actual}')")
                continue

            # ignore + vs no-sign differences for statInc ONLY
            if field == "statInc":
                if normalize_stat_plus(expected) == normalize_stat_plus(actual):
                    debug_lines.append(
                        f"[SKIP PLUS ONLY] {title} - {field} "
                        f"(expected='{expected}', actual='{actual}')"
                    )
                    continue

            effective_diffs.append((field, expected, actual))

        if not effective_diffs:
            debug_lines.append(f"[NO APPLICABLE CHANGE] {title}")
            continue

        diffs = effective_diffs

        missing_seed = wiki_params.get(item_infobox_core.AGRI_MISSING_SEED_KEY, "")
        if missing_seed:
            debug_lines.append(
                f"[AGRI NO SEED JSON] {title} - seed='{missing_seed}' (seed-derived fields left as-is on wiki)"
            )

        if not diffs:
            debug_lines.append(f"[NO CHANGE] {title}")
            continue

        change_lines.append(f"{title}")
        for field, expected, actual in diffs:
            change_lines.append(f"* {field}: actual:'{actual}' → expected:'{expected}'")
        change_lines.append("")  # blank line between pages

        new_text = apply_diffs_with_regex(text, diffs)
        page = pywikibot.Page(site, title)

        try:
            if not DRY_RUN:
                if ADD_HISTORY:
                    from utils.history_utils import append_history_entry
                    changed_fields = [field for field, _, _ in diffs]
                    summary = f"Updated {title} infobox fields: {', '.join(changed_fields)}"
                    patch = constants.PATCH_VERSION.replace("PBE ", "").strip()
                    new_text = append_history_entry(new_text, summary, patch)

                page.text = new_text
                changed_fields = [field for field, expected, actual in diffs if field != "name"]

                seen = set()
                changed_fields = [f for f in changed_fields if not (f in seen or seen.add(f))]

                MAX_FIELDS_IN_SUMMARY = 4
                if len(changed_fields) <= MAX_FIELDS_IN_SUMMARY:
                    summary = f"Update infobox from JSON: {', '.join(changed_fields)}"
                else:
                    shown = changed_fields[:MAX_FIELDS_IN_SUMMARY]
                    remaining = len(changed_fields) - MAX_FIELDS_IN_SUMMARY
                    summary = (
                        f"Update infobox from JSON: "
                        f"{', '.join(shown)} (+{remaining} more)"
                    )
                page.save(summary=summary)

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
        print(
            f"     🔄 Updated {i + BATCH_SIZE} of {len(pages)} pages ({percent}% complete). Sleeping {SLEEP_INTERVAL} seconds."
        )
        if not TEST_RUN:
            time.sleep(SLEEP_INTERVAL)

with open(debug_log_path, "w", encoding="utf-8") as dbg:
    dbg.write("\n".join(debug_lines))
with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    out.write("\n".join(change_lines))

print(f"✅ Infobox update complete. {len(updated)} updated, {len(skipped)} skipped.")
