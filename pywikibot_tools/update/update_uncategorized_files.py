
""" 
This script processes files listed on Special:UncategorizedFiles. It:
1. Null-edits files that already have both license and manual categories.
2. Null-edits and logs files with manual categories but no license.
3. Categorizes and saves files that have a license but no categories, if the base page allows inference.
4. Adds a license and categories for fully uncategorized and unlicensed files with a valid base page.
5. Logs and skips anything that cannot be processed.
Requires: Pywikibot 10.1+ for UnCategorizedImageGenerator.
"""

import os
import re
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pywikibot
from pywikibot import pagegenerators
from pywikibot.pagegenerators import PreloadingGenerator
from utils import wiki_utils

DEBUG_LOG_PATH = os.path.join(".hidden", "debug_output", "pywikibot", "image_categorizer.txt")
UNCATEGORIZED_FILE_BATCH = 1000
BATCH_SIZE = 50
SLEEP_INTERVAL = 5
NULL_EDIT_SLEEP_INTERVAL = 10

page_to_image_category = {
    "Foods": "Food images", 
    "Crops": "Crop images", 
    "Armor": "Armor images",
    "Tools": "Tool images", 
    "Weapons": "Weapon images", 
    "Skills": "Player skill images", 
    "Clothing": "Clothing images",
    "NPCs": "NPC images", 
    "Quest items": "Quest item images", 
    "Accessories": "Accessory images",
    "Furniture": "Furniture images", 
    "Wallpaper": "Wallpaper images", 
    "Tiles": "Tile images",
    "Resources": "Resource images", 
    "Potions": "Potion images", 
    "Sheds": "Shed images",
    "Workbenches": "Workbench images", 
    "Fertilizers": "Fertilizer images",
    "Barn animals": "Barn animal images", 
    "Pets": "Pet images", 
    "Fish": "Fish images",
    "Monsters": "Monster images", 
    "Records": "Record images", 
    "Jams": "Jam images",
    "Bait": "Bait images", 
    "Keys": "Key images", 
    "Stats": "Player stat images",
    "Skills": "Player skill images",
    "Miscellaneous items": "Miscellaneous item images", "Junk items": "Miscellaneous item images", 
    "Building permits and upgrades": "Miscellaneous item images", "Consumer goods": "Miscellaneous item images",
    "Currencies": "Miscellaneous item images", "Totems": "Miscellaneous item images", "Scarecrows": "Miscellaneous item images", 
    "Tomes": "Miscellaneous item images", "Essences": "Miscellaneous item images", "Misc catches": "Miscellaneous item images",
}

npc_animation_keywords = ["breath", "breathing", "blink", "blinking", "walk", "walking", "read", "laugh"]

def log_debug(msg):
    os.makedirs(os.path.dirname(DEBUG_LOG_PATH), exist_ok=True)
    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg.strip() + "\n")

def has_license_header(text):
    return "==Licensing==" in text or "{{Fair use" in text or "{{Copyright" in text or "{{Games" in text

def get_page_categories(title):
    try:
        page = pywikibot.Page(wiki_utils.get_site(), title)
        return [cat.title().removeprefix("Category:") for cat in page.categories()] if page.exists() else []
    except Exception:
        return []

