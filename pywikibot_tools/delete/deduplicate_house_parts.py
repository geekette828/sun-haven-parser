"""
This script normalizes house variant image files on a MediaWiki site.

Workflow:
1. Ensures a canonical "<Type> House.png" image exists and is uploaded if missing.
2. Checks if all variant parts (Door, Roof, Walls, Windows, Patio) redirect to the base image. If so, skips.
3. If all parts are duplicates of each other, deletes them and redirects them to the base image.
4. If a variant differs:
   - Attempts to rename it to "<name>1.png".
   - If "1.png" exists, compares their hashes.
       - If similar, deletes the original and redirects to the base image.
       - If different, logs for manual review.

Relies on preloaded page data, hash comparisons using imagehash, and structured logging.
"""

import os
import sys
import time
import requests
import imagehash
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from pywikibot.pagegenerators import PreloadingGenerator
from utils import file_utils, wiki_utils
from PIL import Image

# Config
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "normalize_house_variants.txt")
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

site = wiki_utils.get_site()
image_input_directory = os.path.join(constants.IMAGE_INPUT_DIRECTORY)
PART_SUFFIXES = ["Door", "Roof", "Walls", "Windows", "Patio"]

HASH_TOLERANCE = 5
MIN_SIZE = 200
GLOBAL_SLEEP = 5

# Logging
def log_debug(msg):
    file_utils.append_line(debug_log_path, msg)

# Helper functions
def get_image_hash(img):
    return imagehash.average_hash(img)

def get_scaled_dimensions(img):
    w, h = img.size
    short = min(w, h)
    scale = MIN_SIZE / short
    return (round(w * scale), round(h * scale))

def get_local_icon_path(base_type):
    return os.path.join(image_input_directory, f"icon_house_{base_type.lower().replace(' ', '_')}.png")

def format_wiki_filename(base_type):
    return f"{base_type} House.png"

def is_redirect_to(page, target_title):
    return page.isRedirectPage() and page.getRedirectTarget().title() == f"File:{target_title}"

def all_variants_redirect(preloaded_pages, base_type, canonical_name):
    for suffix in PART_SUFFIXES:
        name = f"{base_type} {suffix}.png"
        page = preloaded_pages.get(name)
        if page and page.exists() and not is_redirect_to(page, canonical_name):
            return False
    return True

