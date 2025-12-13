'''
This script compares the all_item_descriptions.txt from the current patch
To the all_item_descriptions.txt from the previous patch (set in constants)
And produces a cumulative list of item descriptions
'''

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants

# Define paths
OLD_FILE_PATH = os.path.join(
    constants.PREVIOUS_OUTPUT_DIRECTORY,
    "Wiki Formatted",
    "Module_Description_data.txt",
)
NEW_FILE_PATH = os.path.join(
    constants.OUTPUT_DIRECTORY,
    "Wiki Formatted",
    "Module_Description_data.txt",
)

OUTPUT_FILENAME = "Merged_Descriptions_For_Patch.txt"
OUTPUT_FILE_PATH = os.path.join(constants.OUTPUT_DIRECTORY, OUTPUT_FILENAME)

DEBUG_LOG_PATH = os.path.join(
    constants.DEBUG_DIRECTORY,
    "analysis",
    "patch_description_merge.log",
)
os.makedirs(os.path.dirname(DEBUG_LOG_PATH), exist_ok=True)


# LOGGING
def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_lines(path: str) -> list[str]:
    """Load a file as a list of raw lines. No normalization, no parsing."""
    if not os.path.exists(path):
        log(f"ERROR: File not found -> {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()


def main():
    log("🔍 Loading description modules...")

    old_lines = load_lines(OLD_FILE_PATH)
    new_lines = load_lines(NEW_FILE_PATH)

    log(f"Old file lines: {len(old_lines)}")
    log(f"New file lines: {len(new_lines)}")

    # Start with all old lines exactly as-is
    merged_lines: list[str] = list(old_lines)

    # Track which exact lines we already have
    seen_lines = set(old_lines)

    added_lines = 0

    for line in new_lines:
        # If the exact line text (including indentation, commas, etc.)
        # is not already present, append it.
        if line not in seen_lines:
            merged_lines.append(line)
            seen_lines.add(line)
            added_lines += 1

    log(f"✅ Unique new lines added from current patch: {added_lines}")
    log(f"✅ Total merged lines: {len(merged_lines)}")

    # Write full merged Lua module, ready to paste into the wiki
    with open(OUTPUT_FILE_PATH, "w", encoding="utf-8") as f:
        f.writelines(merged_lines)

    log(f"✅ Merged output written to: {OUTPUT_FILE_PATH}")


if __name__ == "__main__":
    main()
