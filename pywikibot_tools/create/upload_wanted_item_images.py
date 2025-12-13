"""
Uses Special:WantedFiles to find missing file pages on the wiki, then:
- Attempts to map each wanted file back to an item in items_data.json
- Uses that item's iconGUID and images_data.json to find the correct source texture
- Falls back to icon_<ItemName>.png if needed
- Scales the texture up and uploads it as the wanted file
"""

import os
import sys
import time
import json
import traceback
from datetime import datetime

import pywikibot
from PIL import Image

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.stdout.reconfigure(encoding="utf-8")

from config import constants
from config.skip_items import SKIP_ITEMS, SKIP_IMAGES
from utils.text_utils import normalize_apostrophe

sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
site = pywikibot.Site()
pywikibot.config.verbose_output = False
pywikibot.config.log = []
pywikibot.config.noisy_output = False

# Paths
json_data_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot")

items_data_file = os.path.join(json_data_directory, "items_data.json")
images_data_file = os.path.join(json_data_directory, "images_data.json")

debug_log_path = os.path.join(
    constants.DEBUG_DIRECTORY,
    "pywikibot",
    "pywikibot_wantedFiles_imageUploader_debug.txt",
)

# Source textures directory
image_input_directory = constants.IMAGE_INPUT_DIRECTORY

# Settings
TARGET_SCALE = 5
SUMMARY_TEXT = "Uploading upscaled version of image"
UPLOAD_TEMPLATE = "{{License|game}}"

CHUNK_SIZE = 25
CHUNK_SLEEP_SECONDS = 10


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)


def log_debug(message):
    ensure_directory(os.path.dirname(debug_log_path))
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\n")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def chunk_list(lst, chunk_size):
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


def scale_image(image_path, scale):
    with Image.open(image_path) as img:
        new_size = (img.width * scale, img.height * scale)
        return img.resize(new_size, Image.NEAREST)


def upload_image(image, upload_name):
    ensure_directory(output_directory)
    temp_path = os.path.join(output_directory, upload_name)
    image.save(temp_path)

    page = pywikibot.FilePage(site, "File:" + upload_name)
    uploaded = False

    try:
        if page.exists():
            log_debug(f"Skipped upload for {upload_name} (already exists on wiki)")
        else:
            page.text = UPLOAD_TEMPLATE
            page.upload(temp_path, comment=SUMMARY_TEXT, ignore_warnings=False)
            log_debug(f"Uploaded: {upload_name}")
            uploaded = True
    except Exception as e:
        log_debug(f"Upload failed for {upload_name}: {e}")
        log_debug(traceback.format_exc())
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return uploaded


def build_normalized_item_index(items_data):
    index = {}
    for name in items_data.keys():
        norm = normalize_apostrophe(name).lower()
        if norm in index and index[norm] != name:
            log_debug(
                f"Normalized name collision: {norm!r} maps to both "
                f"{index[norm]!r} and {name!r}. Keeping the first."
            )
            continue
        index[norm] = name
    return index


def normalize_wanted_title_to_item_name(file_title):
    title = file_title

    if ":" in title:
        _, title = title.split(":", 1)

    title = title.strip()

    if "." in title:
        title = title.rsplit(".", 1)[0]

    return title.strip()


def get_wanted_files():
    wanted_titles = []

    log_debug("Fetching Special:WantedFiles from wiki...")

    try:
        if hasattr(site, "wantedfiles"):
            for page in site.wantedfiles():
                wanted_titles.append(page.title(with_ns=False))
        else:
            for page in site.querypage("Wantedfiles"):
                wanted_titles.append(page.title(with_ns=False))
    except Exception as e:
        log_debug(f"Error while fetching Special:WantedFiles: {e}")
        log_debug(traceback.format_exc())
        raise

    log_debug(f"Fetched {len(wanted_titles)} wanted files from wiki.")
    return wanted_titles


def build_texture_candidates(texture_filename, base_name):
    candidates = []

    if texture_filename:
        candidates.append(texture_filename)

        root, ext = os.path.splitext(texture_filename)
        if root.endswith("_0"):
            candidates.append(root[:-2] + ext)

    base_variants = set()
    base_variants.add(base_name)
    base_variants.add(base_name.replace(" ", "_"))

    for base in list(base_variants):
        base_variants.add(f"icon_{base}")

    for base in base_variants:
        if not os.path.splitext(base)[1]:
            candidates.append(base + ".png")
        else:
            candidates.append(base)

    expanded = []
    seen = set()

    for c in candidates:
        if " " in c:
            expanded.append(c.replace(" ", "_"))
        expanded.append(c)

    result = []
    for c in expanded:
        if c not in seen:
            result.append(c)
            seen.add(c)

    return result


