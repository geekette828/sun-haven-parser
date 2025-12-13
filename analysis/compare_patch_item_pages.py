'''
This script compares the Item_Comparison_JSONOnly.txt from the current patch
To the Item_Comparison_JSONOnly.txt from the previous patch (set in constants)
And produces a list of new items pages that need to be created in the wiki
'''

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from datetime import datetime
from utils.text_utils import clean_whitespace
from utils.json_utils import load_json

# Define paths
OLD_FILE_PATH = os.path.join(constants.PREVIOUS_OUTPUT_DIRECTORY, "Pywikibot", "Item_Comparison_JSONOnly.txt")
NEW_FILE_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Item_Comparison_JSONOnly.txt")

OUTPUT_FILENAME = "Unique_Items_For_Patch.txt"
OUTPUT_FILE_PATH = os.path.join(constants.OUTPUT_DIRECTORY, OUTPUT_FILENAME)

english_prefab_path = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")

DEBUG_LOG_PATH = os.path.join(
    constants.DEBUG_DIRECTORY,
    "analysis",
    "patch_item_comparison.log"
)
os.makedirs(os.path.dirname(DEBUG_LOG_PATH), exist_ok=True)

# LOGGING
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# NORMALIZATION
def normalize_name(name):
    return clean_whitespace(str(name)).lower()

# LOADERS (JSON OR TXT)
def load_items_from_file(path):
    if not os.path.exists(path):
        log(f"ERROR: File not found -> {path}")
        return set()

    # JSON HANDLING
    if path.lower().endswith(".json"):
        data = load_json(path)

        if isinstance(data, dict):
            return {
                normalize_name(v.get("Name", k))
                for k, v in data.items()
                if v
            }

        if isinstance(data, list):
            return {
                normalize_name(item.get("Name", item))
                for item in data
            }

    # TXT FALLBACK
    with open(path, "r", encoding="utf-8") as f:
        return {
            normalize_name(line)
            for line in f
            if line.strip()
        }

# MAIN
def main():
    log("🔍 Loading patch files...")

    old_items = load_items_from_file(OLD_FILE_PATH)
    new_items = load_items_from_file(NEW_FILE_PATH)

    log(f"Old patch items loaded: {len(old_items)}")
    log(f"New patch items loaded: {len(new_items)}")

    # Only keep truly NEW items
    unique_new_items = sorted(new_items - old_items)

    log(f"✅ Unique new items found: {len(unique_new_items)}")

    with open(OUTPUT_FILE_PATH, "w", encoding="utf-8") as f:
        for item in unique_new_items:
            f.write(item + "\n")

    log(f"✅ Output written to: {OUTPUT_FILE_PATH}")

# EXECUTION
if __name__ == "__main__":
    main()
