'''
This python script compares data in recipies_data.json to the wiki
Allows user to see which pages need to be updated.
'''

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
import pywikibot
import mwparserfromhell
import re
import json
from utils import file_utils
from pywikibot.pagegenerators import PreloadingGenerator
from utils.recipe_utils import normalize_workbench

# Config
test_mode = False

json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "recipe_compare.txt")
debug_log_path = os.path.join(".hidden", "debug_output", "pywikibot", "recipe_compare_debug.txt")
cached_titles_path = os.path.join(".hidden", "debug_output", "pywikibot", "cached_embedded_recipe_pages.txt")
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)

sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
pywikibot.config.throttle = constants.PWB_SETTINGS["throttle"]
pywikibot.config.max_retries = constants.PWB_SETTINGS["max_retries"]
pywikibot.config.retry_wait = constants.PWB_SETTINGS["retry_wait"]
pywikibot.config.user_agent = constants.PWB_SETTINGS["user_agent"]
site = pywikibot.Site("en", "sunhaven")

# Normalization Helpers
def normalize_time_json(value):
    try:
        num = float(value)
        return str(int(num * 60)) if num < 1 else str(int(num))
    except ValueError:
        return str(value).strip()

def normalize_time_wiki(value):
    return re.sub(r"(min|m|hr|h)", "", str(value).lower()).strip()

def parse_ingredients(raw):
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    parsed = []
    for part in parts:
        if "*" in part:
            name, qty = part.split("*", 1)
            parsed.append({"name": name.strip(), "amount": qty.strip()})
        else:
            parsed.append({"name": part.strip(), "amount": "1"})
    return sorted(parsed, key=lambda x: x["name"].lower())

def recipe_matches(expected, wiki, mismatch_info=None):
    normalized_wiki = {
        "workbench": normalize_workbench(wiki["workbench"]),
        "time": normalize_time_wiki(wiki["time"]),
        "yield": str(wiki["yield"]).strip(),
        "ingredients": sorted(wiki["ingredients"], key=lambda x: x["name"].lower())
    }

    if mismatch_info is None:
        mismatch_info = []

    if expected["workbench"] != normalized_wiki["workbench"]:
        mismatch_info.append(f"workbench: {expected['workbench']} ≠ {normalized_wiki['workbench']}")
    if expected["time"] != normalized_wiki["time"]:
        mismatch_info.append(f"time: {expected['time']} ≠ {normalized_wiki['time']}")
    if expected["yield"] != normalized_wiki["yield"]:
        mismatch_info.append(f"yield: {expected['yield']} ≠ {normalized_wiki['yield']}")
    if expected["ingredients"] != normalized_wiki["ingredients"]:
        mismatch_info.append(f"ingredients: {expected['ingredients']} ≠ {normalized_wiki['ingredients']}")

    return not mismatch_info

# Load JSON
with open(json_file_path, "r", encoding="utf-8") as f:
    raw_recipe_data = json.load(f)

json_recipes_by_output_name = {}
for recipe_id, data in raw_recipe_data.items():
    # skip incomplete entries
    if not all(k in data for k in ["output", "inputs", "workbench", "hoursToCraft"]):
        continue
    output = data["output"]
    if not output or "name" not in output:
        continue
    name = output["name"].strip()
    entry = {
        "jsonID":      recipe_id,
        "workbench":   normalize_workbench(data["workbench"]),
        "time":        normalize_time_json(data["hoursToCraft"]),
        "yield":       str(output.get("amount", "1") or "1").strip(),
        "ingredients": sorted(
            [{"name": i["name"], "amount": str(i["amount"]).strip()} for i in data["inputs"]],
            key=lambda x: x["name"].lower()
        )
    }
    json_recipes_by_output_name.setdefault(name, []).append(entry)

# Load wiki titles
if test_mode:
    embedded_titles = {"Acai Bowl", "Basic Fish Bait", "Apple Pie", "Berry Cake", "Blueberry Pie"}
    print(f"🧪 Test mode: comparing {len(embedded_titles)} test pages.")
else:
    if not os.path.exists(cached_titles_path):
        print("❌ No cached embedded recipe list found.")
        sys.exit(1)
    embedded_titles = set(file_utils.read_file_lines(cached_titles_path))

# Preload pages
pages = PreloadingGenerator([pywikibot.Page(site, title) for title in sorted(embedded_titles)])
print(f"📦 Preloading {len(embedded_titles)} pages...")
print("📤 Comparing recipe formatting...")

# Prepare summary lists
mismatch_list           = []  # for w == j mismatches
remove_list             = []  # w > j extras
add_list                = []  # j > w extras
manual_missing_wiki     = []  # j > w fallback
manual_missing_json     = []  # w > j fallback

debug_lines = []
processed   = 0
total       = len(embedded_titles)

