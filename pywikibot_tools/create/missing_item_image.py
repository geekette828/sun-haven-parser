'''
This script will take the list executed from `validators/missing_item_images.py`
and attempt to upload the correct icon images to the wiki. 
Ensure image files are in the right place.
'''

import sys
import config.constants as constants
import os
import pywikibot
import traceback
import time
from datetime import datetime
from PIL import Image

# Set up pyWikiBot configurations
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
site = pywikibot.Site()
pywikibot.config.verbose_output = False
pywikibot.config.log = []
pywikibot.config.noisy_output = False

# Paths
input_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "imagesTEST.txt")
image_input_directory = os.path.join(constants.IMAGE_INPUT_DIRECTORY) #os.path.join(constants.INPUT_DIRECTORY, "Texture2D")
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot")
debug_log_path = os.path.join(constants.OUTPUT_DIRECTORY, "Debug", "pywikibot_imageUploader_debug.txt")
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)

missing_file_output_path = os.path.join(output_file_path, "MissingImages_missingTextureFile.txt")
missing_files = []

# Settings
target_scale = 4  # Scale image dimensions
summary_text = "Uploading upscaled version of image"
upload_template = "{{Games}}"  # Change if needed
CHUNK_SIZE = 5
CHUNK_SLEEP_SECONDS = 10

def log_debug(message):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\n")

def scale_image(image_path, scale):
    with Image.open(image_path) as img:
        new_size = (img.width * scale, img.height * scale)
        return img.resize(new_size, Image.NEAREST)
    
def chunk_list(lst, chunk_size):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def upload_image(image, upload_name):
    temp_path = os.path.join(output_file_path, upload_name)
    image.save(temp_path)

    page = pywikibot.FilePage(site, "File:" + upload_name)
    page.text = upload_template

    try:
        if page.exists():
            log_debug(f"Skipped upload for {upload_name} (already exists on wiki)")
        else:
            page.upload(temp_path, comment=summary_text, ignore_warnings=False)
            log_debug(f"Uploaded: {upload_name}")
    except Exception as e:
        log_debug(f"Upload failed for {upload_name}: {e}")
        log_debug(traceback.format_exc())
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def process_image_line(line):
    if '->' not in line:
        return

    item_name, file_name = [x.strip() for x in line.split('->', 1)]
    upload_name = item_name + ".png"
    image_path = os.path.join(image_input_directory, file_name)

    if not os.path.exists(image_path):
        log_debug(f"Missing file for upload: {file_name} (Expected path: {image_path})")
        missing_files.append(f"{item_name} -> {file_name}")
        return

    try:
        log_debug(f"Processing: {item_name}")
        scaled_image = scale_image(image_path, target_scale)
        upload_image(scaled_image, upload_name)
    except Exception as e:
        log_debug(f"Error with {item_name}: {e}")
        log_debug(traceback.format_exc())

def main():
    if not os.path.exists(input_file_path):
        print(f"Input file not found: {input_file_path}")
        log_debug(f"Input file missing: {input_file_path}")
        return

    with open(input_file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    total = len(lines)
    actual_processed = 0
    last_reported_percent = -1

    for i, chunk in enumerate(chunk_list(lines, CHUNK_SIZE), start=1):
        for line in chunk:
            process_image_line(line)
            actual_processed += 1

            percent = int((actual_processed / total) * 100)
            if percent >= last_reported_percent + 10:
                print(f"  ✅ {actual_processed}/{total} image uploads complete — ({percent}%). Sleeping {CHUNK_SLEEP_SECONDS}s...")
                last_reported_percent = percent

        time.sleep(CHUNK_SLEEP_SECONDS)

    # Optional: Final summary
    print(f"\n✅ Upload complete: {actual_processed}/{total} files processed.")

if __name__ == "__main__":
    main()
    if missing_files:
        with open(missing_file_output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(missing_files))
