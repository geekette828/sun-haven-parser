'''
This python script compares the items.json file to the wiki for missing item images.
For items missing their image in the wiki, it will map the file name of the item to that item in the output.
'''

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import config.constants as constants
import pywikibot
import json
import time

# Set up necessary configurations before other imports
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
site = pywikibot.Site()

# Paths
json_data_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot")

items_data_file = os.path.join(json_data_directory, "items_data.json")
images_data_file = os.path.join(json_data_directory, "images_data.json")
missing_names_txt = os.path.join(output_directory, "MissingImages_nonexistentImages.txt")
missing_files_txt = os.path.join(output_directory, "MissingImages_filenameConversion.txt")

debug_log_path = os.path.join(constants.OUTPUT_DIRECTORY, "Debug", "pywikibot_missingImageCheck_skipped.txt")

# Constants
CHUNK_SIZE = 750
CHUNK_SLEEP_SECONDS = 3

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def chunk_list(lst, chunk_size):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

# Check for missing images and map to file names, separating skipped cases into debug log.
def step1_combined_check_and_map():
    print("🔍 Checking JSON names for images...")
    ensure_dir(missing_files_txt)

    debug_log_path = os.path.join(constants.OUTPUT_DIRECTORY, "Debug", "pywikibot_missingImageCheck_skipped.txt")
    ensure_dir(debug_log_path)

    # Load data
    items_data = load_json(items_data_file)
    images_data = load_json(images_data_file)

    item_names = list(items_data.keys())
    total = len(item_names)

    if total == 0:
        print("⚠️ No items found in items_data.json!")
        return

    all_missing_items = []

    print(f"🔄 Preloading {total} pages in chunks of {CHUNK_SIZE}...")

    for i, chunk in enumerate(chunk_list(item_names, CHUNK_SIZE), start=1):
        file_pages = [pywikibot.FilePage(site, f"{name}.png") for name in chunk]
        preloaded_pages = list(site.preloadpages(file_pages))

        for page in preloaded_pages:
            if not page.exists():
                name = page.title(with_ns=False).rsplit(".", 1)[0]
                all_missing_items.append(name)

        processed = i * CHUNK_SIZE
        percent = min(int((processed / total) * 100), 100)
        actual_processed = min(processed, total)
        print(f"  ✅ {actual_processed}/{total} items complete — ({percent}%). Sleeping {CHUNK_SLEEP_SECONDS}s...")
        time.sleep(CHUNK_SLEEP_SECONDS)

    missing_items = all_missing_items

    print(f"✅ Found {len(missing_items)} missing items out of {total} total.")

    if not missing_items:
        print("🎉 No missing images found. Nothing to map.")
        return

    print("🔗 Mapping missing images to their filenames...")

    with open(missing_files_txt, "w", encoding="utf-8") as f, \
         open(debug_log_path, "w", encoding="utf-8") as debug:
        
        for name in missing_items:
            # Skip some items first
            lower_name = name.lower()
            if (
                any(char.isdigit() for char in name) or
                "(" in name or
                ")" in name or
                "stone node" in lower_name or
                "bundle" in lower_name or
                "octavius" in lower_name
            ):
                debug.write(f"{name} -> Skipped (naming rule)\n")
                continue

            item = items_data.get(name)
            if not item:
                debug.write(f"{name} -> Item not found in items_data.json\n")
                continue

            icon_guid = item.get("iconGUID")
            if not icon_guid:
                debug.write(f"{name} -> No iconGUID found\n")
                continue

            image_info = images_data.get(icon_guid)
            if not image_info:
                debug.write(f"{name} -> No image mapping for GUID {icon_guid}\n")
                continue

            filename = image_info.get("image") or "No filename in image mapping"
            f.write(f"{name} -> {filename}\n")

    print(f"📝 Missing image mapping written to: {missing_files_txt}")
    print(f"🛠️  Skipped items written to: {debug_log_path}")

# Entry point
if __name__ == "__main__":
    step1_combined_check_and_map()