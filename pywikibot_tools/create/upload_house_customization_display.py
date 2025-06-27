import os
import re
import sys
import time
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from utils import image_utils
from utils.wiki_utils import fetch_pages
from pywikibot import Category

# Paths
image_input_directory = os.path.join(constants.IMAGE_INPUT_DIRECTORY)
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "pywikibot_house_display.txt")
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)
if os.path.exists(debug_log_path):
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write("\n\n------------------- " + time.strftime("%Y-%m-%d %H:%M:%S") + " -------------------\n")

HOUSE_TYPES = {
    "Door": 3,
    "Window": 3,
    "Wall": 3,
    "Roof": 3,
    "Patio": 1
}

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def extract_style_and_type(pagename):
    pagename_lc = pagename.lower().strip()
    for type_uc in HOUSE_TYPES:
        type_lc = type_uc.lower()
        if pagename_lc.endswith(type_lc + "s"):
            return pagename[:-len(type_lc + "s")].strip(), type_uc
        elif pagename_lc.endswith(type_lc):
            return pagename[:-len(type_lc)].strip(), type_uc
    return None, None

def find_image_file(style, type_lc, index):
    candidates = []
    plural_map = {
        "wall": "walls",
        "window": "windows",
    }
    type_variants = [type_lc]
    if type_lc in plural_map:
        type_variants.append(plural_map[type_lc])

    for variant in type_variants:
        if type_lc == "patio" and index == 0:
            candidates.append(f"{style}_patio.png")
            candidates.append(f"{style}_house_patio.png")
        else:
            candidates.append(f"{style}_{variant}_{index}.png")
            candidates.append(f"{style}_{variant}_tier_{index + 1}.png")

    files = os.listdir(image_input_directory)
    for candidate in candidates:
        for file in files:
            if normalize_name(file) == normalize_name(candidate):
                return os.path.join(image_input_directory, file), file
    return None, None

def build_upload_name(style, type_uc, index):
    if type_uc == "Patio":
        return f"{style} Patio1.png"
    return f"{style} {type_uc}{index + 1}.png"

def process_page(page, title):
    style, type_uc = extract_style_and_type(title)
    if not style or not type_uc:
        image_utils.log_debug(f"Unrecognized format: {title}", debug_log_path)
        return False

    expected_count = HOUSE_TYPES[type_uc]
    type_lc = type_uc.lower()
    uploaded_or_skipped = 0

    site = pywikibot.Site()

    for i in range(expected_count):
        filepath, source_file = find_image_file(style, type_lc, i)
        if not filepath:
            image_utils.log_debug(f"Image not found for: {title} (index {i})", debug_log_path)
            continue

        upload_name = build_upload_name(style, type_uc, i)
        file_page = pywikibot.FilePage(site, upload_name)
        if file_page.exists():
            image_utils.log_debug(f"Skipped upload for {upload_name} (already exists on wiki)", debug_log_path)
            uploaded_or_skipped += 1
            continue

        caption = f"[[{title}]]"
        try:
            img = image_utils.crop_whitespace(image_utils.Image.open(filepath))
            img = image_utils.scale_image_to_min_size(img, 500)
            image_utils.upload_image(
                img,
                upload_name,
                caption_text=caption,
                categories=[f"Custom {type_lc} images"],
                debug_path=debug_log_path,
                upload_comment=f"House {type_lc} image upload"
            )
            uploaded_or_skipped += 1
        except Exception as e:
            image_utils.log_debug(f"Failed uploading {upload_name}: {e}", debug_log_path)

    if uploaded_or_skipped == expected_count:
        try:
            text = page.text
            if "[[Category:House images needed]]" in text:
                new_text = text.replace("[[Category:House images needed]]", "").strip()
                page.text = new_text
                page.save(summary="Remove House images needed category (images uploaded)")
            return True
        except Exception as e:
            image_utils.log_debug(f"Failed to remove category for {title}: {e}", debug_log_path)
            return False

    return False

def main():
    site = pywikibot.Site()
    cat = Category(site, "Category:House images needed")
    titles = [page.title() for page in cat.articles()]
    pages = fetch_pages(titles)

    total = len(pages)
    number_processed = 0
    actual_pages_resolved = 0

    print(f"🔍 Processing category: House images needed")

    for idx, (title, page) in enumerate(pages.items(), 1):
        if process_page(page, title):
            actual_pages_resolved += 1
        number_processed += 1

        if idx % max(total // 10, 1) == 0:
            percent = (number_processed / total) * 100
            print(f"      🔄 {number_processed}/{total} processed pages — ({percent:.1f}%).")

    print(f"✅ House display uploads complete: {actual_pages_resolved}/{total} pages resolved.")

if __name__ == "__main__":
    main()