# Core function
def normalize_type(base_type, preloaded_pages):
    print(f"🔧 Processing: {base_type}")
    canonical_name = format_wiki_filename(base_type)
    canonical_page = pywikibot.FilePage(site, canonical_name)
    local_path = get_local_icon_path(base_type)

    # Skip if already done
    if all_variants_redirect(preloaded_pages, base_type, canonical_name):
        log_debug(f"⏩ Skipping {base_type}, all variants already redirect.")
        return

    # Step 1: Ensure base image exists
    if not canonical_page.exists():
        if not os.path.exists(local_path):
            log_debug(f"❌ Missing local icon for: {base_type} ({local_path})")
            return
        try:
            img = Image.open(local_path)
            img = img.resize(get_scaled_dimensions(img), resample=Image.NEAREST)
            tmp_path = os.path.join(image_input_directory, f"upload_{base_type}.png")
            img.save(tmp_path)
            canonical_page.upload(tmp_path, ignore_warnings=True, comment="Uploading scaled canonical house image")
            log_debug(f"📤 Uploaded: {canonical_name}")
        except Exception as e:
            log_debug(f"❌ Upload failed for {canonical_name}: {e}")
            return

    # Step 2: Gather variant hashes
    variant_hashes = {}
    for suffix in PART_SUFFIXES:
        variant_name = f"{base_type} {suffix}.png"
        page = preloaded_pages.get(variant_name)
        if not page or not page.exists():
            log_debug(f"🟡 Missing: {variant_name}")
            continue
        try:
            downloaded = page.get_file_url()
            tmp_path = os.path.join(image_input_directory, f"variant_{variant_name.lower().replace(' ', '_')}")
            r = requests.get(downloaded)
            r.raise_for_status()
            with open(tmp_path, "wb") as f:
                f.write(r.content)
            with Image.open(tmp_path) as img:
                variant_hashes[variant_name] = (get_image_hash(img), page)
        except Exception as e:
            log_debug(f"❌ Error hashing {variant_name}: {e}")

    # Step 3: Compare all variants to each other
    if len(variant_hashes) < 2:
        log_debug(f"⚠️ Not enough variants to validate: {base_type}")
        return

    variant_list = list(variant_hashes.items())
    mismatch_found = False
    base_hash = variant_list[0][1][0]
    for other_name, (other_hash, _) in variant_list[1:]:
        delta = abs(base_hash - other_hash)
        log_debug(f"🔍 Δ={delta} vs {variant_list[0][0]} and {other_name}")
        if delta > HASH_TOLERANCE:
            mismatch_found = True
            break

    if not mismatch_found:
        # All are duplicates, delete + redirect to canonical
        for variant_name, (_, page) in variant_hashes.items():
            try:
                page.delete(reason=f"Redirect to [[File:{canonical_name}]]", prompt=False)
                time.sleep(1)
                redirect = pywikibot.FilePage(site, variant_name)
                redirect.text = f"#REDIRECT [[File:{canonical_name}]]"
                redirect.save(summary=f"Redirect to [[File:{canonical_name}]]")
                log_debug(f"🔁 Redirect created for {variant_name} → {canonical_name}")
            except Exception as e:
                log_debug(f"❌ Failed to delete or redirect {variant_name}: {e}")
        return

    # Step 4: Handle mismatched variants
    for variant_name, (hash1, page1) in variant_hashes.items():
        alt_name = variant_name.replace(".png", "1.png")
        alt_page = pywikibot.FilePage(site, alt_name)
        if not alt_page.exists():
            try:
                page1.move(alt_name, reason="Renaming variant to avoid conflict", leave_redirect=False, movetalk=False)
                redirect = pywikibot.FilePage(site, variant_name)
                redirect.text = f"#REDIRECT [[File:{canonical_name}]]"
                redirect.save(summary=f"Redirect to [[File:{canonical_name}]]")
                log_debug(f"📁 Moved {variant_name} → {alt_name} and redirected to {canonical_name}")
            except Exception as e:
                log_debug(f"❌ Failed to move {variant_name} to {alt_name}: {e}")
        else:
            try:
                downloaded = alt_page.get_file_url()
                tmp_path = os.path.join(image_input_directory, f"alt_{alt_name.lower().replace(' ', '_')}")
                r = requests.get(downloaded)
                r.raise_for_status()
                with open(tmp_path, "wb") as f:
                    f.write(r.content)
                with Image.open(tmp_path) as img:
                    hash2 = get_image_hash(img)
                if abs(hash1 - hash2) <= HASH_TOLERANCE:
                    page1.delete(reason=f"Duplicate of [[File:{canonical_name}]]", prompt=False)
                    redirect = pywikibot.FilePage(site, variant_name)
                    redirect.text = f"#REDIRECT [[File:{canonical_name}]]"
                    redirect.save(summary=f"Redirect to [[File:{canonical_name}]]")
                    log_debug(f"🗑️ Deleted {variant_name} and redirected to {canonical_name}")
                else:
                    log_debug(f"⚠️ Conflict: {variant_name} and {alt_name} differ beyond tolerance")
            except Exception as e:
                log_debug(f"❌ Failed comparing {variant_name} with {alt_name}: {e}")

# Main execution
def main():
    base_types = [
        "Mini Green Polka Dot", "Mini Blue Polka Dot", "Log Cabin", "Ice", "Honeycomb",
        "Greenhouse", "Green Striped", "Green Poke A Dot", "Green Plank", "Gingerbread",
        "Demo Kit", "Deep Sea", "Cow Print", "Cottage Core", "Charming", "Cat", "Castle",
        "Cardboard", "Brown Stone", "Brown Cobblestone", "Blue Tiled", "Blue Striped",
        "Blue Poke A Dot", "Basic", "Bamboo", "Yellow", "Yellow Striped", "Yellow Poke A Dot",
        "Withergate", "Upgrade Kit", "Terracotta", "Terracotta Shackle", "Stucco", "Straw",
        "Stone", "Stone Brick", "Steel", "Slimey", "Slime Drop", "Simple", "Simple Red",
        "Simple Green", "Simple Blue", "Robotic", "Rickity", "Red", "Red Striped", "Red Prism",
        "Red Brick", "Red Poke A Dot", "Purple Striped", "Purple Ruffled", "Purple Poke A Dot",
        "Oriental", "Orange Tiled", "Old Stone", "Neon", "Nature", "Monster Mouth",
        "Mini Yellow Polka Dot"
    ]

    all_variant_titles = [f"{base} {suffix}.png" for base in base_types for suffix in PART_SUFFIXES]
    preloaded = {page.title(with_ns=False): page for page in PreloadingGenerator([pywikibot.FilePage(site, title) for title in all_variant_titles])}

    for base in base_types:
        normalize_type(base, preloaded)
        print(f"⏳ Sleeping {GLOBAL_SLEEP}s to avoid rate limits...")
        time.sleep(GLOBAL_SLEEP)

    log_debug("✅ Normalization complete.")

if __name__ == "__main__":
    main()