def find_existing_texture_file(texture_filename, base_name):
    candidates = build_texture_candidates(texture_filename, base_name)
    tried_paths = []

    for name in candidates:
        candidate_path = os.path.join(image_input_directory, name)
        tried_paths.append(candidate_path)
        if os.path.exists(candidate_path):
            log_debug(
                f"Resolved texture for {base_name!r}: using existing file {candidate_path!r}"
            )
            return candidate_path

    fallback_name = f"icon_{base_name}.png"
    fallback_path = os.path.join(image_input_directory, fallback_name)
    tried_paths.append(fallback_path)

    if os.path.exists(fallback_path):
        log_debug(
            f"Resolved texture for {base_name!r} via hard fallback: {fallback_path!r}"
        )
        return fallback_path

    log_debug(
        f"No existing texture file found for {base_name!r}. "
        f"Tried paths: {', '.join(repr(p) for p in tried_paths)}"
    )
    return None


def process_wanted_file(file_title, items_data, images_data, item_index):
    base_name = normalize_wanted_title_to_item_name(file_title)
    norm_base = normalize_apostrophe(base_name).lower()

    item_key = item_index.get(norm_base)
    if not item_key:
        log_debug(f"{file_title} -> No matching item in items_data.json (normalized={norm_base!r})")
        return False

    if item_key.lower() in SKIP_ITEMS:
        log_debug(f"{file_title} -> Skipping item in SKIP_ITEMS: {item_key}")
        return False

    item = items_data.get(item_key)
    if not item:
        log_debug(f"{file_title} -> Item key {item_key!r} not found in items_data.json")
        return False

    icon_guid = item.get("iconGUID")
    if not icon_guid:
        log_debug(f"{file_title} -> Item {item_key!r} has no iconGUID")
        return False

    image_info = images_data.get(icon_guid)
    if not image_info:
        log_debug(
            f"{file_title} -> No images_data entry for iconGUID {icon_guid!r} "
            f"(item {item_key!r})"
        )
        return False

    texture_filename = image_info.get("image")
    if not texture_filename:
        log_debug(
            f"{file_title} -> images_data entry for {icon_guid!r} has no 'image' filename "
            f"(item {item_key!r})"
        )
        return False

    if texture_filename in SKIP_IMAGES:
        log_debug(
            f"{file_title} -> Skipping texture in SKIP_IMAGES: {texture_filename} "
            f"(item {item_key!r})"
        )
        return False

    source_path = find_existing_texture_file(texture_filename, base_name)
    if not source_path:
        return False

    upload_name = f"{base_name}.png"

    try:
        log_debug(
            f"{file_title} -> Uploading '{upload_name}' from '{source_path}' "
            f"(item={item_key!r}, GUID={icon_guid!r})"
        )
        scaled_image = scale_image(source_path, TARGET_SCALE)
        uploaded = upload_image(scaled_image, upload_name)
        return uploaded
    except Exception as e:
        log_debug(
            f"{file_title} -> Error while scaling/uploading from {source_path!r}: {e}"
        )
        log_debug(traceback.format_exc())
        return False


def main():
    ensure_directory(output_directory)
    ensure_directory(os.path.dirname(debug_log_path))

    items_data = load_json(items_data_file)
    images_data = load_json(images_data_file)

    if not items_data or not images_data:
        log_debug("Missing items_data.json or images_data.json; aborting.")
        return

    item_index = build_normalized_item_index(items_data)
    wanted_files = get_wanted_files()

    total = len(wanted_files)
    processed = 0
    uploaded_count = 0

    for chunk in chunk_list(wanted_files, CHUNK_SIZE):
        for file_title in chunk:
            processed += 1
            if process_wanted_file(
                file_title=file_title,
                items_data=items_data,
                images_data=images_data,
                item_index=item_index,
            ):
                uploaded_count += 1

        time.sleep(CHUNK_SLEEP_SECONDS)

    log_debug(
        f"Finished Special:WantedFiles. Total: {total}, Uploaded: {uploaded_count}"
    )


if __name__ == "__main__":
    main()
