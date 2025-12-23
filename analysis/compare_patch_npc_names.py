'''
This script compares npc_list.txt
one per line.
'''

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from datetime import datetime
from utils.text_utils import clean_whitespace
from utils.json_utils import load_json

# Define paths
OLD_FILE_PATH = os.path.join(constants.PREVIOUS_OUTPUT_DIRECTORY, "Wiki Formatted", "npc_list.txt")
NEW_FILE_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "npc_list.txt")

OUTPUT_FILENAME = "Unique_NPC_Names_For_Patch.txt"
OUTPUT_FILE_PATH = os.path.join(constants.OUTPUT_DIRECTORY, OUTPUT_FILENAME)

DEBUG_LOG_PATH = os.path.join(
    constants.DEBUG_DIRECTORY,
    "analysis",
    "patch_quest_comparison.log"
)
os.makedirs(os.path.dirname(DEBUG_LOG_PATH), exist_ok=True)

# LOGGING
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# NORMALIZATION
def normalize_name(name):
    return clean_whitespace(name).lower()

# LOAD TXT FILE
def load_npc_names(path):
    if not os.path.exists(path):
        log(f"ERROR: File not found -> {path}")
        return set()

    with open(path, "r", encoding="utf-8") as f:
        return {
            normalize_name(line)
            for line in f
            if line.strip()
        }

# MAIN
def main():
    log("🔍 Loading NPC lists...")

    old_npcs = load_npc_names(OLD_FILE_PATH)
    new_npcs = load_npc_names(NEW_FILE_PATH)

    log(f"Old NPCs loaded: {len(old_npcs)}")
    log(f"New NPCs loaded: {len(new_npcs)}")

    unique_new_npcs = sorted(new_npcs - old_npcs)

    log(f"✅ Unique new NPCs found: {len(unique_new_npcs)}")

    with open(OUTPUT_FILE_PATH, "w", encoding="utf-8") as f:
        for npc in unique_new_npcs:
            f.write(npc + "\n")

    log(f"✅ Output written to: {OUTPUT_FILE_PATH}")

if __name__ == "__main__":
    main()