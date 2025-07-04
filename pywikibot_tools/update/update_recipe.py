import os
import re
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pywikibot
import mwparserfromhell
from pywikibot_tools.core import recipe_core
from mappings.recipe_mapping import RECIPE_FIELD_MAP
from utils import file_utils, text_utils, recipe_utils
from config import constants
from config.skip_items import SKIP_ITEMS, SKIP_FIELDS

SKIP_WORKBENCH = True           # Skip updating the workbench
SKIP_SKILL_TOMES = True         # Skip items that have the words "Skill Tome" in them.

DRY_RUN = False                 # No actual edits
ADD_HISTORY = True              # Add a history bullet if changes were made

TEST_RUN = False                # Only process test pages
TEST_PAGES = ["Elven Wood End Table"]

json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
debug_log_path = os.path.join(".hidden", "debug_output", "pywikibot", "recipe_update_debug.txt")
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

KEYS_TO_CHECK = ["product", "workbench", "ingredients", "time", "yield", "id"]
BATCH_SIZE = constants.PWB_SETTINGS["BATCH_SIZE"]
SLEEP_INTERVAL = constants.PWB_SETTINGS["SLEEP_INTERVAL"]

site = pywikibot.Site()
pages = recipe_core.get_recipe_pages(TEST_RUN, TEST_PAGES) + recipe_core.get_recipe_none_pages(TEST_RUN, TEST_PAGES)
pages = list(dict.fromkeys(pages))  # Removes duplicates while preserving order
data = recipe_core.load_normalized_json(json_file_path)

debug_lines = []
updated = []
skipped = []

def normalize_field(field, value):
    if not value:
        return ""
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

def find_json_by_id_or_product(data, title):
    for key, entry in data.items():
        if entry.get("recipeID") == title:
            return key, entry
    return recipe_core.find_json_by_product_name(data, title)

def title_case_ingredients(value):
    parts = [x.strip().title() for x in value.split(";") if x.strip()]
    return "; ".join(parts)

def apply_diffs_with_regex(text, diffs, target_template):
    template_str = str(target_template)
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

    existing_fields = {param.name.strip(): i for i, param in enumerate(target_template.params)}

    for field, expected, _ in diffs:
        if field == "product":
            continue
        if SKIP_WORKBENCH and field == "workbench":
            continue

        if field == "ingredients":
            expected = title_case_ingredients(expected)
        elif field == "time":
            try:
                expected = recipe_utils.format_time(float(expected.strip()))
            except ValueError:
                expected = recipe_utils.format_time(recipe_utils.parse_time(expected.strip()))

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
    return text.replace(template_str, updated_template)

