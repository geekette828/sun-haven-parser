'''
This python script pulls a list of pages that are both `Mounts` and `DLC`
then associates specific cateogories to those image files
so they show up in various DPL queries on the wiki.
'''

import sys
import config.constants as constants
import os
import pywikibot
import time
import re

# Pywikibot config
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
pywikibot.config.throttle = constants.PWB_SETTINGS["throttle"]
pywikibot.config.max_retries = constants.PWB_SETTINGS["max_retries"]
pywikibot.config.retry_wait = constants.PWB_SETTINGS["retry_wait"]
pywikibot.config.user_agent = constants.PWB_SETTINGS["user_agent"]
site = pywikibot.Site()

# Paths
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "pywikibot_updateMountImage.txt")
debug_log_path = os.path.join(constants.OUTPUT_DIRECTORY, "Debug", "pywikibot_updateMountImage_debug.txt")
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)

# Constants
UNKNOWN_PACK_CATEGORY = "Unknown pack images"

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

def image_has_caption(text):
    return re.search(r'^\s*==\s*Caption\s*==\s*$', text, re.IGNORECASE | re.MULTILINE)

def image_has_licensing(text):
    return "{{Games}}" in text and re.search(r'==\s*Licensing\s*==\s*\n\{\{Games\}\}', text, re.IGNORECASE)

def get_required_categories(image_type, pack_category):
    cats = {"Sun Haven assets"}
    if pack_category:
        cats.add(f"{pack_category} images")
    if image_type == "Side":
        cats.update({"Mount images", "DLC mount images"})
    return cats

def add_missing_elements(file_page, image_type, title, pack_category):
    text = file_page.text
    modified = False
    fix_log_parts = []
    categories = get_category_titles(file_page)

    # Caption
    if not image_has_caption(text):
        caption_block = f"==Caption==\n[[{title}|{title}]]\n\n"
        text = caption_block + text
        modified = True
        fix_log_parts.append("Caption section")

    # Licensing
    if "{{Games}}" in text:
        if not image_has_licensing(text):
            text = re.sub(r'(\{\{Games\}\})', r'==Licensing==\n\1', text, count=1, flags=re.IGNORECASE)
            modified = True
            fix_log_parts.append("Inserted Licensing header above {{Games}}")
    else:
        text += "\n\n==Licensing==\n{{Games}}"
        modified = True
        fix_log_parts.append("Added Licensing section with {{Games}}")

    # Categories
    required = get_required_categories(image_type, pack_category)
    missing = required - categories
    for cat in sorted(missing):
        text += f"\n[[Category:{cat}]]"
        modified = True
        fix_log_parts.append(f"Added category: {cat}")

    return text, modified, fix_log_parts, missing

def main():
    try:
        mounts_pages = get_category_members("Mounts")
        dlc_pages = get_category_members("DLC")
        common_pages = sorted(mounts_pages & dlc_pages)

        print(f"✅ Found {len(common_pages)} pages that are both in 'Mounts' and 'DLC' categories.")

        page_map = preload_pages(common_pages)

        # Logs
        missing_images = []
        missing_base = []
        mismatch_pack = []
        unknown_pack = []
        missing_caption = []
        non_standard = []

        for title in common_pages:
            if "whistle" not in title.lower():
                non_standard.append(title)
                continue

            # Determine base name and enforce 'Mount' in name
            base_name = title.rsplit(" Whistle", 1)[0]
            if "mount" not in base_name.lower():
                base_name += " Mount"

            whistle_file = f"{title}.png"
            base_file = f"{base_name}.png"
            side_file = f"{base_name} Side.png"
            all_files = [("Whistle", whistle_file), ("Base", base_file), ("Side", side_file)]

            file_map = preload_file_pages([f[1] for f in all_files])
            original_page = page_map.get(title)
            original_categories = get_category_titles(original_page) if original_page else set()
            pack_category = next((cat for cat in original_categories if cat.endswith("pack") and cat.lower() != "unknown dlc pack"), None)

            for image_type, file_name in all_files:
                file_page = file_map.get(file_name)
                if file_page is None or not file_page.exists():
                    missing_images.append(f"{image_type}: {file_name}")
                    continue

                current_text = file_page.text
                required_categories = get_required_categories(image_type, pack_category)
                current_categories = get_category_titles(file_page)

                already_good = (
                    image_has_caption(current_text)
                    and image_has_licensing(current_text)
                    and required_categories.issubset(current_categories)
                )

                if already_good:
                    continue

                updated_text, modified, fix_log_parts, missing_cats = add_missing_elements(
                    file_page, image_type, title, pack_category
                )

                # Log base category issues
                if missing_cats:
                    missing_base.append(f"{file_name}: missing {', '.join(sorted(missing_cats))}")

                # Log caption
                if not image_has_caption(current_text):
                    missing_caption.append(file_name)

                # Log unknown or mismatch
                if UNKNOWN_PACK_CATEGORY in current_categories:
                    unknown_pack.append(file_name)
                if pack_category and f"{pack_category} images" not in current_categories:
                    mismatch_pack.append(f"{file_name}: has no match for '{pack_category} images'")

                # Create missing category page
                if pack_category:
                    pack_image_category = f"{pack_category} images"
                    cat_page = pywikibot.Page(site, f"Category:{pack_image_category}")
                    if not cat_page.exists():
                        try:
                            cat_page.text = f"{{{{category}}}}\n[[Category:{pack_category}]]"
                            cat_page.save(summary=f"Creating image category for {pack_category}")
                            log_debug(f"📁 Created category: [[Category:{pack_image_category}]]")
                            time.sleep(6)
                        except Exception as e:
                            log_debug(f"❌ Failed to create category [[Category:{pack_image_category}]]: {e}")

                if modified and updated_text.strip() != file_page.text.strip():
                    file_page.text = updated_text
                    try:
                        file_page.save(summary=f"Updated {image_type} image: added caption, licensing, categories")
                        log_debug(f"🔧 Fixed {file_name}: " + " + ".join(fix_log_parts))
                        time.sleep(6)
                    except Exception as e:
                        log_debug(f"❌ Failed to save {file_name}: {e}")
                        time.sleep(10)

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
            if non_standard:
                write_section_header(out, "Non-standard Mount Page")
                out.write("\n".join(non_standard) + "\n")

    except Exception as e:
        log_debug(f"Unexpected error in main: {e}")
        print("⚠️ An error occurred. Check the debug log for details.")

if __name__ == "__main__":
    main()
