import sys
import config
import os
import pywikibot
import time
import re

# Set up pyWikiBot configurations
sys.path.append(config.ADDITIONAL_PATHS["PWB"])
site = pywikibot.Site()

# Paths
output_file_path = os.path.join(config.OUTPUT_DIRECTORY, "Pywikibot", "pywikibot_updatePetImage.txt")
debug_log_path = os.path.join(config.OUTPUT_DIRECTORY, "Debug", "pywikibot_updatePetImage_debug.txt")
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
        # Step 1: Collect pages from both categories
        pets_pages = get_category_members("Pets")
        dlc_pages = get_category_members("DLC")
        common_pages = sorted(pets_pages & dlc_pages)

        print(f"✅ Found {len(common_pages)} pages that are both 'Pets' and 'DLC' categories.")
        print("📦 Gathering and updating category information from matched pages...")

        # Step 2: Preload both the pages and their image files
        page_map = preload_pages(common_pages)
        file_titles = [f"{title}.png" for title in common_pages]
        file_map = preload_file_pages(file_titles)

        # Containers for sorting results
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

            # Check base categories and fix if needed
            missing = BASE_CATEGORIES - image_categories
            fix_log_parts = []
            if missing:
                updated_text = file_page.text
                modified = False

                if "Sun Haven assets" in missing:
                    has_licensing_header = re.search(r'^\s*==\s*Licensing\s*==\s*$', file_page.text, re.IGNORECASE | re.MULTILINE)
                    has_games_template = "{{Games}}" in file_page.text

                    if has_games_template and not has_licensing_header:
                        # Insert '==Licensing==' above '{{Games}}'
                        updated_text = re.sub(r'(\{\{Games\}\})', r'==Licensing==\n\1', file_page.text, count=1, flags=re.IGNORECASE)
                        modified = True
                        fix_log_parts.append("Inserted Licensing header above {{Games}}")
                    elif not has_games_template and not has_licensing_header:
                        # Add both at the end
                        updated_text = file_page.text + "\n\n==Licensing==\n{{Games}}"
                        modified = True
                        fix_log_parts.append("Added Licensing section with {{Games}}")
                    else:
                        updated_text = file_page.text  # No changes needed here

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

                if modified and updated_text.strip() != file_page.text.strip():
                    file_page.text = updated_text
                    try:
                        file_page.save(summary="Added missing base image categories and/or licensing section")
                        log_debug(f"🔧 Fixed {file_name}: Added {' + '.join(fix_log_parts)}")
                    except Exception as e:
                        log_debug(f"❌ Failed to save {file_name}: {e}")
                        missing_base.append(f"{file_name}: missing {', '.join(sorted(missing))}")
                else:
                    missing_base.append(f"{file_name}: missing {', '.join(sorted(missing))}")

            # Check unknown pack
            if UNKNOWN_PACK_CATEGORY in image_categories:
                unknown_pack.append(file_name)

            # Check matching pack category
            has_pack_category = False
            pack_mismatch_found = False
            for cat in image_categories:
                if cat.endswith(PACK_SUFFIX):
                    has_pack_category = True
                    base_name = cat.replace(PACK_SUFFIX, "").strip()
                    expected = f"{base_name} pack"
                    if expected not in original_categories:
                        mismatch_pack.append(f"{file_name}: has '{cat}' but page lacks '{expected}'")
                        pack_mismatch_found = True

            # Check for ==Caption== section
            has_caption = re.search(r'^\s*==\s*Caption\s*==\s*$', file_page.text, re.IGNORECASE | re.MULTILINE)
            if not has_caption:
                caption_block = f"==Caption==\n[[{title}|{title}]]\n\n"
                updated_text = caption_block + file_page.text
                if updated_text.strip() != file_page.text.strip():
                    file_page.text = updated_text
                    try:
                        file_page.save(summary="Added missing caption section to file")
                        log_debug(f"🔧 Fixed {file_name}: Added caption section")
                    except Exception as e:
                        log_debug(f"❌ Failed to add caption to {file_name}: {e}")
                        missing_caption.append(file_name)
                else:
                    missing_caption.append(file_name)

            # Log good files (fully compliant)
            if (
                not missing
                and UNKNOWN_PACK_CATEGORY not in image_categories
                and not pack_mismatch_found
                and has_caption
            ):
                log_debug(f"✅ {file_name} passed all checks.")

        # Write to output file
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