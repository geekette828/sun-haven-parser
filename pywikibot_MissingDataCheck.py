"""
This python module will review the SH wiki and compare the JSON file with item infobox items
The user must be in the PWB-Core folder and logged in to PyWikiBot using: python pwb.py login
"""

import sys
sys.path.append(r"C:\Users\marjo\PWB\core") 
import pywikibot
site = pywikibot.Site()

import os
import config
import json
import re
import time
from collections import defaultdict

# Define paths
output_directory = os.path.join(config.OUTPUT_DIRECTORY, "Pywikibot")
os.makedirs(output_directory, exist_ok=True)
comparison_wiki_json_path = os.path.join(output_directory, "Comparison_WikiJSON.txt")
comparison_wiki_only_path = os.path.join(output_directory, "Comparison_WikiOnly.txt")
comparison_json_only_path = os.path.join(output_directory, "Comparison_JSONOnly.txt")
comparison_output_path = os.path.join(output_directory, "Comparison_Infobox.txt")
json_path = os.path.join(config.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")

def get_base_and_variant(name):
    name = name.strip().lower()
    name = re.sub(r'[_ ]\d+$', '', name)  # Remove trailing numeric suffixes

    # Only handle (variant) cases, ignore all others
    match = re.search(r'^(.*?)\s*\((.*?)\)\s*(.*)$', name)
    if match:
        # Combine front and back parts of the base name without extra space
        front = match.group(1).strip()
        back = match.group(3).strip()
        base = f"{front} {back}".strip()
        variant = match.group(2).strip().capitalize()
        return base, variant

    return name, None  # Don't group or show variant if no parentheses

def categorize_items(item_list):
    categorized = defaultdict(set)
    for item in item_list:
        base_name, variant = get_base_and_variant(item)
        if variant:  # Only include if it's a parenthetical variant
            categorized[base_name].add(variant)
    return categorized

def format_output(categorized_items):
    output_lines = []
    for base_name, variants in sorted(categorized_items.items()):
        output_lines.append(base_name)
        sorted_variants = sorted(variants)
        for variant in sorted_variants:
            output_lines.append(f"   - {variant}")
    return "\n".join(output_lines)

def load_json_items():
    with open(json_path, "r", encoding="utf-8") as file:
        json_data = json.load(file)
    return {name: item for name, item in json_data.items()}

def get_infobox_pages():
    site = pywikibot.Site("en", "sunhaven")
    templates = ["Item infobox", "Agriculture infobox"]
    wiki_names = set()
    for template_name in templates:
        template_page = pywikibot.Page(site, f"Template:{template_name}")
        transclusions = template_page.embeddedin(namespaces=[0])
        for page in transclusions:
            norm_name = page.title().strip().lower()
            norm_name = re.sub(r'[_ ]\d+$', '', norm_name)
            norm_name = re.sub(r'^(.*?)\s*\((.*?)\)\s*(.*)$', lambda m: f"{m.group(1).strip()} {m.group(3).strip()}".strip(), norm_name)
            wiki_names.add(norm_name)
    return wiki_names

def compare_infobox_to_json(wiki_names, json_items):
    wiki_base_names = {get_base_and_variant(name)[0] for name in wiki_names}
    json_base_names = {get_base_and_variant(name)[0] for name in json_items.keys()}

    wiki_only = wiki_base_names - json_base_names
    json_only = json_base_names - wiki_base_names
    both = wiki_base_names & json_base_names

    categorized_wiki = categorize_items(wiki_names)
    categorized_json = categorize_items(json_items.keys())

    with open(comparison_wiki_json_path, "w", encoding="utf-8") as f:
        f.write(format_output({name: categorized_json[name] for name in sorted(both)}))

    with open(comparison_wiki_only_path, "w", encoding="utf-8") as f:
        f.write(format_output({name: categorized_wiki[name] for name in sorted(wiki_only)}))

    with open(comparison_json_only_path, "w", encoding="utf-8") as f:
        f.write(format_output({name: categorized_json[name] for name in sorted(json_only)}))

    return both

def extract_infobox_data(page):
    text = page.text
    extracted_data = {}
    field_mappings = {
        "sell": ["sellPrice", "orbsSellPrice", "ticketSellPrice"],
        "stack": "stackSize",
        "rarity": "rarity",
        "hearts": "hearts",
        "organic": "isFruit",
        "statInc": "foodStat",
        "effect": "stats",
        "exp": "experience",
        "requirement": "requiredLevel",
        "restores": ["health", "mana"]
    }
    for wiki_field, json_fields in field_mappings.items():
        match = re.search(rf"\|\s*{wiki_field}\s*=\s*(.*?)\s*($|\n)", text)
        extracted_data[wiki_field] = match.group(1).strip() if match else "Unknown"
    return extracted_data

def compare_wiki_json(both_items):
    site = pywikibot.Site("en", "sunhaven")
    json_items = load_json_items()
    comparison_results = []
    for item in list(both_items)[:10]:
        time.sleep(1)
        page = pywikibot.Page(site, item)
        if not page.exists():
            continue
        wiki_data = extract_infobox_data(page)
        base_item, _ = get_base_and_variant(item)
        json_data = json_items.get(base_item, {})
        comparison_results.append(f"{item}:")
        for wiki_field, wiki_value in wiki_data.items():
            json_value = json_data.get(wiki_field, "Unknown")
            comparison_results.append(f"  {wiki_field}: Wiki -> {wiki_value}, JSON -> {json_value}")
        comparison_results.append("")
    with open(comparison_output_path, "w", encoding="utf-8") as f:
        f.write("Comparison of Wiki and JSON Data:\n\n")
        f.write("\n".join(comparison_results))

# Main execution
json_items = load_json_items()
wik_names = get_infobox_pages()
both_items = compare_infobox_to_json(wik_names, json_items)
compare_wiki_json(both_items)
