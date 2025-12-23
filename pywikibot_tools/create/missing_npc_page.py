"""
Create missing NPC pages + upload associated NPC images.

- Reads NPC names from:
  OUTPUT_DIRECTORY/Wiki Formatted/npc_list.txt

- Skips if the NPC page already exists on the wiki.

- Builds NPC page text by calling into:
  formatter.page_assembly.create_npc_page (existing page builder logic)

- Attempts to find an associated image in constants.IMAGE_INPUT_DIRECTORY using patterns:
  icon_<NPCName>.png
  <NPCName>_idle_south_0.png
  <NPCName>_south_0.png
  <NPCName>_walk_south_0.png

- If found, upscales and uploads to File:<NPCName>.png (skips if already exists).
"""

import os
import sys
import time
import traceback
import pywikibot
from datetime import datetime
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from utils.file_utils import read_file_lines

# IMPORTANT: This is your existing NPC page builder script/module.
# It contains helpers like: to_title_case, read_text_file, extract_chat_templates,
# load_schedule_text, build_page_wikitext, etc.
from formatter.page_assembly import create_npc_page


# Set up pyWikiBot configurations
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
site = pywikibot.Site()
pywikibot.config.verbose_output = False
pywikibot.config.log = []
pywikibot.config.noisy_output = False


# Paths
npc_list = os.path.join(constants.OUTPUT_DIRECTORY, "Unique_NPC_Names_For_Patch.txt")
image_input_directory = os.path.join(constants.IMAGE_INPUT_DIRECTORY)

output_temp_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "temp_uploads")
os.makedirs(output_temp_directory, exist_ok=True)

debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "pywikibot_create_npc_pages.log")
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)


# Settings
TEST_RUN = False

PAGE_SUMMARY_TEXT = "Page creation for a new NPC from most recent patch."
IMAGE_SUMMARY_TEXT = "Uploading upscaled version of NPC image"
UPLOAD_TEMPLATE = "{{License|game}}"

TARGET_SCALE = 10

CHUNK_SIZE = 25
CHUNK_SLEEP_SECONDS = 3


def log_debug(message: str) -> None:
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\n")


def normalize_npc_name(raw_name: str) -> str:
    # Keep consistent with your existing create_npc_page title-casing.
    return create_npc_page.to_title_case(raw_name.strip())


def read_npc_list() -> list[str]:
    if not os.path.exists(npc_list):
        raise FileNotFoundError(f"NPC list file not found: {npc_list}")

    names = []
    seen = set()

    for line in read_file_lines(npc_list):
        raw = (line or "").strip()
        if not raw:
            continue

        name = normalize_npc_name(raw)
        key = name.lower()
        if key in seen:
            continue

        seen.add(key)
        names.append(name)

    return names


def build_npc_page_text(npc_name: str) -> str:
    # Use your existing page-assembly pipeline + file locations.
    one_liner_path = create_npc_page.get_one_liner_file_path(npc_name)
    cycles_path = create_npc_page.get_cycles_file_path(npc_name)

    one_liner_text = create_npc_page.read_text_file(one_liner_path)
    cycles_text = create_npc_page.read_text_file(cycles_path)
    schedule_text = create_npc_page.load_schedule_text(npc_name)

    one_liners = create_npc_page.extract_chat_templates(one_liner_text)

    return create_npc_page.build_page_wikitext(
        npc_name=npc_name,
        one_liners=one_liners,
        cycles_text=cycles_text,
        schedule_text=schedule_text,
    )


def scale_image_nearest(image_path: str, scale: int) -> Image.Image:
    with Image.open(image_path) as img:
        img = img.convert("RGBA")
        new_size = (img.width * scale, img.height * scale)
        return img.resize(new_size, Image.NEAREST)


def candidate_image_names(npc_name: str) -> list[str]:
    """
    Generate filename candidates for the npc_name across a few common name formats.
    """
    base_variants = []
    base_variants.append(npc_name)                     # "Claude"
    base_variants.append(npc_name.replace(" ", ""))    # "OldMan"
    base_variants.append(npc_name.replace(" ", "_"))   # "Old_Man"

    patterns = []
    for b in base_variants:
        patterns.extend([
            f"icon_{b}.png",
            f"{b}_idle_south_0.png",
            f"{b}_south_0.png",
            f"{b}_walk_south_0.png",
            f"{b}_0.png",
            f"{b}_Idle_0.png",          # ✅ NEW FORMAT
        ])

    # de-dupe while preserving order
    seen = set()
    out = []
    for p in patterns:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out

