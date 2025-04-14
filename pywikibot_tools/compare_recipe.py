'''
This python script compares data in recipies_data.json to the wiki
Allows user to see which pages need to be updated.
'''

import pywikibot
import sys
import os
import re
import json
import time
import config.constants as constants
from utils import file_utils
import mwparserfromhell

# Testing Config
test_mode = False  # Set to False to run the full recipe comparison

# Pull batch size for site.preload()
preload_batch_size = constants.PWB_SETTINGS.get("preload_batch_size", 50)

sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
pywikibot.config.throttle = constants.PWB_SETTINGS["throttle"]
pywikibot.config.max_retries = constants.PWB_SETTINGS["max_retries"]
pywikibot.config.retry_wait = constants.PWB_SETTINGS["retry_wait"]
pywikibot.config.user_agent = constants.PWB_SETTINGS["user_agent"]
site = pywikibot.Site("en", "sunhaven")

# Paths
json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "recipe_compare.txt")
debug_log_path = os.path.join(constants.OUTPUT_DIRECTORY, "Debug", "recipe_compare_debug.txt")
cached_titles_path = os.path.join(constants.OUTPUT_DIRECTORY, "Debug", "cached_embedded_recipe_pages.txt")
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)

# If not in test mode, run the missing recipe check first
if not test_mode:
    import subprocess
    script_path = os.path.join(constants.ROOT_DIRECTORY, "pywikibot_tools", "validators", "missing_recipe_template.py")
    result = subprocess.run(["python", script_path])
    if result.returncode != 0:
        print("❌ Failed to run missing recipe script")
    else:
        print("✅ Missing recipe template check completed.")

# Load JSON recipes
with open(json_file_path, "r", encoding="utf-8") as f:
    raw_recipe_data = json.load(f)

json_recipes_by_output_name = {}
for recipe_id, data in raw_recipe_data.items():
    if not all(k in data for k in ["output", "inputs", "workbench", "hoursToCraft"]):
        continue
    output = data["output"]
    if not output or "name" not in output:
        continue
    output_name = output["name"].strip()
    entry = {
        "workbench": data["workbench"],
        "time": data["hoursToCraft"],
        "yield": output.get("amount", "1") or "1",
        "inputs": sorted(
            [{"name": i["name"], "amount": str(i["amount"])} for i in data["inputs"]],
            key=lambda x: x["name"].lower()
        )
    }
    json_recipes_by_output_name.setdefault(output_name, []).append(entry)

# Comparison helpers
def normalize_time(t):
    t = t.strip().lower().replace("hr", "").replace("h", "").strip()
    # Handle fractional hours like 0.25 as 15m, 0.5 as 30m
    try:
        if "m" not in t and "." in t:
            minutes = round(float(t) * 60)
            return f"{minutes}m"
    except ValueError:
        pass
    return t

def normalize_workbench(wb):
    wb = wb.lower().strip().replace(" ", "")
    if wb.endswith("_0"):
        wb = wb[:-2]
    wb = wb.replace("basicfurnituretable1", "basicfurnituretable")
    return wb

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

def parse_recipe_template_block(template):
    try:
        workbench = normalize_workbench(template.get("workbench").value)
        time = normalize_time(template.get("time").value)
        yield_amt = template.get("yield").value.strip() or "1"
        ingredients_raw = template.get("ingredients")
        if ingredients_raw is None:
            raise ValueError("Missing ingredients field")
        ingredients = parse_ingredients(ingredients_raw.value.strip())
        return {"workbench": workbench, "time": time, "yield": yield_amt, "ingredients": ingredients}
    except Exception as e:
        raise ValueError(f"Template parsing failed: {e}")

def recipe_matches(r1, r2):
    return (
        normalize_workbench(r1["workbench"]) == normalize_workbench(r2["workbench"]) and
        normalize_time(r1["time"]) == normalize_time(r2["time"]) and
        r1["yield"] == r2["yield"] and
        r1["ingredients"] == r2["ingredients"]
    )

# Wiki JSON compare
debug_lines = []
recipe_mismatch_pages = []
output_lines = []

if test_mode:
    embedded_titles = {
        "Acai Bowl",
        "Basic Fish Bait",
        "Apple Pie",
        "Berry Cake",
        "Blueberry Pie"
    }
    print(f"🧪 Test mode: comparing {len(embedded_titles)} selected pages.")
else:
    if not os.path.exists(cached_titles_path):
        print("❌ No cached embedded recipe list found. Run missing template check first.")
        sys.exit(1)
    embedded_titles = set(line.strip() for line in file_utils.read_file_lines(cached_titles_path))

print("📤 Comparing recipe formatting...")
total = len(embedded_titles)
processed = 0
from pywikibot.pagegenerators import PreloadingGenerator

print(f"📦 Preloading {len(embedded_titles)} pages in batches of {preload_batch_size}...")
pages = PreloadingGenerator([pywikibot.Page(site, title) for title in sorted(embedded_titles)], groupsize=preload_batch_size)

for page in pages:
    page_title = page.title()
    if page_title not in json_recipes_by_output_name:
        continue

    processed += 1
    if processed % 250 == 0:
        percent = int((processed / total) * 100)
        print(f"  🔄 Comparing recipes: {percent}% complete ({processed}/{total})")

    try:
        actual_text = page.text
        wikicode = mwparserfromhell.parse(actual_text)
        wiki_recipes = [parse_recipe_template_block(tpl) for tpl in wikicode.filter_templates() if tpl.name.matches("Recipe")]

        expected_recipes = json_recipes_by_output_name.get(page_title, [])
        all_matched = True

        for expected in expected_recipes:
            matched = False
            for wiki in wiki_recipes:
                if recipe_matches(expected, wiki):
                    matched = True
                    break

            if not matched:
                all_matched = False
                recipe_mismatch_pages.append(page_title)
                debug_lines.append(f"[MISMATCH] {page_title} Expected: {expected} Wiki Options: {wiki_recipes}")

        if all_matched:
            debug_lines.append(f"[MATCH] {page_title}")
    except Exception as e:
        debug_lines.append(f"[ERROR] {page_title} - {str(e)}")

if recipe_mismatch_pages:
    output_lines.append("=== Recipe Mismatches ===\n")
    output_lines.extend(page + "\n" for page in sorted(recipe_mismatch_pages))
    output_lines.append("\n")
else:
    output_lines.append("No mismatched pages found.\n")

file_utils.write_lines(output_file_path, output_lines)
file_utils.write_lines(debug_log_path, debug_lines)

print("✅ Recipe comparison complete.")
