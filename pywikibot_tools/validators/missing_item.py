"""
This python script will review the SH wiki and compare the JSON file with item infobox items
The user must be in the PWB-Core folder and logged in to PyWikiBot using: python pwb.py login
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.stdout.reconfigure(encoding='utf-8')

import config.constants as constants
import pywikibot
import json
import re
import time
import fnmatch
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
        base_name, variant = get_base_and_variant(item)
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

# Step 1: Extract wiki pages that transclude infobox templates 
def get_infobox_pages():
    templates = ["Item infobox", "Agriculture infobox"]
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

# Step 2: Compare JSON to infobox list
def compare_infobox_to_json(wiki_names, json_items):
    wiki_base_names = {get_base_and_variant(name)[0] for name in wiki_names}
    json_base_names = {get_base_and_variant(name)[0] for name in json_items}

    both = wiki_base_names & json_base_names
    wiki_only = wiki_base_names - json_base_names
    json_only = json_base_names - wiki_base_names

    print("Finished comparing the wiki page names to the json")
    return both, wiki_only, json_only

# Step 3: Check for pages/redirects for JSON-only names
def recheck_jsononly_against_wiki(json_items, json_only):
    recovered = set()
    to_check = [
        name for name in json_items
        if get_base_and_variant(name)[0] in json_only
    ]

    print("Beginning the comparison between the left over json names and the wiki")

    def chunked(iterable, size):
        it = iter(iterable)
        while True:
            chunk = list(islice(it, size))
            if not chunk:
                break
            yield chunk

    batch_size = 20
    last_percent = -1
    total = len(to_check)

    for idx, batch in enumerate(chunked(to_check, batch_size)):
        pages = [pywikibot.Page(site, name) for name in batch]

        while True:
            try:
                preloaded = site.preloadpages(pages)
                for original, page in zip(batch, preloaded):
                    if page.exists():
                        recovered.add(get_base_and_variant(original)[0])
                break
            except pywikibot.exceptions.APIError as e:
                if 'ratelimited' in str(e).lower():
                    print(f"⚠️ Rate limited. Sleeping for {batch_size} seconds...")
                    time.sleep(batch_size)
                    batch_size = min(batch_size * 2, 60)
                else:
                    raise

        time.sleep(0.1)

        progress = min((idx + 1) * batch_size, total)
        percent = int((progress / total) * 100)
        if percent % 25 == 0 and percent != last_percent:
            print(f"Comparison progress: {progress}/{total} -- {percent}%")
            last_percent = percent

    print("Completed the comparison between the left over json names and the wiki")

    os.makedirs(debug_log_path, exist_ok=True)
    recovered_log_path = os.path.join(debug_log_path, "MissingDataCheck_recoveredRedirects.txt")
    with open(recovered_log_path, "w", encoding="utf-8") as f:
        for item in sorted(recovered):
            f.write(f"{item}\n")

    json_only -= recovered
    return recovered, json_only

# Step 4: Categorize and Write Output Files
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
both, wiki_only, json_only = compare_infobox_to_json(wiki_names, json_items)
recovered, json_only = recheck_jsononly_against_wiki(json_items, json_only)
both |= recovered
write_outputs(json_items, wiki_names, both, wiki_only, json_only)
