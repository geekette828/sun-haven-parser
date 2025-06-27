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
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "pywikibot_floor_wallpaper_display.txt")
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)
if os.path.exists(debug_log_path):
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write("\n\n------------------- " + time.strftime("%Y-%m-%d %H:%M:%S") + " -------------------\n")

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def find_image_file(pagename, is_flooring):
    files = os.listdir(image_input_directory)

    # Flooring uses only "_NV_Top.png"
    if is_flooring:
        candidate = f"{pagename}_NV_Top.png"
    else:
        # Wallpaper fallback
        candidate = f"{pagename}_0.png"

    for file in files:
        if normalize_name(file) == normalize_name(candidate):
            return os.path.join(image_input_directory, file), file
    return None, None

def process_page(title, is_flooring):
    output_filename = f"{title} display.png"
    caption = f"[[{title}]]"
    category = "Flooring display images" if is_flooring else "Wallpaper display images"

    filepath, source_file = find_image_file(title, is_flooring)
    if not filepath:
        image_utils.log_debug(f"Image not found for: {title}", debug_log_path)
        return False

    image_utils.log_debug(f"Using file for {title}: {source_file}", debug_log_path)

    try:
        img = image_utils.crop_whitespace(image_utils.Image.open(filepath))

        if is_flooring:
            # Scale flooring to exactly 1080x780 (approx 500% if original is 216x156)
            img = img.resize((1080, 780), resample=image_utils.Image.NEAREST)
        else:
            # Default scale to at least 500px on one side
            img = image_utils.scale_image_to_min_size(img, 500)

        image_utils.upload_image(
            img,
            output_filename,
            caption_text=caption,
            categories=[category],
            debug_path=debug_log_path,
            upload_comment=f"{category.split()[0]} display image upload"
        )
        return True
    except Exception as e:
        image_utils.log_debug(f"Failed processing {title}: {e}", debug_log_path)
        return False

def main():
    site = pywikibot.Site()

    for catname, is_flooring in [("Flooring", True), ("Wallpaper", False)]:
        print(f"🔍 Processing category: {catname}")
        cat = Category(site, f"Category:{catname}")
        titles = [page.title() for page in cat.articles()]
        pages = fetch_pages(titles)

        total = len(pages)
        number_processed = 0
        actual_new_uploads = 0

        for idx, (title, _) in enumerate(pages.items(), 1):
            if process_page(title, is_flooring):
                actual_new_uploads += 1
            number_processed += 1

            if idx % max(total // 10, 1) == 0:
                percent = (number_processed / total) * 100
                print(f"      🔄 {number_processed}/{total} processed images — ({percent:.1f}%).")

        print(f"✅ Display images uploads complete: {actual_new_uploads}/{total} pages processed.")

if __name__ == "__main__":
    main()
