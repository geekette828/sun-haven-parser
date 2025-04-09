import sys
import config.constants as constants
import os
import pywikibot
import time
import re

# Apply Pywikibot config from constants
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
pywikibot.config.throttle = constants.PWB_SETTINGS["throttle"]
pywikibot.config.max_retries = constants.PWB_SETTINGS["max_retries"]
pywikibot.config.retry_wait = constants.PWB_SETTINGS["retry_wait"]
pywikibot.config.user_agent = constants.PWB_SETTINGS["user_agent"]

# Set up pyWikiBot configurations
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
site = pywikibot.Site()

# Paths
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "pywikibot_updatePetImage.txt")
debug_log_path = os.path.join(constants.OUTPUT_DIRECTORY, "Debug", "pywikibot_updatePetImage_debug.txt")
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)

# Constants
BASE_CATEGORIES = {"Sun Haven assets", "Pet images", "DLC pet images"}
UNKNOWN_PACK_CATEGORY = "Unknown pack images"
PACK_SUFFIX = " pack images"

def log_debug(message):
    with open(debug_log_path, "a", encoding="utf-8") as debug_file:
        debug_file.write(message + "\n")

def write_section_header(file, header):
    file.write(f"\n### {header} ###\n")

def get_category_titles(page):
    return set(cat.title().replace("Category:", "") for cat in page.categories())

def preload_pages(page_titles):
    pages = [pywikibot.Page(site, title) for title in page_titles]
    return {page.title(): page for page in site.preloadpages(pages)}

def preload_file_pages(file_titles):
    files = [pywikibot.FilePage(site, f"File:{title}") for title in file_titles]
    return {file.title(with_ns=False): file for file in site.preloadpages(files)}

def get_category_members(category_name):
    try:
        cat = pywikibot.Category(site, f"Category:{category_name}")
        return set(page.title() for page in cat.articles())
    except Exception as e:
        log_debug(f"Error fetching category {category_name}: {e}")
        return set()

