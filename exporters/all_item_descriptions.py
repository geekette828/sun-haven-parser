"""
Item descriptions writer — Layer 3 of the pipeline.

Reads item data from the builder cache and writes a Lua /data module file
suitable for pasting into Module:Description/data on the wiki.

Usage:
    python exporters/all_item_descriptions.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from builders.item_builder import _CACHE_FILE, _load_cache
from utils import file_utils

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR  = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "Module_Description_data.txt")

# Hardcoded aliases: alias_key -> original_key (both lowercase)
ALIAS_MAP = {
    "sprinkles":  "blueberry sprinkles",
    "shiver":     "black shiver",
    "kitty (pet)": "black kitty",
    "cape":       "black cape",
}

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

    descriptions = {}
    seen_keys = set()

    for item in items.values():
        name = item.name
        description = item.description

        if not name or not description:
            continue

        # Normalize base name: lowercase
        name = name.lower().replace("_", " ")

        # Scrub description: remove unwanted formatting
        description = description.replace("\\", "")
        description = description.replace("\n", "<br>")
        description = description.replace('"', "")
        description = re.sub(r"<color=[^>]*>", "", description)
        description = description.replace("</color>", "")
        description = re.sub(r"<sprite=[^>]*>", "", description)

        # Normalize item name: remove (Color), trailing numbers, extra whitespace
        simplified_name = re.sub(r"\s?\(.*?\)$", "", name)   # Remove (Green), (Blue), etc.
        simplified_name = re.sub(r"\s\d+$", "", simplified_name)  # Remove "Chair 1", "Chair 101"
        simplified_name = simplified_name.strip()

        if not simplified_name:
            continue

        # Only keep first occurrence of each simplified name
        if simplified_name in seen_keys:
            continue

        seen_keys.add(simplified_name)
        descriptions[simplified_name] = description

    # Add hardcoded aliases after all items are processed
    for alias, original in ALIAS_MAP.items():
        if original in descriptions:
            descriptions[alias] = descriptions[original]

    # Generate Lua /data module output
    lua_lines = []
    lua_lines.append("local data = {\n")

    for item_key, desc in sorted(descriptions.items()):
        safe_item = item_key.replace("\\", "")
        safe_desc = desc.replace("\\", "")
        lua_lines.append(f'    ["{safe_item}"] = "{safe_desc}",\n')

    lua_lines.append("}\n\nreturn data\n")

    file_utils.write_lines(OUTPUT_FILE, lua_lines)

    print(f"Lua /data module generated successfully: {OUTPUT_FILE}")


if __name__ == "__main__":
    run()
