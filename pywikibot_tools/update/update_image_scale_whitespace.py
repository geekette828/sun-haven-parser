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
    new_l = shrink(l)
    new_t = shrink(t)
    new_r = shrink(r)
    new_b = shrink(b)

    return img.crop((new_l, new_t, w - new_r, h - new_b))

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

def process_file(file_page):
    log_debug(f"🔍 Checking {file_page.title()}")
    img = download_image(file_page)
    if not img:
        return

    original_size = img.size
    summary_parts = []

    if original_size[0] < MIN_DIM and original_size[1] < MIN_DIM:
        img = scale_image(img)
        summary_parts.append(f"scaled from {original_size[0]}x{original_size[1]}")

    bounds = get_transparent_bounds(img)
    if any(p > MAX_PAD for p in bounds):
        img = trim_whitespace(img, bounds)
        summary_parts.append(f"trimmed transparent padding {bounds} to {TARGET_PAD}px")

    if not summary_parts:
        log_debug(f"✅ {file_page.title()} OK (size: {img.size}, padding: {bounds})")
        return

    upload_overwrite(file_page, img, "; ".join(summary_parts))

def main():
    category = "Sun Haven assets"
    cat = pywikibot.Category(site, f"Category:{category}")
    pages = list(cat.articles(namespaces="File"))
    log_debug(f"🗂️ Found {len(pages)} files in '{category}'")

    for i, file_page in enumerate(pages, 1):
        log_debug(f"\n--- [{i}/{len(pages)}] {file_page.title()} ---")
        process_file(file_page)
        time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    main()
