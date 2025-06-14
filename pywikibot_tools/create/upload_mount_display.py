import os
import re
import sys
import time
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
import pywikibot
import mwparserfromhell
from utils import image_utils
from utils.wiki_utils import fetch_pages, parse_template_params
from utils.file_utils import write_debug_log

# Paths
image_input_directory = os.path.join(constants.IMAGE_INPUT_DIRECTORY)
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "pywikibot_mount_display.txt")
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)
if os.path.exists(debug_log_path):
    with open(debug_log_path, 'a', encoding='utf-8') as f:
        f.write("\n\n------------------- " + time.strftime("%Y-%m-%d %H:%M:%S") + " -------------------\n")

CATEGORY_NAME = "Mount image needed"
json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")

used_images = set()

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def update_gallery_section(wikitext, front_name, side_name):
    new_gallery = (
        "==Mount Display==\n"
        "<gallery widths=\"150\" bordercolor=\"transparent\" spacing=\"small\" captionalign=\"center\">\n"
        f"{front_name}|Front\n"
        f"{side_name}|Side\n"
        "</gallery>\n"
        "\n"
    )
    parsed = mwparserfromhell.parse(wikitext)
    found = False
    for section in parsed.get_sections(matches="Mount Display", include_lead=False, include_headings=True):
        wikitext = str(parsed).replace(str(section), new_gallery)
        found = True
        break
    if not found:
        wikitext += "\n\n" + new_gallery
    return wikitext

def find_image_pair(base, back_suffixes, front_suffixes):
    normalized_base = normalize_name(base)
    files = os.listdir(image_input_directory)
    for back_suffix in back_suffixes:
        for front_suffix in front_suffixes:
            write_debug_log(f"Searching for: *{normalized_base}*{back_suffix} and *{normalized_base}*{front_suffix}", debug_log_path)
            matches1 = [f for f in files if f.lower().endswith(back_suffix.lower()) and normalize_name(f).find(normalized_base) != -1 and f not in used_images]
            matches2 = [f for f in files if f.lower().endswith(front_suffix.lower()) and normalize_name(f).find(normalized_base) != -1 and f not in used_images]
            if matches1 and matches2:
                used_images.update([matches1[0], matches2[0]])
                return os.path.join(image_input_directory, matches1[0]), os.path.join(image_input_directory, matches2[0])
    return None, None

def get_best_image_pair(name, asset_name, is_front):
    base_candidates = [
        name.replace(" Whistle", "").strip(),
        asset_name.replace(" Whistle", "").strip()
    ]
    third_candidate = base_candidates[0].replace(" Mount", "").strip()
    if third_candidate not in base_candidates:
        base_candidates.append(third_candidate)

    back_suffixes = ["_back_1.png", "_Back_1.png", "_bot_1.png", "_back_20.png", "_Back_20.png", "_bot_20.png"]
    front_suffixes = ["_front_1.png", "_Front_1.png", "_top_1.png", "_front_20.png", "_Front_20.png", "_top_20.png"]

    if is_front:
        back_suffixes += ["_South_Idle_layer_1_0.png"]
        front_suffixes += ["_South_Idle_layer_2_0.png"]
    else:
        back_suffixes += ["_East_Idle_layer_1_0.png"]
        front_suffixes += ["_East_Idle_layer_2_0.png"]

    for base in base_candidates:
        back, front = find_image_pair(base, back_suffixes, front_suffixes)
        if back and front:
            return back, front, base
    return None, None, base_candidates[0]

def process_page(title, text, item_data):
    uploaded_images = 0

    wiki_params = parse_template_params(text, "Item infobox")
    is_dlc = wiki_params.get("dlc", "").strip().lower() == "true"

    item_info = item_data.get(title, {})
    name = item_info.get("Name", title)
    asset_name = item_info.get("assetName", title)

    front_back, front_front, _ = get_best_image_pair(name, asset_name, is_front=True)
    side_back, side_front, _ = get_best_image_pair(name, asset_name, is_front=False)

    display_base = title.replace(" Whistle", "").strip()
    front_out = f"{display_base}_Front.png"
    side_out = f"{display_base}.png"
    caption = f"[[{title}|{display_base}]]"

    for label, back, front, output, extra_cats in [
        ("Front", front_back, front_front, front_out, ["Mount images"]),
        ("Side", side_back, side_front, side_out, ["Mount images"] + (["DLC mount images"] if is_dlc else []))
    ]:
        if not back or not front:
            write_debug_log(f"Missing {label} image for {display_base}: {back if not back else front}", debug_log_path)
            continue

        try:
            img = image_utils.composite_images(back, front)
            img = image_utils.crop_whitespace(img)
            img = image_utils.scale_image_to_min_size(img, 500)
            write_debug_log(f"Uploading cropped, upscaled version of image: {output}", debug_log_path)
            image_utils.upload_image(
                img,
                output,
                caption_text=caption,
                categories=extra_cats,
                debug_path=debug_log_path,
                upload_comment=f"Mount display image upload."
            )
            write_debug_log(f"Uploaded: {output}", debug_log_path)
            uploaded_images += 1
        except Exception as e:
            write_debug_log(f"Failed to process {label} image for {display_base}: {e}", debug_log_path)

    if uploaded_images < 2:
        write_debug_log(f"Skipping save for {title}: only {uploaded_images} image(s) uploaded", debug_log_path)
        return None, None

    new_text = update_gallery_section(text, front_out, side_out)
    return title, new_text

def main():
    print("🔍 Checking missing mount images list...")
    site = pywikibot.Site()
    cat = pywikibot.Category(site, f"Category:{CATEGORY_NAME}")
    pages = list(cat.articles())
    titles = [p.title() for p in pages]

    with open(json_file_path, encoding="utf-8") as f:
        item_data = json.load(f)

    fetched = fetch_pages(titles)
    for title, text in fetched.items():
        print(f"🛠️ Beginning process on: {title}")
        updated_title, updated_text = process_page(title, text, item_data)
        if updated_title and updated_text and updated_text != text:
            page = pywikibot.Page(site, updated_title)
            page.text = updated_text
            try:
                print(f"✏️  Removing category on: {updated_title}")
                page.save(summary="Uploading mount images and updating display gallery.")
                print(f"✅ Process complete, updated page: {updated_title}")
            except Exception as e:
                write_debug_log(f"Failed to update page {updated_title}: {e}", debug_log_path)

if __name__ == "__main__":
    main()
