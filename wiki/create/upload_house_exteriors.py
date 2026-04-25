"""
Uploads composited house exterior images from the House Exteriors output folder
to the wiki.

Behaviour per file:
- Not on wiki yet  → upload with license template and category.
- Already on wiki  → check page text; add any missing license / category.
- Already complete → skip.

Usage:
    python upload_house_exteriors.py                # all styles, all tiers
    python upload_house_exteriors.py "Log Cabin"    # one style, all tiers
"""

import os
import re
import sys
import time
import argparse
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from utils import image_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
input_directory = os.path.join(constants.OUTPUT_DIRECTORY, "House Exteriors")
debug_log_path  = os.path.join(
    constants.DEBUG_DIRECTORY, "pywikibot", "pywikibot_house_exteriors.txt"
)
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)
if os.path.exists(debug_log_path):
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write(
            "\n\n------------------- "
            + time.strftime("%Y-%m-%d %H:%M:%S")
            + " -------------------\n"
        )

# ---------------------------------------------------------------------------
# Wiki text constants
# ---------------------------------------------------------------------------
LICENSE_TEMPLATE = "{{License|game}}"
CATEGORY         = "[[Category:House Exterior images]]"
UPLOAD_COMMENT   = "House exterior composite image upload"

FULL_PAGE_TEXT = f"==Licensing==\n{LICENSE_TEMPLATE}\n{CATEGORY}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def has_license(text):
    """Return True if the file page already contains the license template."""
    return "{{License|game}}" in text


def has_category(text):
    """Return True if the file page already contains the house exterior category."""
    return bool(re.search(
        r'\[\[\s*Category\s*:\s*House Exterior images\s*\]\]',
        text,
        re.IGNORECASE,
    ))


def get_image_files(style=None):
    """
    Return sorted (filepath, filename) pairs from the House Exteriors folder.
    Optionally filtered to a single style by prefix match.
    """
    if not os.path.isdir(input_directory):
        print(f"✗ Output folder not found: {input_directory}")
        return []

    results = []
    for filename in sorted(os.listdir(input_directory)):
        if not filename.lower().endswith(".png"):
            continue
        if style and not filename.lower().startswith(style.lower()):
            continue
        results.append((os.path.join(input_directory, filename), filename))
    return results


# ---------------------------------------------------------------------------
# Upload / update logic
# ---------------------------------------------------------------------------

def upload_or_update_file(filepath, filename):
    """
    Upload a new file, or patch the page text of an existing file with any
    missing license template or category.
    """
    site      = pywikibot.Site()
    file_page = pywikibot.FilePage(site, f"File:{filename}")

    if not file_page.exists():
        file_page.text = FULL_PAGE_TEXT
        try:
            file_page.upload(filepath, comment=UPLOAD_COMMENT, ignore_warnings=False)
            image_utils.log_debug(f"Uploaded: {filename}", debug_log_path)
            print(f"    ✓ Uploaded: {filename}")
        except Exception as e:
            image_utils.log_debug(f"Upload failed for {filename}: {e}", debug_log_path)
            print(f"    ✗ Upload failed: {filename} — {e}")
        return

    # File already exists — check for missing pieces
    text    = file_page.text
    missing = []

    if not has_license(text):
        missing.append(("license", f"==Licensing==\n{LICENSE_TEMPLATE}"))

    if not has_category(text):
        missing.append(("category", CATEGORY))

    if not missing:
        image_utils.log_debug(f"Skipped (already complete): {filename}", debug_log_path)
        print(f"    — Already complete: {filename}")
        return

    labels   = [label for label, _ in missing]
    additions = [addition for _, addition in missing]
    new_text  = text.rstrip() + "\n" + "\n".join(additions)

    file_page.text = new_text
    try:
        file_page.save(summary=f"Add missing {', '.join(labels)}")
        image_utils.log_debug(
            f"Updated ({', '.join(labels)}): {filename}", debug_log_path
        )
        print(f"    ✓ Updated ({', '.join(labels)}): {filename}")
    except Exception as e:
        image_utils.log_debug(f"Failed to update {filename}: {e}", debug_log_path)
        print(f"    ✗ Update failed: {filename} — {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Upload house exterior composite images to the wiki."
    )
    parser.add_argument(
        "style",
        nargs="?",
        help="House style name (e.g. 'Log Cabin'). Omit to upload all styles.",
    )
    args = parser.parse_args()

    files = get_image_files(args.style)
    if not files:
        print("No images found to upload.")
        return

    total = len(files)
    label = f'"{args.style}"' if args.style else "all styles"
    print(f"🏠 Uploading {total} house exterior image(s) — {label}")

    for idx, (filepath, filename) in enumerate(files, 1):
        print(f"  [{idx}/{total}] {filename}")
        upload_or_update_file(filepath, filename)

    print(f"\n✅ Done.")


if __name__ == "__main__":
    main()