def main():
    try:
        pets_pages = get_category_members("Pets")
        dlc_pages = get_category_members("DLC")
        common_pages = sorted(pets_pages & dlc_pages)

        print(f"✅ Found {len(common_pages)} pages that are both 'Pets' and 'DLC' categories.")
        print("📦 Gathering category information from matched pages...")

        page_map = preload_pages(common_pages)
        file_titles = [f"{title}.png" for title in common_pages]
        file_map = preload_file_pages(file_titles)

        missing_images = []
        missing_base = []
        mismatch_pack = []
        unknown_pack = []
        missing_caption = []

        for title in common_pages:
            file_name = f"{title}.png"
            file_page = file_map.get(file_name)
            original_page = page_map.get(title)

            if file_page is None or not file_page.exists():
                missing_images.append(file_name)
                continue

            image_categories = get_category_titles(file_page)
            original_categories = get_category_titles(original_page)
            updated_text = file_page.text
            modified = False
            fix_log_parts = []

            # --- Caption ---
            if not re.search(r'^\s*==\s*Caption\s*==\s*$', updated_text, re.IGNORECASE | re.MULTILINE):
                caption_block = f"==Caption==\n[[{title}|{title}]]\n\n"
                updated_text = caption_block + updated_text
                modified = True
                fix_log_parts.append("Caption section")

            # --- Licensing ---
            missing = BASE_CATEGORIES - image_categories
            has_games_template = "{{Games}}" in updated_text
            if has_games_template:
                if not re.search(r'==\s*Licensing\s*==\s*\n\{\{Games\}\}', updated_text, re.IGNORECASE):
                    updated_text = re.sub(r'(\{\{Games\}\})', r'==Licensing==\n\1', updated_text, count=1, flags=re.IGNORECASE)
                    modified = True
                    fix_log_parts.append("Inserted Licensing header above {{Games}}")
            else:
                updated_text += "\n\n==Licensing==\n{{Games}}"
                modified = True
                fix_log_parts.append("Added Licensing section with {{Games}}")

            cat_lines = []
            if "DLC pet images" in missing:
                cat_lines.append("[[Category:DLC pet images]]")
                fix_log_parts.append("DLC category")
            if "Pet images" in missing:
                cat_lines.append("[[Category:Pet images]]")
                fix_log_parts.append("Pet category")
            if cat_lines:
                updated_text += "\n" + "\n".join(cat_lines)
                modified = True

            # --- Pack category from pet page ---
            pack_category = None
            for cat in original_categories:
                if cat.endswith("pack") and cat.lower() != "unknown dlc pack":
                    pack_category = cat
                    break
            if pack_category:
                pack_image_category = f"{pack_category} images"
                if pack_image_category not in image_categories:
                    updated_text = updated_text.rstrip() + f"\n[[Category:{pack_image_category}]]"
                    modified = True
                    fix_log_parts.append(f"Added [[Category:{pack_image_category}]]")

                # Always check for creation, even if already present in image
                image_cat_page = pywikibot.Page(site, f"Category:{pack_image_category}")
                if not image_cat_page.exists():
                    try:
                        image_cat_page.text = f"{{{{category}}}}\n[[Category:{pack_category}]]"
                        image_cat_page.save(summary=f"Creating image category for {pack_category}")
                        log_debug(f"📁 Created category: [[Category:{pack_image_category}]]")
                        time.sleep(6)
                    except Exception as e:
                        log_debug(f"❌ Failed to create category page [[Category:{pack_image_category}]]: {e}")

            # --- Save the page if needed ---
            if modified and updated_text.strip() != file_page.text.strip():
                file_page.text = updated_text
                try:
                    file_page.save(summary="Updated image page: added missing caption, licensing, and categories")
                    log_debug(f"🔧 Fixed {file_name}: " + " + ".join(fix_log_parts))
                    time.sleep(6)  # Respect server limits
                except Exception as e:
                    log_debug(f"❌ Failed to save {file_name}: {e}")
                    time.sleep(10)  # Backoff after failure
                    if missing:
                        missing_base.append(f"{file_name}: missing {', '.join(sorted(missing))}")
                    if not re.search(r'^\s*==\s*Caption\s*==\s*$', updated_text, re.IGNORECASE | re.MULTILINE):
                        missing_caption.append(file_name)

            # --- Other status checks ---
            if UNKNOWN_PACK_CATEGORY in image_categories:
                unknown_pack.append(file_name)

            if pack_category:
                expected = f"{pack_category} images"
                if expected not in image_categories:
                    mismatch_pack.append(f"{file_name}: has no match for '{expected}' from pet page")

            if (
                not missing and
                UNKNOWN_PACK_CATEGORY not in image_categories and
                re.search(r'^\s*==\s*Caption\s*==\s*$', updated_text, re.IGNORECASE | re.MULTILINE) and
                pack_category and f"{pack_category} images" in updated_text
            ):
                log_debug(f"✅ {file_name} passed all checks.")

        with open(output_file_path, "w", encoding="utf-8") as out:
            if missing_images:
                write_section_header(out, "Missing Images")
                out.write("\n".join(missing_images) + "\n")
            if missing_base:
                write_section_header(out, "Missing a Base Category")
                out.write("\n".join(missing_base) + "\n")
            if mismatch_pack:
                write_section_header(out, "Mis-match Pack")
                out.write("\n".join(mismatch_pack) + "\n")
            if unknown_pack:
                write_section_header(out, "Unknown Pack")
                out.write("\n".join(unknown_pack) + "\n")
            if missing_caption:
                write_section_header(out, "Missing Caption Section")
                out.write("\n".join(missing_caption) + "\n")

    except Exception as e:
        log_debug(f"Unexpected error in main: {e}")
        print("⚠️ An error occurred. Check the debug log for details.")

if __name__ == "__main__":
    main()