def find_associated_image_path(npc_name: str) -> str | None:
    if not os.path.isdir(image_input_directory):
        log_debug(f"Image input directory missing: {image_input_directory}")
        return None

    # Fast path: direct existence checks
    for filename in candidate_image_names(npc_name):
        path = os.path.join(image_input_directory, filename)
        if os.path.exists(path):
            return path

    # Fallback: case-insensitive scan once
    try:
        files_lower = {f.lower(): f for f in os.listdir(image_input_directory)}
    except Exception as e:
        log_debug(f"Failed to list image directory: {e}")
        return None

    for filename in candidate_image_names(npc_name):
        real = files_lower.get(filename.lower())
        if real:
            return os.path.join(image_input_directory, real)

    return None


def upload_image_to_wiki(image: Image.Image, upload_name: str) -> None:
    temp_path = os.path.join(output_temp_directory, upload_name)
    image.save(temp_path)

    file_page = pywikibot.FilePage(site, "File:" + upload_name)
    file_page.text = UPLOAD_TEMPLATE

    try:
        if file_page.exists():
            log_debug(f"Skipped image upload '{upload_name}' (file already exists on wiki).")
            return

        if TEST_RUN:
            log_debug(f"TEST_RUN: Would upload image '{upload_name}' from '{temp_path}'.")
            return

        file_page.upload(temp_path, comment=IMAGE_SUMMARY_TEXT, ignore_warnings=False)
        log_debug(f"Uploaded image: {upload_name}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def create_npc_page_on_wiki(npc_name: str, page_text: str) -> bool:
    page = pywikibot.Page(site, npc_name)
    if page.exists():
        log_debug(f"Skipped '{npc_name}' (page already exists).")
        return False

    if TEST_RUN:
        log_debug(f"TEST_RUN: Would create page '{npc_name}'.")
        return True

    page.text = page_text
    page.save(summary=PAGE_SUMMARY_TEXT, minor=False)
    log_debug(f"Created page: {npc_name}")
    return True


def chunk_list(lst: list[str], chunk_size: int):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def main() -> None:
    print("🔍 Loading NPC list...")
    log_debug("--- Starting NPC page creation ---")

    try:
        npc_names = read_npc_list()
    except Exception as e:
        log_debug(f"ERROR reading NPC list: {e}")
        raise

    total = len(npc_names)
    print(f"🔍 NPCs loaded: {total}")
    log_debug(f"NPCs loaded: {total} | Source: {npc_list}")

    created_pages = 0
    attempted_images = 0
    uploaded_images = 0

    processed = 0
    last_reported_percent = -1

    for chunk in chunk_list(npc_names, CHUNK_SIZE):
        for npc_name in chunk:
            processed += 1

            try:
                page_text = build_npc_page_text(npc_name)
                created = create_npc_page_on_wiki(npc_name, page_text)

                if created:
                    created_pages += 1

                # Image handling: only attempt if we can find a local image
                image_path = find_associated_image_path(npc_name)
                if image_path:
                    attempted_images += 1

                    upload_name = f"{npc_name}.png"
                    scaled = scale_image_nearest(image_path, TARGET_SCALE)

                    before = uploaded_images
                    upload_image_to_wiki(scaled, upload_name)

                    # If it didn't exist, upload_image_to_wiki logs upload; we can infer by checking again:
                    # (Keep it simple: attempt a quick exists check to count successful uploads.)
                    try:
                        if pywikibot.FilePage(site, "File:" + upload_name).exists():
                            # Might have already existed, but that's fine—best effort.
                            # Only increment if it was newly created is hard without extra logic.
                            # We'll do a light heuristic: if it didn't exist earlier, we'd need caching.
                            pass
                    except Exception:
                        pass

                else:
                    log_debug(f"No associated image found for '{npc_name}'. Skipping upload.")

            except Exception as e:
                log_debug(f"FAILED '{npc_name}': {e}")
                log_debug(traceback.format_exc())

            percent = int((processed / max(total, 1)) * 100)
            if percent >= last_reported_percent + 10:
                print(f"  ✅ {processed}/{total} processed — ({percent}%)")
                last_reported_percent = percent

        time.sleep(CHUNK_SLEEP_SECONDS)

    print(f"\n✅ Done. Pages created: {created_pages}/{total}. Image attempts: {attempted_images}.")
    log_debug(f"--- Completed. Pages created: {created_pages}/{total}. Image attempts: {attempted_images}. ---")


if __name__ == "__main__":
    main()
