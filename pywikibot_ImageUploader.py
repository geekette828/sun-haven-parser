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
missing_names_txt = os.path.join(output_directory, "images that dont exist.txt")
missing_files_txt = os.path.join(output_directory, "missing images with filenames.txt")

# Rate limiting (in seconds)
RATE_LIMIT_SECONDS = 1.0

def format_time(seconds):
    """Format seconds as MM:SS."""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

# Check for missing images and map to file names using preload and single output.
def step1_combined_check_and_map():
    print("Checking JSON names for images...")
    ensure_dir(missing_files_txt)

    items_data = load_json(items_data_file)
    images_data = load_json(images_data_file)

    item_names = list(items_data.keys())
    total = len(item_names)
    progress_checkpoints = {int(total * i / 20) for i in range(1, 21)}  # Every 5%
    start_time = time.time()

    # Build and preload all pages in a single batch
    file_pages = [pywikibot.FilePage(site, f"{name}.png") for name in item_names]
    preloaded_pages = list(site.preloadpages(file_pages))

    # Collect missing items first
    missing_items = []
    for page in preloaded_pages:
        if not page.exists():
            name = page.title(with_ns=False).rsplit(".", 1)[0]
            missing_items.append(name)

    print("Gathering missing images complete.")
    print("Mapping missing images to their filename...")

    # Start the progress for mapping
    total_missing = len(missing_items)
    mapping_checkpoints = {int(total_missing * i / 20) for i in range(1, 21)}
    start_mapping_time = time.time()

    with open(missing_files_txt, "w", encoding="utf-8") as f:
        for index, name in enumerate(missing_items, start=1):
            item = items_data.get(name)
            if not item:
                f.write(f"{name}: Item not found in items_data.json\n")
                continue

            icon_guid = item.get("iconGUID")
            if not icon_guid:
                f.write(f"{name}: No iconGUID found\n")
                continue

            image_info = images_data.get(icon_guid)
            if not image_info:
                f.write(f"{name}: No image mapping for GUID {icon_guid}\n")
                continue

            filename = image_info.get("image") or "No filename in image mapping"
            f.write(f"{name}: {filename}\n")

            if index in mapping_checkpoints:
                percent = int((index / total_missing) * 100)
                elapsed = time.time() - start_mapping_time
                avg_time = elapsed / index
                eta = avg_time * (total_missing - index)
                print(f"...{percent}% complete — approx. {format_time(eta)} remaining")

    print(f"Missing image mapping written to: {missing_files_txt}")