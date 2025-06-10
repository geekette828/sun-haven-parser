'''
This script creates missing item pages. 
This script is dependent on output from
pywikibot_tools/validators/missing_item.py
'''

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import config.constants as constants
import pywikibot
import time

from formatter.page_assembly.create_item_page import create_item_page
from utils.file_utils import read_file_lines, write_debug_log
from utils.json_utils import load_json
from config.skip_items import SKIP_ITEMS, SKIP_PATTERNS

# Set up necessary configurations
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
site = pywikibot.Site()

# Paths
input_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "NEWITEMS.txt")
json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
debug_log_path = os.path.join(constants.OUTPUT_DIRECTORY, "Debug", "pywikibot_create_item_page.txt")

# Constants
CHUNK_SIZE = 750
CHUNK_SLEEP_SECONDS = 3
SUMMARY_TEXT = "New item from most recent patch page creation."

# Load items data
items_data = load_json(json_file_path)
items_data_lower = {key.lower(): value for key, value in items_data.items()}

# Load skip items
skip_items_lower = {item.lower() for item in SKIP_ITEMS}
skip_patterns_lower = [pattern.lower().replace('*', '') for pattern in SKIP_PATTERNS]

# Read the items list
item_names = [line.strip() for line in read_file_lines(input_file)]
total = len(item_names)
actual_processed = 0

# Function to check skip patterns
def should_skip(item_name):
    item_lower = item_name.lower()
    if item_lower in skip_items_lower:
        return True
    for pattern in skip_patterns_lower:
        if item_lower.endswith(pattern):
            return True
    return False

# Initial terminal output
print("🔍 Checking missing pages list...")
write_debug_log("--- Starting page creation log ---", debug_log_path)

# Main processing loop
processed_in_chunk = 0
for idx, item_name in enumerate(item_names, 1):
    if should_skip(item_name):
        write_debug_log(f"Skipped '{item_name}' (matched skip pattern/item)", debug_log_path)
        continue

    key = item_name.lower()
    if key not in items_data_lower:
        write_debug_log(f"Item '{item_name}' not found in JSON data. Skipped.", debug_log_path)
        continue

    # Title-case the page name
    page_title = item_name.title()

    # Check if page exists
    page = pywikibot.Page(site, page_title)
    if page.exists():
        write_debug_log(f"Wiki page '{page_title}' already exists. Skipped.", debug_log_path)
        continue

    # Generate content using formatter
    item = items_data_lower[key]
    page_content = create_item_page(item, display_name=page_title)

    # Post to wiki
    try:
        page.text = page_content
        page.save(summary=SUMMARY_TEXT, minor=False)
        write_debug_log(f"Successfully created page '{page_title}'", debug_log_path)
        actual_processed += 1
    except Exception as e:
        write_debug_log(f"Failed to create page '{page_title}': {e}", debug_log_path)

    processed_in_chunk += 1

    # Progress updates every 10%
    if idx % max(total // 10, 1) == 0:
        percent = (actual_processed / total) * 100
        print(f"  ✅ {actual_processed}/{total} page creations complete — ({percent:.1f}%).")

    # Chunk handling
    if processed_in_chunk >= CHUNK_SIZE:
        time.sleep(CHUNK_SLEEP_SECONDS)
        processed_in_chunk = 0

# Final summary
print(f"\n✅ Page creation complete: {actual_processed}/{total} pages processed.")
write_debug_log(f"--- Completed: {actual_processed}/{total} pages processed ---", debug_log_path)
