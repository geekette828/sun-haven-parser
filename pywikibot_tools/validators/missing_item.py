"""
This python script will review the SH wiki and compare the JSON file with item infobox items
The user must be in the PWB-Core folder and logged in to PyWikiBot using: python pwb.py login
"""
import os
import re
import sys
import json
import time
import fnmatch
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.stdout.reconfigure(encoding='utf-8')

from config import constants
from config.skip_items import SKIP_ITEMS, SKIP_PATTERNS
from collections import defaultdict
from itertools import islice

# Set up paths and pywikibot site
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
site = pywikibot.Site("en", "sunhaven")

output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot")
os.makedirs(output_directory, exist_ok=True)

json_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
infobox_txt_path = os.path.join(output_directory, "infobox_pages.txt")
comparison_wiki_json_path = os.path.join(output_directory, "Item_Comparison_WikiJSON.txt")
comparison_wiki_only_path = os.path.join(output_directory, "Item_Comparison_WikiOnly.txt")
comparison_json_only_path = os.path.join(output_directory, "Item_Comparison_JSONOnly.txt")
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot")

def should_skip(name):
    name = name.lower()
    if name in SKIP_ITEMS:
        return True
    for pattern in SKIP_PATTERNS:
        if fnmatch.fnmatch(name, pattern.lower()):
            return True
    return False

def get_base_and_variant(name):
    name = name.strip().lower()
    name = re.sub(r'[_ ]\d+$', '', name)
    match = re.search(r'^(.*?)\s*\((.*?)\)\s*(.*)$', name)
    if match:
        base = f"{match.group(1).strip()} {match.group(3).strip()}".strip()
        variant = match.group(2).strip().capitalize()
        return base, variant
    return name, None

def categorize_items(item_list):
    categorized = defaultdict(set)
    for item in item_list:
        base_name, variant = split_base_and_variant_display(item)
        if variant:
            categorized[base_name].add(variant)
        elif not re.search(r'\d+$', item):
            categorized[base_name].add(None)
    return categorized

def format_output(categorized_items):
    output_lines = []
    for base_name, variants in sorted(categorized_items.items()):
        output_lines.append(base_name)
        for variant in sorted(filter(None, variants)):
            output_lines.append(f"   - {variant}")
    return "\n".join(output_lines)

def load_json_items():
    with open(json_path, "r", encoding="utf-8") as file:
        raw_data = json.load(file)

    name_to_filename = {}
    for filename, data in raw_data.items():
        display_name = data.get("Name", "").strip()
        if display_name and not should_skip(display_name):
            name_to_filename[display_name] = filename

    return name_to_filename

def split_base_and_variant_display(name):
    """
    Like get_base_and_variant, but preserves original capitalization
    for output. Works directly on the original string.
    """
    original = name.strip()
    # Drop trailing _1 / _2 / " 1" / " 2" style suffixes, but keep case
    no_suffix = re.sub(r'[_ ]\d+$', '', original)

    match = re.search(r'^(.*?)\s*\((.*?)\)\s*(.*)$', no_suffix)
    if match:
        base = f"{match.group(1).strip()} {match.group(3).strip()}".strip()
        variant = match.group(2).strip()
        return base, variant

    return no_suffix, None

# Step 1: Extract wiki pages that transclude infobox templates 
def get_infobox_pages():
    templates = ["Item infobox", "Agriculture infobox", "Animal infobox", "Clothing infobox", "Consumable infobox", "Equipment infobox", "Fish infobox", "Furniture infobox"]
    wiki_names = set()
    with open(infobox_txt_path, "w", encoding="utf-8") as txt_file:
        for template in templates:
            template_page = pywikibot.Page(site, f"Template:{template}")
            for page in template_page.embeddedin(namespaces=[0], content=False):
                title = page.title().strip()
                txt_file.write(title + "\n")
                wiki_names.add(title.lower())
    print(f"Finished gathering {len(wiki_names)} normalized wiki page names.")
    return wiki_names

def get_all_mainspace_titles():
    """
    Gather all titles in mainspace (including redirects) once,
    so existence checks are done locally instead of via per-item API calls.
    """
    print("Gathering all mainspace page titles (including redirects)...")
    all_titles = set()
    # filterredir=None (or omitted) -> both normal pages and redirects
    for page in site.allpages(namespace=0, content=False):
        all_titles.add(page.title().strip().lower())
    print(f"Finished gathering {len(all_titles)} mainspace titles.")
    return all_titles

# Step 2: Compare JSON to infobox list
def compare_infobox_to_json(wiki_names, json_items):
    wiki_base_names = {get_base_and_variant(name)[0] for name in wiki_names}
    json_base_names = {get_base_and_variant(name)[0] for name in json_items}

    both = wiki_base_names & json_base_names
    wiki_only = wiki_base_names - json_base_names
    json_only = json_base_names - wiki_base_names

    print("Finished comparing the wiki page names to the json")
    return both, wiki_only, json_only

# Step 3: Categorize and Write Output Files
def write_outputs(json_items, wiki_names, both, wiki_only, json_only):
    json_names = list(json_items.keys())

    categorized_json_only = categorize_items([
        name for name in json_names
        if get_base_and_variant(name)[0] in json_only
    ])
    categorized_both = categorize_items([
        name for name in json_names
        if get_base_and_variant(name)[0] in both
    ])
    categorized_wiki = categorize_items(wiki_names)

    with open(comparison_json_only_path, "w", encoding="utf-8") as f:
        f.write(format_output(categorized_json_only))

    with open(comparison_wiki_json_path, "w", encoding="utf-8") as f:
        f.write(format_output(categorized_both))

    with open(comparison_wiki_only_path, "w", encoding="utf-8") as f:
        f.write(format_output({
            name: categorized_wiki[name]
            for name in sorted(categorized_wiki)
            if name in wiki_only
        }))

    print("✅ Completed missing data check.")

# Main
json_items = load_json_items()
wiki_names = get_infobox_pages()
all_main_titles = get_all_mainspace_titles()

# Base-name sets
wiki_base_names = {get_base_and_variant(name)[0] for name in wiki_names}
json_base_names = {get_base_and_variant(name)[0] for name in json_items}
all_main_base_names = {get_base_and_variant(title)[0] for title in all_main_titles}

# Items with an infobox and a JSON entry
both = wiki_base_names & json_base_names

# Items that have an infobox but no JSON entry
wiki_only = wiki_base_names - json_base_names

# JSON items whose base name exists on the wiki (page or redirect),
# but do NOT have an infobox
json_with_page_no_infobox = (json_base_names & all_main_base_names) - wiki_base_names

# JSON items whose base name does not exist as any page/redirect
json_only = json_base_names - all_main_base_names

print("Finished comparing the wiki page names, JSON, and overall wiki titles.")

write_outputs(json_items, wiki_names, both, wiki_only, json_only)
print("✅ Completed missing data check.")

