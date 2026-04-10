"""
Item page writer — Layer 3 of the pipeline.

Builds item data via the builder, exports wikitext via the exporters,
and writes one .txt file per item to the output directory.

Usage:
    python exporters/create_item_pages.py

Toggle TEST_RUN / TEST_ITEMS to target specific items, or set
ALL_ITEMS = True to write pages for every item in the dataset.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from builders.item_builder import _CACHE_FILE, _load_cache
from formatters.pages.item_page import export_item_page
from utils import file_utils

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ALL_ITEMS = False       # Set True to write pages for every item

TEST_ITEMS = [
    "Ethereal Pegasus Mount Whistle",
    "Astral Wallpaper",
    "Arcade Flooring",
    "Spring Door",
    "Myths and Muses Chair",
]

OUTPUT_DIR = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Item Pages")

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(OUTPUT_DIR)

    if not os.path.exists(_CACHE_FILE):
        print(f"❌ No item data found. Run the builder first:")
        print(f"   python builders/item_builder.py")
        return

    print("Loading item data...")
    items = _load_cache()

    targets = list(items.keys()) if ALL_ITEMS else [n.lower() for n in TEST_ITEMS]

    created = 0
    skipped = 0

    for key in targets:
        item = items.get(key)
        if item is None:
            print(f"  ⚠️  Not found: '{key}'")
            skipped += 1
            continue

        page_content = export_item_page(item, display_name=item.name)
        safe_filename = item.name.replace(" ", "_").replace("'", "") + ".txt"
        output_path = os.path.join(OUTPUT_DIR, safe_filename)

        try:
            file_utils.write_lines(output_path, [page_content])
            print(f"  ✅ {item.name}")
            created += 1
        except Exception as exc:
            print(f"  ❌ Failed to write {item.name}: {exc}")
            skipped += 1

    print(f"\nDone. {created} written, {skipped} skipped.")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    run()
