'''
This python script checks for missing front and side mount images. 
Since the data has a top and bottom image of the mount
it will put both parts together, scale it, and upload it to the wiki.
'''

import os
import re
import time
from PIL import Image
import pywikibot
import config.constants as constants

# Pywikibot setup
import sys
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
pywikibot.config.throttle = constants.PWB_SETTINGS["throttle"]
pywikibot.config.max_retries = constants.PWB_SETTINGS["max_retries"]
pywikibot.config.retry_wait = constants.PWB_SETTINGS["retry_wait"]
pywikibot.config.user_agent = constants.PWB_SETTINGS["user_agent"]
site = pywikibot.Site()

# Paths
INPUT_FILE_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "pywikibot_updateMountImage.txt")
INPUT_IMAGE_PATH = r"N:\\Images\\Sprite"
DEBUG_LOG_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "Debug", "pywikibot_uploadMountImage_debug.txt")
os.makedirs(os.path.dirname(DEBUG_LOG_PATH), exist_ok=True)

# Settings
TARGET_SCALE = 4
UPLOAD_TEMPLATE = "{{Games}}"
CHUNK_SIZE = 5
CHUNK_SLEEP_SECONDS = 10

def log_debug(message):
    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def trim_transparency(im):
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    alpha = im.getchannel('A')
    bbox = alpha.getbbox()
    if bbox:
        return im.crop(bbox)
    return im

def combine_images_vertically(top_path, bottom_path):
    top = Image.open(top_path).convert("RGBA")
    bottom = Image.open(bottom_path).convert("RGBA")
    combined = Image.new("RGBA", (top.width, top.height + bottom.height))
    combined.paste(top, (0, 0))
    combined.paste(bottom, (0, top.height))
    return combined

def upscale_image(im, factor=4):
    return im.resize((im.width * factor, im.height * factor), resample=Image.NEAREST)

def process_image_pair(name):
    base_name = os.path.splitext(name)[0].replace(" Side", "")
    is_side = "Side" in name
    packname = base_name.split()[0]

    top_num = 2 if is_side else 1
    top_img = os.path.join(INPUT_IMAGE_PATH, f"{base_name}_mount_top_{top_num}.png")
    bottom_img = os.path.join(INPUT_IMAGE_PATH, f"{base_name}_mount_bottom_{top_num}.png")

    if not os.path.exists(top_img) or not os.path.exists(bottom_img):
        log_debug(f"Missing image files for {name}")
        return

    combined = combine_images_vertically(top_img, bottom_img)
    trimmed = trim_transparency(combined)
    upscaled = upscale_image(trimmed, factor=TARGET_SCALE)

    upload_name = name
    file_page = pywikibot.FilePage(site, f"File:{upload_name}")

    text = UPLOAD_TEMPLATE
    text += f"\n\n==Licensing==\n{UPLOAD_TEMPLATE}"

    if is_side:
        text += f"\n[[Category:Mount images]]"
        text += f"\n[[Category:DLC mount images]]"
    text += f"\n[[Category:{packname} pack images]]"

    file_page.text = text

    try:
        file_page.upload(
            source=upscaled,
            ignore_warnings=True,
            comment=f"Uploading upscaled version of image: {upload_name}",
        )
        file_page.save(summary="Added licensing and categories.")
        log_debug(f"✅ Uploaded {upload_name}")
    except Exception as e:
        log_debug(f"❌ Failed to upload {upload_name}: {e}")

def extract_missing_images():
    with open(INPUT_FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    section = re.search(r"### Missing Images ###(.*?)###", content, re.DOTALL)
    if not section:
        log_debug("Missing Images section not found.")
        return []
    lines = [line.strip() for line in section.group(1).strip().splitlines() if line.strip()]
    return [line.split(": ", 1)[1] for line in lines if ": " in line]

def chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

def upload_missing_mount_images():
    images = extract_missing_images()
    total = len(images)
    actual_processed = 0
    last_reported_percent = -1

    for i, chunk in enumerate(chunk_list(images, CHUNK_SIZE), start=1):
        for name in chunk:
            process_image_pair(name)
            actual_processed += 1
            percent = int((actual_processed / total) * 100)
            if percent >= last_reported_percent + 10:
                print(f"  ✅ {actual_processed}/{total} image uploads complete — ({percent}%). Sleeping {CHUNK_SLEEP_SECONDS}s...")
                last_reported_percent = percent
        time.sleep(CHUNK_SLEEP_SECONDS)

    print(f"\n✅ Upload complete: {actual_processed}/{total} files processed.")
