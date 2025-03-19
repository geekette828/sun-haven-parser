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

# Define paths
output_directory = os.path.join(config.OUTPUT_DIRECTORY, "Pywikibot")
os.makedirs(output_directory, exist_ok=True)
infobox_pages_path = os.path.join(output_directory, "infobox_pages.txt")
comparison_summary_path = os.path.join(output_directory, "comparison_summary.txt")
comparison_output_path = os.path.join(output_directory, "wiki_json_compare.txt")
json_path = os.path.join(config.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")

# Normalize name for comparison
def normalize_name(name):
    return name.strip().lower().replace("_", " ")

# Load JSON items
def load_json_items():
    with open(json_path, "r", encoding="utf-8") as file:
        json_data = json.load(file)
    return {normalize_name(name): item for name, item in json_data.items()}

# Retrieve all pages transcluding given templates and store them in a file
def get_infobox_pages():
    site = pywikibot.Site("en", "sunhaven")
    templates = ["Item infobox", "Agriculture infobox"]
    wiki_names = set()
    
    with open(infobox_pages_path, "w", encoding="utf-8") as f:
        for template_name in templates:
            template_page = pywikibot.Page(site, f"Template:{template_name}")
            transclusions = template_page.embeddedin(namespaces=[0])
            for page in transclusions:
                norm_name = normalize_name(page.title())
                wiki_names.add(norm_name)
                f.write(f"{page.title()}\n")
    
    return wiki_names

# Compare the retrieved wiki pages to JSON and categorize the results
def compare_infobox_to_json(wiki_names, json_items):
    def get_base_name(name):
        return re.sub(r' \(.*?\)$', '', name)  # Remove color/variant from the end of the name
    wiki_base_names = {get_base_name(name) for name in wiki_names}
    json_base_names = {get_base_name(name) for name in json_items.keys()}
    
    wiki_only = wiki_base_names - json_base_names
    json_only = json_base_names - wiki_base_names
    both = wiki_base_names & json_base_names
    
    with open(comparison_summary_path, "w", encoding="utf-8") as f:
        f.write("##### Wiki and JSON File #####\n")
        for item in sorted(both):
            f.write(f"{item}\n")
        
        f.write("\n\n##### Wiki Only #####\n")
        for item in sorted(wiki_only):
            f.write(f"{item}\n")
        
        f.write("\n\n##### JSON Only #####\n")
        for item in sorted(json_only):
            f.write(f"{item}\n")
    
    return both

# Extract wiki data from pages
def extract_infobox_data(page):
    text = page.text
    extracted_data = {}
    
    # Extract fields from wiki
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

# Compare wiki and JSON data for items found in both lists
def compare_wiki_json(both_items):
    site = pywikibot.Site("en", "sunhaven")
    json_items = load_json_items()
    comparison_results = []
    
    for item in list(both_items)[:10]:
        time.sleep(1)  # Prevent API rate limit
        page = pywikibot.Page(site, item)
        if not page.exists():
            continue
        
        wiki_data = extract_infobox_data(page)
        base_item = re.sub(r' \(.*?\)$', '', item)  # Normalize base name
        json_data = json_items.get(base_item, {})
        
        comparison_results.append(f"{item}:")
        for wiki_field, wiki_value in wiki_data.items():
            json_value = json_data.get(wiki_field, "Unknown")
            comparison_results.append(f"  {wiki_field}: Wiki -> {wiki_value}, JSON -> {json_value}")
        comparison_results.append("")
    
    with open(comparison_output_path, "w", encoding="utf-8") as f:
        f.write("Comparison of Wiki and JSON Data:\n\n")
        f.write("\n".join(comparison_results))

print("Starting: Retrieving pages with infobox templates...")
# Main execution
json_items = load_json_items()
wik_names = get_infobox_pages()
print(f"Success: Infobox pages written to {infobox_pages_path}")
both_items = compare_infobox_to_json(wik_names, json_items)
print(f"Success: Comparison summary written to {comparison_summary_path}")
print("Starting: Wiki-JSON comparison...")
compare_wiki_json(both_items)

print(f"Retrieved infobox pages written to {infobox_pages_path}")
print(f"Comparison summary written to {comparison_summary_path}")
print(f"Wiki-JSON comparison written to {comparison_output_path}")
