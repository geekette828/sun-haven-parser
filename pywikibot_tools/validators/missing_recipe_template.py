'''
This python script will create a list of pages and redirects
that do not have `Template:Recipe` based on `recipes_data.json`
'''

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.stdout.reconfigure(encoding='utf-8')

import config.constants as constants
import pywikibot
import json
from utils import file_utils

# Setup PWB and site
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
pywikibot.config.throttle = constants.PWB_SETTINGS["throttle"]
pywikibot.config.max_retries = constants.PWB_SETTINGS["max_retries"]
pywikibot.config.retry_wait = constants.PWB_SETTINGS["retry_wait"]
pywikibot.config.user_agent = constants.PWB_SETTINGS["user_agent"]
site = pywikibot.Site("en", "sunhaven")

# Paths
json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "missing_recipe_templates.txt")
debug_log_path = os.path.join(".hidden", "debug_output", "pywikibot", "missing_recipe_templates_debug.txt")
page_list_path = os.path.join(".hidden", "debug_output", "pywikibot", "cached_embedded_recipe_pages.txt")
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)

# Load JSON recipes
with open(json_file_path, "r", encoding="utf-8") as f:
    raw_recipe_data = json.load(f)

expected_titles = set()
for recipe_id, data in raw_recipe_data.items():
    if not all(k in data for k in ["output"]):
        continue
    output = data["output"]
    if not output or "name" not in output:
        continue
    expected_titles.add(output["name"].strip())

# Step 1: Pull pages using Template:Recipe
template_page = pywikibot.Page(site, "Template:Recipe")
embeddedin_pages = list(template_page.embeddedin(total=10000))
embedded_titles = {page.title() for page in embeddedin_pages}
print(f"Found {len(embedded_titles)} pages using Template:Recipe.")

# Save embedded_titles to file for reuse
file_utils.write_lines(page_list_path, [title + "\n" for title in sorted(embedded_titles)])

# Step 2: Find missing pages
missing_recipe_pages = sorted(expected_titles - embedded_titles)
print(f"Found {len(missing_recipe_pages)} pages missing the recipe template.")

# Step 3: Filter out redirects
redirect_titles = {page.title() for page in site.allpages(filterredir=True)}
redirects_removed = set(missing_recipe_pages) & redirect_titles
missing_recipe_pages = [page for page in missing_recipe_pages if page not in redirect_titles]
print(f"{len(redirects_removed)} redirects removed. {len(missing_recipe_pages)} pages remaining.")

# Step 4: Write output
output_lines = []
debug_lines = []

if missing_recipe_pages:
    output_lines.append("=== Missing Entire Recipe Template ===\n")
    output_lines.extend(page + "\n" for page in sorted(missing_recipe_pages))
    output_lines.append("\n")
    for title in sorted(redirects_removed):
        debug_lines.append(f"[SKIPPED - REDIRECT] {title}")
else:
    output_lines.append("No missing recipe templates found.\n")

file_utils.write_lines(output_file_path, output_lines)
file_utils.write_lines(debug_log_path, debug_lines)

print("Missing recipe template check complete.")