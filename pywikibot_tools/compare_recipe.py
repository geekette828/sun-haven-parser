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
    if not all(k in data for k in ["output", "inputs", "workbench", "hoursToCraft"]):
        continue
    output = data["output"]
    if not output or "name" not in output:
        continue
    name = output["name"].strip()
    entry = {
        "workbench": normalize_workbench(data["workbench"]),
        "time": normalize_time_json(data["hoursToCraft"]),
        "yield": str(output.get("amount", "1") or "1").strip(),
        "ingredients": sorted(
            [{"name": i["name"], "amount": str(i["amount"]).strip()} for i in data["inputs"]],
            key=lambda x: x["name"].lower()
        )
    }
    json_recipes_by_output_name.setdefault(name, []).append(entry)

# Load wiki
if test_mode:
    embedded_titles = {"Acai Bowl", "Basic Fish Bait", "Apple Pie", "Berry Cake", "Blueberry Pie"}
    print(f"🧪 Test mode: comparing {len(embedded_titles)} test pages.")
else:
    if not os.path.exists(cached_titles_path):
        print("❌ No cached embedded recipe list found.")
        sys.exit(1)
    embedded_titles = set(file_utils.read_file_lines(cached_titles_path))

# Compare
debug_lines = []
recipe_mismatch_pages = []
output_lines = []

pages = PreloadingGenerator([pywikibot.Page(site, title) for title in sorted(embedded_titles)])
print(f"📦 Preloading {len(embedded_titles)} pages...")
total = len(embedded_titles)
processed = 0

print("📤 Comparing recipe formatting...")
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

        if len(wiki_templates) > 1:
            debug_lines.append(f"[SKIPPED MULTI] {page_title} has {len(wiki_templates)} recipe blocks, skipping.\n")
            continue

        tpl = wiki_templates[0]
        raw_time = tpl.get("time").value.strip()
        wiki_data = {
            "workbench": tpl.get("workbench").value,
            "time": raw_time,
            "yield": tpl.get("yield").value.strip() or "1",
            "ingredients": parse_ingredients(tpl.get("ingredients").value)
        }

        matched = False
        for expected in json_recipes_by_output_name[page_title]:
            mismatch_info = []
            if recipe_matches(expected, wiki_data, mismatch_info):
                debug_lines.append(f"[MATCH] {page_title}\n")
                matched = True
                break
            else:
                debug_lines.append(
                    f"[MISMATCH] {page_title}\nExpected: {expected}\nWiki: {wiki_data}\n"
                    f"Mismatch Fields: {mismatch_info}\n"
                )
                recipe_mismatch_pages.append(page_title)

    except Exception as e:
        debug_lines.append(f"[ERROR] {page_title} - {str(e)}")

# Final Output
if recipe_mismatch_pages:
    output_lines.append("=== Recipe Mismatches ===\n")
    output_lines.extend(f"{page}\n" for page in sorted(set(recipe_mismatch_pages)))
    output_lines.append("\n")
else:
    output_lines.append("No mismatched pages found.\n")

file_utils.write_lines(output_file_path, output_lines)
file_utils.write_lines(debug_log_path, debug_lines)

print("✅ Recipe comparison complete.")