for page in pages:
    page_title = page.title()
    if page_title not in json_recipes_by_output_name:
        continue

    processed += 1
    if processed % 250 == 0:
        print(f"  🔄 {processed}/{total} recipes compared")

    try:
        wikicode = mwparserfromhell.parse(page.text)
        wiki_templates = [tpl for tpl in wikicode.filter_templates() if tpl.name.matches("Recipe")]

        # parse every recipe block and capture its wikiID
        wiki_datas = []
        for idx, tpl in enumerate(wiki_templates, start=1):
            raw_time = tpl.get("time").value.strip()
            tpl_id   = tpl.get("id").value.strip() if tpl.has("id") else str(idx)
            wiki_datas.append({
                "wikiID":      tpl_id,
                "workbench":   tpl.get("workbench").value,
                "time":        raw_time,
                "yield":       tpl.get("yield").value.strip() or "1",
                "ingredients": parse_ingredients(tpl.get("ingredients").value)
            })

        expected_list = json_recipes_by_output_name.get(page_title, [])
        w, j = len(wiki_datas), len(expected_list)

        # Case 1: wiki has extra recipes
        if w > j:
            matched_expected = [False] * j
            matched_wiki     = [False] * w

            # exact‑match pass
            for i, wiki_data in enumerate(wiki_datas):
                for k, expected in enumerate(expected_list):
                    if not matched_expected[k]:
                        mismatch_info = []
                        if recipe_matches(expected, wiki_data, mismatch_info):
                            header = page_title
                            if wiki_data.get("wikiID"):
                                header += f" (wikiID {wiki_data['wikiID']})"
                            debug_lines.append(f"[MATCH]    {header}\n")
                            matched_expected[k] = True
                            matched_wiki[i]     = True
                            break

            # all JSON recipes matched?
            if all(matched_expected):
                # flag leftover wiki recipes
                for i, wiki_data in enumerate(wiki_datas):
                    if not matched_wiki[i]:
                        header = page_title
                        if wiki_data.get("wikiID"):
                            header += f" (wikiID {wiki_data['wikiID']})"
                        remove_list.append({"page": page_title, "header": header})
                        debug_lines.append(f"[INVALID - NO LONGER IN JSON] {header}\n")
            else:
                manual_missing_json.append(page_title)
                debug_lines.append(f"[MANUAL REVIEW - MISSING IN JSON] {page_title}\n")

            continue

        # Case 2: JSON has extra recipes
        elif j > w:
            matched_expected = [False] * j
            matched_wiki     = [False] * w

            # exact‑match pass
            for i, wiki_data in enumerate(wiki_datas):
                for k, expected in enumerate(expected_list):
                    if not matched_expected[k]:
                        mismatch_info = []
                        if recipe_matches(expected, wiki_data, mismatch_info):
                            header = page_title
                            if wiki_data.get("wikiID"):
                                header += f" (wikiID {wiki_data['wikiID']})"
                            debug_lines.append(f"[MATCH]    {header}\n")
                            matched_expected[k] = True
                            matched_wiki[i]     = True
                            break

            # all wiki recipes matched?
            if all(matched_wiki):
                # flag leftover JSON recipes
                for k, expected in enumerate(expected_list):
                    if not matched_expected[k]:
                        add_list.append({"page": page_title, "jsonID": expected["jsonID"]})
                        debug_lines.append(
                            f"[MISSING - ADD TO WIKI] {page_title} (jsonID {expected['jsonID']})\n"
                        )
            else:
                manual_missing_wiki.append(page_title)
                debug_lines.append(f"[MANUAL REVIEW - MISSING IN WIKI] {page_title}\n")

            continue

        # Case 3: counts match → two‑pass match/mismatch
        matched_expected = [False] * j
        matched_wiki     = [False] * w

        # Pass 1: exact matches
        for i, wiki_data in enumerate(wiki_datas):
            for k, expected in enumerate(expected_list):
                if not matched_expected[k]:
                    mismatch_info = []
                    if recipe_matches(expected, wiki_data, mismatch_info):
                        header = page_title
                        if wiki_data.get("wikiID"):
                            header += f" (wikiID {wiki_data['wikiID']})"
                        debug_lines.append(f"[MATCH]    {header}\n")
                        matched_expected[k] = True
                        matched_wiki[i]     = True
                        break

        # Pass 2: mismatches
        for k, expected in enumerate(expected_list):
            if not matched_expected[k]:
                idx2 = next((ii for ii, used in enumerate(matched_wiki) if not used), 0)
                wiki_data = wiki_datas[idx2]
                mismatch_info = []
                recipe_matches(expected, wiki_data, mismatch_info)

                header = page_title
                if wiki_data.get("wikiID"):
                    header += f" (wikiID {wiki_data['wikiID']})"

                display_expected = expected.copy()
                display_expected.pop("jsonID", None)

                mismatch_list.append({
                    "page":  page_title,
                    "header": header,
                    "fields": mismatch_info
                })
                debug_lines.append(
                    f"[MISMATCH] {header}\n"
                    f"  Mismatch Fields: {mismatch_info}\n"
                    f"  Expected: {display_expected}\n"
                    f"  Wiki:     {wiki_data}\n"
                )

    except Exception as e:
        debug_lines.append(f"[ERROR] {page_title} - {e}\n")

# Build summary output
output_lines = []

if mismatch_list:
    output_lines.append("### RECIPE MISMATCHES ###\n")
    for m in mismatch_list:
        # main bullet is the header (page + wikiID, etc.)
        output_lines.append(f"{m['header']}\n")
        # under that, one • per mismatched field
        for field in m['fields']:
            output_lines.append(f"  • Mismatch: {field}\n")
        output_lines.append("\n")

if remove_list:
    output_lines.append("### REMOVE FROM WIKI ###\n")
    for r in remove_list:
        output_lines.append(f"{r['header']}\n")
    output_lines.append("\n")

if add_list:
    output_lines.append("### ADD TO WIKI ###\n")
    for a in add_list:
        output_lines.append(f"{a['page']} --- (jsonID {a['jsonID']})\n")
    output_lines.append("\n")

if manual_missing_wiki:
    output_lines.append("### MANUAL REVIEW: MISSING IN WIKI ###\n")
    for page in manual_missing_wiki:
        output_lines.append(f"{page}\n")
    output_lines.append("\n")

if manual_missing_json:
    output_lines.append("### MANUAL REVIEW: MISSING IN JSON ###\n")
    for page in manual_missing_json:
        output_lines.append(f"{page}\n")
    output_lines.append("\n")

# Write out the summary and debug files
file_utils.write_lines(output_file_path, output_lines)
file_utils.write_lines(debug_log_path, debug_lines)

print("✅ Recipe comparison complete.")