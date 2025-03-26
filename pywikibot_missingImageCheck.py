import sys
import config
import os
import json
import re
import time
import pywikibot
import datetime

# Set up necessary configurations before other imports
sys.path.append(config.ADDITIONAL_PATHS["PWB"])
site = pywikibot.Site()

# Paths
json_data_directory = os.path.join(config.OUTPUT_DIRECTORY, "JSON Data")
output_directory = os.path.join(config.OUTPUT_DIRECTORY, "Pywikibot")

items_data_file = os.path.join(json_data_directory, "items_data.json")
images_data_file = os.path.join(json_data_directory, "images_data.json")
missing_names_txt = os.path.join(output_directory, "MissingImages_nonexistentImages.txt")
missing_files_txt = os.path.join(output_directory, "MissingImages_filenameConversion.txt")

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

def step1_combined_check_and_map():
    print("🔍 Step 1: Checking JSON names for images...")
    ensure_dir(missing_files_txt)

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

    with open(missing_files_txt, "w", encoding="utf-8") as f:
        for name in missing_items:
            item = items_data.get(name)
            if not item:
                f.write(f"{name}: Item not found in items_data.json\n")
                continue

            icon_guid = item.get("iconGUID")
            if not icon_guid:
                f.write(f"{name} -> No iconGUID found\n")
                continue

            image_info = images_data.get(icon_guid)
            if not image_info:
                f.write(f"{name}: No image mapping for GUID {icon_guid}\n")
                continue

            filename = image_info.get("image") or "No filename in image mapping"
            f.write(f"{name} -> {filename}\n")

    print(f"📝 Missing image mapping written to: {missing_files_txt}")

# Entry point
if __name__ == "__main__":
    step1_combined_check_and_map()