def infer_categories(filename, base_name, site):
    categories = []
    name_lower = filename.lower()

    if filename.endswith(".gif"):
        categories.append("Animations")
        if any(name_lower.endswith(k + ".gif") for k in npc_animation_keywords):
            if pywikibot.Page(site, base_name).exists():
                if "NPCs" in get_page_categories(base_name):
                    categories.append("NPC animations")

    if " wallpaper display" in name_lower:
        categories.append("Wallpaper display images")
    if filename.lower().endswith(" seeds.png"):
        categories.append("Seed images")
    if filename.lower().endswith(" stall.png"):
        categories.append("Stall images")
    if filename.lower().endswith(" node.png"):
        categories.append("Mineral node images")
    if filename.lower().startswith("face "):
        categories.append("NPC images")

    # Player house customization
    if (
        re.search(r"house tier\s*[123]", filename.lower()) or
        filename.startswith("CommunityHouseCustom-") or
        re.search(r"windows[123]\.png$", filename.lower()) or
        re.search(r"roof[123]\.png$", filename.lower()) or
        re.search(r"door[123]\.png$", filename.lower())
    ):
        categories.append("External house customization images")
    if filename.lower().startswith("greenhouse "):
        categories.append("Miscellaneous item images")
    if re.search(r"(?:_|\s|\()?stages?(?:_|\s)?(?:[0-9]|10|[0-9] golden|10 golden)", name_lower):
        page_cats = get_page_categories(base_name)
        if "Crops" in page_cats or "Trees" in page_cats:
            categories.append("Crop stage images")
        else:
            log_debug(f"🔍 Detected stage pattern but no crop/tree match: {filename}")
            categories.append("Crop stage images")

    if " whistle.png" in name_lower:
        if not pywikibot.Page(site, base_name).exists():
            if base_name.lower().endswith(" whistle"):
                base_name = " ".join(base_name.split(" ")[:-1]) + " whistle"
        if "Mount whistle" in base_name.lower() or "whistle" in base_name.lower():
            categories.append("Mount whistle images")

    match = re.match(r"(.+?) \(([^)]+)\)(?: [BRL])?\.png", filename)
    if match:
        item_name = match.group(1).strip()
        if "Clothing" in get_page_categories(item_name):
            categories.append("Clothing images")

    if base_name.endswith(" Shed"):
        if not pywikibot.Page(site, base_name).exists():
            kit_page = base_name + " Kit"
            if "Sheds" in get_page_categories(kit_page):
                categories.append("Shed images")

    for cat in get_page_categories(base_name):
        if cat in page_to_image_category:
            categories.append(page_to_image_category[cat])

    return list(set(categories))

def process_files():
    site = wiki_utils.get_site()
    uncategorized_files = list(pagegenerators.UnCategorizedImageGenerator(site=site, total=UNCATEGORIZED_FILE_BATCH))
    print(f"🔍 Found {len(uncategorized_files)} uncategorized files")

    for i in range(0, len(uncategorized_files), BATCH_SIZE):
        batch = uncategorized_files[i:i + BATCH_SIZE]
        print(f"📦 Processing batch {i // BATCH_SIZE + 1} of {((len(uncategorized_files) - 1) // BATCH_SIZE) + 1}")
        for file_page in PreloadingGenerator(batch, BATCH_SIZE):
            filename = file_page.title(with_ns=False)
            base_name = re.sub(r"\.\w+$", "", filename)

            if " wallpaper display" in filename.lower():
                base_name = filename[:filename.lower().index(" wallpaper display")]

            text = file_page.text
            has_license = has_license_header(text)
            has_categories = bool(re.search(r"\[\[Category:.*?\]\]", text))

            if has_license and has_categories:
                try:
                    file_page.touch()
                    print(f"🔄 Null-edited (licensed + categorized): {filename}")
                    time.sleep(NULL_EDIT_SLEEP_INTERVAL)
                except Exception as e:
                    log_debug(f"❌ Null-edit error for {filename}: {e}")
                continue

            if has_categories and not has_license:
                log_debug(f"⚠️ Missing license (but has categories): {filename}")
                try:
                    file_page.touch()
                    print(f"🔄 Null-edited (missing license): {filename}")
                    time.sleep(NULL_EDIT_SLEEP_INTERVAL)
                except Exception as e:
                    log_debug(f"❌ Null-edit error for {filename}: {e}")
                continue

            categories_to_add = infer_categories(filename, base_name, site)
            if not categories_to_add:
                log_debug(f"❓ No category match for: {filename}")
                continue

            if not has_license:
                text += "\n==Licensing==\n{{Games}}"

            for cat in categories_to_add:
                text += f"\n[[Category:{cat}]]"
            text += "\n"

            file_page.text = text
            try:
                file_page.save(summary="Added " + ", ".join(f"[[Category:{c}]]" for c in categories_to_add))
                print(f"✅ Categorized: {filename}")
            except Exception as e:
                log_debug(f"❌ Failed to save {filename}: {e}")
        time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    process_files()