for i in range(0, len(pages), BATCH_SIZE):
    batch = pages[i:i + BATCH_SIZE]
    page_texts = recipe_core.fetch_pages(batch)

    batch_index = i // BATCH_SIZE
    if batch_index > 0 and batch_index % 10 == 0:
        percent = round(((i + BATCH_SIZE) / len(pages)) * 100, 1)
        print(f"     🔄 Updated {i + BATCH_SIZE} of {len(pages)} pages ({percent}% complete). Sleeping {SLEEP_INTERVAL} seconds.")
        if not TEST_RUN:
            time.sleep(SLEEP_INTERVAL)

    for title in batch:
        did_save_page = False
        text = page_texts.get(title, "")
        if title in SKIP_ITEMS or (SKIP_SKILL_TOMES and "skill tome" in title.lower()):
            continue

        parsed = mwparserfromhell.parse(text)
        templates = [tpl for tpl in parsed.filter_templates() if tpl.name.strip().lower() == "recipe"]

        if not templates:
            for tpl in parsed.filter_templates():
                if tpl.name.strip().lower() == "recipe/none":
                    key, matched_json = find_json_by_id_or_product(data, title)
                    match_logs = [f"[ID/NAME MATCH] {title} → {key}"] if matched_json else [f"[NO MATCH] {title}"]
                    debug_lines.extend(match_logs)
                    if not matched_json:
                        debug_lines.append(f"[RECIPE/NONE - NO MATCH] {title}")
                        break

                    mapped = {}
                    for param, (json_key, normalizer) in RECIPE_FIELD_MAP.items():
                        value = matched_json
                        if isinstance(json_key, str):
                            for key_part in json_key.split("."):
                                value = value.get(key_part, {}) if isinstance(value, dict) else {}
                        mapped[param] = normalizer(value)
                    mapped["id"] = matched_json.get("recipeID", "").strip()
                    mapped["recipesource"] = matched_json.get("recipesource", "").strip()

                    lines = ["{{Recipe"]
                    for name in ["product", "workbench", "ingredients", "time", "yield", "id", "recipesource"]:
                        lines.append(f"|{name} = {mapped.get(name, '')}")
                    lines[-1] += "}}"
                    formatted_tpl = "\n".join(lines)

                    parsed.replace(tpl, formatted_tpl)
                    text = str(parsed)
                    parsed = mwparserfromhell.parse(text)
                    templates = [tpl for tpl in parsed.filter_templates() if tpl.name.strip().lower() == "recipe"]

                    debug_lines.append(f"[REPLACED RECIPE/NONE] {title}")

                    page = pywikibot.Page(site, title)
                    try:
                        if not DRY_RUN:
                            if ADD_HISTORY:
                                from utils.history_utils import append_history_entry
                                product = mapped.get("product", title)
                                summary = f"[[{product}]] can now be crafted."
                                patch = constants.PATCH_VERSION
                                text = append_history_entry(text, summary, patch)
                            page.text = text
                            page.save(summary="Adding recipe to craft item.")
                            if not TEST_RUN:
                                time.sleep(SLEEP_INTERVAL)
                        updated.append(title)
                        debug_lines.append(f"[{'DRY RUN' if DRY_RUN else 'UPDATED'}] {title}")
                        did_save_page = True
                    except Exception as e:
                        skipped.append(title)
                        debug_lines.append(f"[FAILED] {title} - {str(e)}")
                    break

            if did_save_page or not templates:
                continue

        if did_save_page:
            continue

        for template in templates:
            matched_json, match_logs = recipe_core.match_json_recipe(template, title, data, len(templates))
            debug_lines.extend(match_logs)

            if not matched_json:
                product = template.get("product").value.strip() if template.has("product") else title
                matches = [
                    (k, v) for k, v in data.items()
                    if isinstance(v.get("output"), dict) and v["output"].get("name", "").strip().lower() == product.lower()
                ]
                if len(matches) == 1 and len(templates) == 1:
                    key, matched_json = matches[0]
                    debug_lines.append(f"[FALLBACK PRODUCT MATCH] {title} → {key}")
                elif len(matches) > 1:
                    debug_lines.append(f"[FALLBACK ABORT] {title} - Multiple JSON matches for '{product}'")
                    continue
                else:
                    debug_lines.append(f"[NO MATCH] {title} - No JSON match for product '{product}'")
                    continue

            diffs, wiki_params = recipe_core.compare_page_to_json(
                title, str(template), matched_json, KEYS_TO_CHECK, skip_fields_map=SKIP_FIELDS
            )

            seen = set()
            clean_diffs = []
            for field, expected, actual in diffs:
                if field.lower() in seen:
                    continue
                seen.add(field.lower())

                if field == "id" and not matched_json.get("recipeID"):
                    continue

                norm_expected = normalize_field(field, expected)
                norm_actual = normalize_field(field, actual)
                if norm_expected != norm_actual:
                    clean_diffs.append((field, expected, actual))

            non_skipped_diffs = [
                (f, e, a) for f, e, a in clean_diffs
                if not (SKIP_WORKBENCH and f == "workbench")
            ]

            if not non_skipped_diffs:
                debug_lines.append(f"[NO CHANGE] {title}")
                continue

            new_text = apply_diffs_with_regex(text, clean_diffs, template)
            page = pywikibot.Page(site, title)

            try:
                if not DRY_RUN:
                    if ADD_HISTORY:
                        from utils.history_utils import append_history_entry
                        changed_fields = [field for field, _, _ in non_skipped_diffs]
                        summary = f"Updated recipe fields: {', '.join(changed_fields)}"
                        patch = constants.PATCH_VERSION
                        new_text = append_history_entry(new_text, summary, patch)

                    summary = f"Updating {', '.join([f for f, _, _ in non_skipped_diffs])}."
                    page.text = new_text
                    page.save(summary=summary)
                    if not TEST_RUN:
                        time.sleep(SLEEP_INTERVAL)

                updated.append(title)
                status = "DRY RUN" if DRY_RUN else "UPDATED"
                debug_lines.append(f"[{status}] {title}")
                for field, expected, actual in clean_diffs:
                    if field == "workbench" and SKIP_WORKBENCH:
                        continue
                    debug_lines.append(f"    - {field} expected: '{expected}' but found: '{actual}'")
            except Exception as e:
                skipped.append(title)
                debug_lines.append(f"[FAILED] {title} - {str(e)}")

with open(debug_log_path, "w", encoding="utf-8") as dbg:
    dbg.write("\n".join(debug_lines))

print(f"✅ Recipe template update complete. {len(updated)} updated, {len(skipped)} skipped.")
