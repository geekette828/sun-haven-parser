"""
Updates wiki pages for house customisation pieces (Door, Patio, Roof, Walls, Windows).

Two changes are applied to each page:

1.  Media section
    Gallery shows the full composite exterior images (Tier 3 → 2 → 1).

    - Already has our images (new format "Spring House Tier 1.png" OR old format
      "Spring House (tier 1).png") → gallery is left alone; the section is still
      uncommented if it was inside a comment block.
    - Gallery exists but has other images → our three file lines are prepended to
      the top of the existing gallery.
    - No gallery at all → a fresh ==Media== section is inserted before ==History==.
    - If ==Media== was inside a comment block, it is always moved out; any other
      content (e.g. ==Trivia==) remains commented.

2.  "Other items in the set" cross-link sentence
    - Checks whether the sentence is already present.
    - If absent, inserts it immediately above ==Display==.

Usage:
    python update_house_part_pages.py                   # all styles, all parts
    python update_house_part_pages.py "Spring"          # one style, all parts
    python update_house_part_pages.py "Spring" Wall     # one style, one part
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
# Debug log
# ---------------------------------------------------------------------------

debug_log_path = os.path.join(
    constants.DEBUG_DIRECTORY, "pywikibot", "pywikibot_update_house_parts.txt"
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
# Part / page-name mapping
# ---------------------------------------------------------------------------

# Internal key → wiki page-name suffix
PART_PAGE_SUFFIX = {
    "Door":   "Door",
    "Patio":  "Patio",
    "Roof":   "Roof",
    "Wall":   "Walls",
    "Window": "Windows",
}

# Consistent display order for the "Other items" sentence
PART_ORDER = ["Door", "Patio", "Roof", "Wall", "Window"]

ALL_HOUSE_STYLES = [
    "Bamboo", "Basic", "Blue Polka Dot", "Blue Striped",
    "Blue Tiled", "Brown Cobblestone", "Brown Stone",
    "Cardboard", "Castle", "Cat", "Charming",
    "Classic Brick", "Cottage Core", "Cow Print",
    "Deep Sea", "Eastern", "Fall", "Gingerbread",
    "Great City", "Green Plank", "Green Polka Dot",
    "Green Striped", "Greenhouse", "Honeycomb",
    "Ice", "Log Cabin", "Mini Blue Polka Dot",
    "Mini Green Polka Dot", "Mini Purple Polka Dot",
    "Mini Red Polka Dot", "Mini Yellow Polka Dot",
    "Monster Mouth", "Nature", "Neon", "Old Stone",
    "Orange Tiled", "Purple Polka Dot",
    "Purple Ruffled", "Purple Striped", "Red",
    "Red Polka Dot", "Red Prism", "Red Striped",
    "Rickity", "Robotic", "Simple Blue",
    "Simple Green", "Simple Purple", "Simple Red",
    "Simple Yellow", "Slime Drop", "Slimey",
    "Spring", "Steel", "Stone", "Stone Brick",
    "Straw", "Stucco", "Summer", "Terracotta",
    "Terracotta Shackle", "Winter", "Withergate",
    "Yellow", "Yellow Polka Dot", "Yellow Striped",
]

# ---------------------------------------------------------------------------
# Text builders
# ---------------------------------------------------------------------------

GALLERY_HEADER = (
    '<gallery widths="200" bordercolor="transparent" '
    'spacing="small" captionalign="center">'
)


def build_file_lines(style):
    """Return the three File: lines for the composite exterior images (tier 3 → 1)."""
    return "\n".join(
        f"File:{style} House Tier {tier}.png|{style} House (Tier {tier})"
        for tier in (3, 2, 1)
    )


def build_gallery_block(style):
    """Return a complete ==Media== section with composite exterior images."""
    return f"==Media==\n{GALLERY_HEADER}\n{build_file_lines(style)}\n</gallery>"


def has_our_images(text, style):
    """
    Return True if text already contains our composite exterior file references.
    Matches both the current format (Spring House Tier 1.png) and the old format
    (Spring House (tier 1).png), tolerating spaces or underscores as separators.
    """
    s = re.escape(style)
    sep = r'[\s_]'
    new_fmt = re.compile(
        rf'File\s*:\s*{s}{sep}House{sep}Tier{sep}[123]\.png',
        re.IGNORECASE,
    )
    old_fmt = re.compile(
        rf'File\s*:\s*{s}{sep}House{sep}\(tier{sep}[123]\)\.png',
        re.IGNORECASE,
    )
    return bool(new_fmt.search(text) or old_fmt.search(text))


def prepend_files_to_gallery(gallery_block, style):
    """
    Insert our three file lines at the top of an existing <gallery> block,
    immediately after the opening tag.
    """
    file_lines = build_file_lines(style)
    return re.sub(
        r'(<gallery[^>]*>)',
        rf'\1\n{file_lines}',
        gallery_block,
        count=1,
    )


def build_set_line(style, current_part):
    """Return the cross-link sentence listing the other parts in the set."""
    others = [
        f"[[{style} {PART_PAGE_SUFFIX[p]}]]"
        for p in PART_ORDER
        if p != current_part
    ]
    return f"Other items in the '''{style}''' set include {', '.join(others)}."


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Commented block that contains ==Media== and its gallery
RE_COMMENT_WITH_MEDIA = re.compile(
    r'<!--\s*(==Media==\s*<gallery[^>]*>.*?</gallery>\s*)(.*?)-->',
    re.DOTALL,
)

# Already-uncommented ==Media== section (page was previously updated)
RE_UNCOMMENTED_MEDIA = re.compile(
    r'==Media==\s*<gallery[^>]*>.*?</gallery>',
    re.DOTALL,
)

# Presence check for the "Other items" sentence (any style)
RE_SET_LINE = re.compile(
    r"Other items in the '''[^']+''' set include",
    re.IGNORECASE,
)

# ==Display== and ==History== section headers (insertion reference points)
RE_DISPLAY = re.compile(r'(==Display==)', re.IGNORECASE)
RE_HISTORY = re.compile(r'(==History==)', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Per-page update helpers
# ---------------------------------------------------------------------------

def apply_media_section(text, style):
    """
    Insert or update the ==Media== section.

    Returns (new_text, description_string) if a change was made,
    or (text, None) if nothing needed to change.
    """
    # Case 1: ==Media== is inside a comment block — always pull it out.
    m = RE_COMMENT_WITH_MEDIA.search(text)
    if m:
        media_block = m.group(1).strip()   # "==Media==\n<gallery...>...\n</gallery>"
        rest        = m.group(2).strip()   # trivia / other sections (stays commented)
        tail        = f"\n<!--\n{rest}\n-->" if rest else ""

        if has_our_images(media_block, style):
            # Our images already present — just uncomment, leave gallery as-is.
            replacement = media_block + tail
            return text[:m.start()] + replacement + text[m.end():], "uncommented media section"
        else:
            # Prepend our file lines and uncomment.
            updated_block = prepend_files_to_gallery(media_block, style)
            replacement   = updated_block + tail
            return text[:m.start()] + replacement + text[m.end():], "uncommented and prepended composite images"

    # Case 2: ==Media== already uncommented.
    m = RE_UNCOMMENTED_MEDIA.search(text)
    if m:
        gallery_block = m.group(0)
        if has_our_images(gallery_block, style):
            return text, None  # Already complete — nothing to do.
        updated = prepend_files_to_gallery(gallery_block, style)
        return text[:m.start()] + updated + text[m.end():], "prepended composite images to gallery"

    # Case 3: No media section at all — insert before ==History==.
    m = RE_HISTORY.search(text)
    if m:
        new_block = build_gallery_block(style)
        return text[:m.start()] + new_block + "\n\n" + text[m.start():], "added missing media section"

    return text, None


def apply_set_line(text, style, current_part):
    """
    Add the "Other items in the set" cross-link sentence above ==Display==.

    Returns (new_text, True) if the line was inserted, (text, False) otherwise.
    """
    if RE_SET_LINE.search(text):
        return text, False

    m = RE_DISPLAY.search(text)
    if not m:
        return text, False

    set_line = build_set_line(style, current_part)
    return text[:m.start()] + set_line + "\n\n" + text[m.start():], True


# ---------------------------------------------------------------------------
# Main update logic
# ---------------------------------------------------------------------------

def update_page(style, part_type):
    """Fetch and update a single house part wiki page."""
    suffix = PART_PAGE_SUFFIX[part_type]
    title  = f"{style} {suffix}"

    site = pywikibot.Site()
    page = pywikibot.Page(site, title)

    if not page.exists():
        image_utils.log_debug(f"Page not found: {title}", debug_log_path)
        print(f"    ✗ Page not found: {title}")
        return

    text    = page.text
    changes = []

    text, media_change = apply_media_section(text, style)
    if media_change:
        changes.append(media_change)

    text, set_line_added = apply_set_line(text, style, part_type)
    if set_line_added:
        changes.append("added set cross-links")

    if not changes:
        image_utils.log_debug(f"No changes needed: {title}", debug_log_path)
        print(f"    — No changes: {title}")
        return

    summary    = "; ".join(changes)
    page.text  = text
    try:
        page.save(summary=summary)
        image_utils.log_debug(f"Updated ({summary}): {title}", debug_log_path)
        print(f"    ✓ Updated ({summary}): {title}")
    except Exception as e:
        image_utils.log_debug(f"Save failed for {title}: {e}", debug_log_path)
        print(f"    ✗ Save failed: {title} — {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Update house part wiki pages with media gallery and set cross-links."
    )
    parser.add_argument(
        "style",
        nargs="?",
        help="House style name (e.g. 'Spring'). Omit to process all styles.",
    )
    parser.add_argument(
        "part",
        nargs="?",
        choices=list(PART_PAGE_SUFFIX.keys()),
        metavar="PART",
        help=f"Part type: {', '.join(PART_PAGE_SUFFIX.keys())}. Omit to process all parts.",
    )
    args = parser.parse_args()

    styles = [args.style] if args.style else ALL_HOUSE_STYLES
    parts  = [args.part]  if args.part  else PART_ORDER

    total = len(styles) * len(parts)
    print(f"🏠 Updating {total} page(s)")

    count = 0
    for style in styles:
        print(f"  {style}")
        for part in parts:
            count += 1
            title = f"{style} {PART_PAGE_SUFFIX[part]}"
            print(f"    [{count}/{total}] {title}")
            update_page(style, part)

    print(f"\n✅ Done.")


if __name__ == "__main__":
    main()
