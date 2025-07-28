import os
import re
import sys
import time
import pywikibot
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from utils import file_utils, wiki_utils
from PIL import Image
from io import BytesIO

# Config
site = wiki_utils.get_site()

# Paths
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "image_trim_scale_upload_debug.txt")
temp_dir = os.path.join(constants.IMAGE_INPUT_DIRECTORY, "temp")
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))
file_utils.ensure_dir_exists(temp_dir)

# Constants
MIN_DIM = 300
MAX_PAD = 10
TARGET_PAD = 3
SLEEP_INTERVAL = constants.PWB_SETTINGS["SLEEP_INTERVAL"]
CATEGORY_NAME = "Sun Haven assets"
START_AT_LETTER = "M"  # Leave as 'None' to disable filtering

def log_debug(msg):
    file_utils.append_line(debug_log_path, msg)

def download_image(page):
    try:
        url = page.get_file_url()
        r = requests.get(url, headers={'User-Agent': 'image-fixer/1.0'})
        return Image.open(BytesIO(r.content)) if r.status_code == 200 else None
    except Exception as e:
        log_debug(f"❌ Failed to download {page.title()}: {e}")
        return None

def get_transparent_bounds(img):
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    w, h = img.size
    px = img.load()

    def is_col_transparent(x): return all(px[x, y][3] == 0 for y in range(h))
    def is_row_transparent(y): return all(px[x, y][3] == 0 for x in range(w))

    left = 0
    while left < w and is_col_transparent(left): left += 1
    right = w - 1
    while right >= 0 and is_col_transparent(right): right -= 1

    top = 0
    while top < h and is_row_transparent(top): top += 1
    bottom = h - 1
    while bottom >= 0 and is_row_transparent(bottom): bottom -= 1

    return left, top, w - 1 - right, h - 1 - bottom

def trim_whitespace(img, bounds):
    l, t, r, b = bounds
    w, h = img.size

    def shrink(val): return val - (MAX_PAD - TARGET_PAD) if val > MAX_PAD else 0

    new_l = min(max(0, shrink(l)), w - 1)
    new_t = min(max(0, shrink(t)), h - 1)
    new_r = min(max(0, shrink(r)), w - 1)
    new_b = min(max(0, shrink(b)), h - 1)

    # Calculate crop box
    crop_left = new_l
    crop_top = new_t
    crop_right = max(crop_left + 1, w - new_r)  # ensure right > left
    crop_bottom = max(crop_top + 1, h - new_b)  # ensure bottom > top

    return img.crop((crop_left, crop_top, crop_right, crop_bottom))

def scale_image(img):
    w, h = img.size
    if w >= MIN_DIM or h >= MIN_DIM:
        return img
    scale = MIN_DIM / min(w, h)
    new_size = (round(w * scale), round(h * scale))
    return img.resize(new_size, Image.NEAREST)

def save_temp_image(img, filename):
    temp_path = os.path.join(temp_dir, filename.replace("File:", "").replace(" ", "_"))
    img.save(temp_path)
    return temp_path

def upload_overwrite(file_page, img, summary):
    temp_path = save_temp_image(img, file_page.title())
    try:
        file_page.upload(temp_path, comment=summary, ignore_warnings=True)
        log_debug(f"📝 Overwrote {file_page.title()} - {summary}")
    except Exception as e:
        log_debug(f"❌ Upload failed for {file_page.title()}: {e}")
    finally:
        try:
            os.remove(temp_path)
            log_debug(f"🗑️ Deleted temp file: {temp_path}")
        except Exception as e:
            log_debug(f"⚠️ Failed to delete temp file {temp_path}: {e}")

API_METADATA_SLEEP = 0.5  # seconds between file info queries

def process_file(file_page):
    title = file_page.title(with_ns=False)
    if title.lower().endswith('.gif'):
        log_debug(f"⏩ Skipped GIF file: {title}")
        return

    if not file_page.exists():
        log_debug(f"❌ File missing: {title}")
        return

    # Throttle API metadata calls
    time.sleep(API_METADATA_SLEEP)
    info = file_page.latest_file_info
    if not info or not info.mime or 'image' not in info.mime:
        log_debug(f"⏩ Skipped non-image or unknown type: {title}")
        return

    width = info.width
    height = info.height

    if width >= MIN_DIM or height >= MIN_DIM:
        log_debug(f"✅ {title} already ≥{MIN_DIM}px (W:{width} H:{height}) — skipping download")
        return

    log_debug(f"🔍 Downloading {title} for deeper inspection")
    img = download_image(file_page)
    if not img:
        return

    w, h = img.size
    summary_parts = []

    if w < MIN_DIM and h < MIN_DIM:
        img = scale_image(img)
        summary_parts.append(f"scaled from {w}x{h}")
        w, h = img.size  # update after scaling

    bounds = get_transparent_bounds(img)
    if any(p > MAX_PAD for p in bounds):
        l, t, r, b = bounds
        def shrink(val): return val - (MAX_PAD - TARGET_PAD) if val > MAX_PAD else 0
        new_l = min(max(0, shrink(l)), w - 1)
        new_t = min(max(0, shrink(t)), h - 1)
        new_r = min(max(0, shrink(r)), w - 1)
        new_b = min(max(0, shrink(b)), h - 1)
        crop_left = new_l
        crop_top = new_t
        crop_right = max(crop_left + 1, w - new_r)
        crop_bottom = max(crop_top + 1, h - new_b)
        img = img.crop((crop_left, crop_top, crop_right, crop_bottom))
        summary_parts.append(f"trimmed transparent padding {bounds} to {TARGET_PAD}px")

    if summary_parts:
        upload_overwrite(file_page, img, "; ".join(summary_parts))
    else:
        log_debug(f"✅ {title} passed all checks after full inspection")

def main():
    cat = pywikibot.Category(site, f"Category:{CATEGORY_NAME}")
    pages = list(cat.articles(namespaces="File"))
    log_debug(f"🗂️ Found {len(pages)} files in '{CATEGORY_NAME}'")

    filtered_pages = []

    for page in pages:
        title = page.title(with_ns=False)
        if START_AT_LETTER:
            first_char = title.lstrip().upper()[:1]
            if first_char < START_AT_LETTER.upper():
                continue
        filtered_pages.append(page)

    log_debug(f"▶️ Starting from letter '{START_AT_LETTER}' — {len(filtered_pages)} files remaining")

    for i, file_page in enumerate(filtered_pages, 1):
        log_debug(f"\n--- [{i}/{len(filtered_pages)}] {file_page.title()} ---")
        process_file(file_page)

        if i % 250 == 0:
            log_debug(f"🔄 Progress: {i}/{len(filtered_pages)} images processed")

        time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    main()
