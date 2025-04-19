'''
Automatically update mismatched recipes on the Sun Haven wiki to match JSON source data.
'''

import os
import sys
SCRIPT = os.path.dirname(__file__)           # .../pywikibot_tools/update
TOOLS = os.path.abspath(os.path.join(SCRIPT, ".."))      # .../pywikibot_tools
ROOT  = os.path.abspath(os.path.join(TOOLS, ".."))       # your project root

sys.path.insert(0, TOOLS)  # now compare_recipe.py is on the path
sys.path.insert(0, ROOT)   # still need root for config/ and utils/

import config.constants as constants
import pywikibot
import mwparserfromhell
import json
from collections import Counter
from utils.file_utils import read_file_lines, write_lines
from utils.recipe_utils import normalize_workbench, format_time
from compare_recipe import compare_recipes

# Pywikibot configuration
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
pywikibot.config.throttle = constants.PWB_SETTINGS["throttle"]
pywikibot.config.max_retries = constants.PWB_SETTINGS["max_retries"]
pywikibot.config.retry_wait = constants.PWB_SETTINGS["retry_wait"]
pywikibot.config.user_agent = constants.PWB_SETTINGS["user_agent"]
SITE = pywikibot.Site("en", "sunhaven")

# Paths (reuse same as compare_recipe)
JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
CACHED_TITLES_PATH = os.path.join(".hidden", "debug_output", "pywikibot", "cached_embedded_recipe_pages.txt")
SKIPPED_MULTIPLE_MISMATCHES_PATH = os.path.join(".hidden", "debug_output", "pywikibot", "skipped_multiple_mismatch_pages.txt")
DEBUG_LOG_PATH = os.path.join(".hidden", "debug_output", "pywikibot", "recipe_compare_debug.txt")

def load_raw_json_map():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    mapping = {}
    for raw in data.values():
        name = raw.get("output", {}).get("name", "").strip()
        if not name:
            continue
        mapping.setdefault(name, []).append(raw)
    return mapping


def update_page_fields(page, expected_raw, fields, wiki_id, multiple_templates, skipped_pages):
    original = page.text
    code = mwparserfromhell.parse(original)

    if multiple_templates:
        print(f"⚠️  Skipping update — multiple mismatches on page: {page.title()}")
        skipped_pages.append(page.title())
        return

    tpl = next((t for t in code.filter_templates() if t.name.matches("Recipe")), None)
    if not tpl:
        print(f"⚠️  No recipe template found on page: {page.title()}")
        return

    for mismatch in fields:
        key = mismatch.split(":", 1)[0]
        if key == "workbench":
            new_wb = normalize_workbench(expected_raw.get("workbench", ""))
            tpl.add("workbench", new_wb, preserve_spacing=True)
        elif key == "time":
            raw_time = expected_raw.get("hoursToCraft", "0")
            new_time = format_time(raw_time)  # ✅ uses utils.format_time
            tpl.add("time", new_time, preserve_spacing=True)
        elif key == "yield":
            amount = str(expected_raw.get("output", {}).get("amount", "1") or "1").strip()
            tpl.add("yield", amount, preserve_spacing=True)
        elif key == "ingredients":
            inputs = expected_raw.get("inputs", [])
            ingr = "; ".join(f"{i.get('name','')}*{i.get('amount','')}" for i in inputs)
            tpl.add("ingredients", ingr, preserve_spacing=True)

    new_text = str(code)
    if new_text.strip() != original.strip():
        summary = "PyWikiBot: updated mismatch: " + "; ".join(fields)
        page.text = new_text
        page.save(summary=summary)
        print(f"Updated page: {page.title()} | {summary}")
    else:
        print(f"⚠️  No changes detected on page: {page.title()} — skipping save")
        skipped_pages.append(page.title())

def main():
    if not os.path.exists(CACHED_TITLES_PATH):
        print("❌ Missing cached recipe pages list.")
        return
    embedded_titles = set(read_file_lines(CACHED_TITLES_PATH))

    # get mismatches and progress
    result = compare_recipes(embedded_titles, print_progress=True)

    # always write debug output from result
    write_lines(DEBUG_LOG_PATH, result.get("debug_lines", []))

    raw_map = load_raw_json_map()

    # count mismatches per page
    mismatch_list = result.get("mismatch_list", [])
    mismatch_counts = Counter(m["page"] for m in mismatch_list)

    skipped_pages = []

    for mismatch in mismatch_list:
        page_title = mismatch["page"]
        if mismatch_counts[page_title] > 1:
            print(f"⚠️  Skipping page with multiple mismatches: {page_title}")
            skipped_pages.append(page_title)
            continue

        fields = mismatch.get("fields", [])
        header = mismatch.get("header", "")
        wiki_id = header.split("wikiID", 1)[-1].strip("() ") if "wikiID" in header else "1"
        expected_list = raw_map.get(page_title, [])
        if not expected_list:
            continue
        expected = next((r for r in expected_list if str(r.get("jsonID")) == wiki_id or str(expected_list.index(r)+1) == wiki_id), expected_list[0])
        page = pywikibot.Page(SITE, page_title)
        multiple_templates = False  # already filtered above
        print(f"Processing mismatch fields on: {page_title} (wikiID {wiki_id})")
        update_page_fields(page, expected, fields, wiki_id, multiple_templates, skipped_pages)

    if skipped_pages:
        write_lines(SKIPPED_MULTIPLE_MISMATCHES_PATH, sorted(set(skipped_pages)))
        print(f"📄 Skipped {len(skipped_pages)} pages due to multiple mismatches or no changes: {SKIPPED_MULTIPLE_MISMATCHES_PATH}")


if __name__ == "__main__":
    main()
