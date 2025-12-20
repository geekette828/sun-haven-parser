'''
This script compares quest_data_BB_SQ.json from the current patch
to quest_data_BB_SQ.json from the previous patch (set in constants)
and produces a list of NEW bulletin board quest names (questName),
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
OLD_FILE_PATH = os.path.join(constants.PREVIOUS_OUTPUT_DIRECTORY, "JSON Data", "quest_data_BB_SQ.json")
NEW_FILE_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "quest_data_BB_SQ.json")

OUTPUT_FILENAME = "Unique_BB_Quest_Names_For_Patch.txt"
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
    return clean_whitespace(str(name)).lower()

def iter_dicts_with_key(obj, key_name):
    """
    Recursively yield dicts anywhere in obj that contain key_name.
    Handles nested dict/list JSON structures.
    """
    if isinstance(obj, dict):
        if key_name in obj:
            yield obj
        for v in obj.values():
            yield from iter_dicts_with_key(v, key_name)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_dicts_with_key(item, key_name)

def load_questname_map(json_path):
    """
    Returns a dict: normalized_quest_name -> original questName (from the file).
    Recursively searches the JSON for dicts containing 'questName'.
    """
    if not os.path.exists(json_path):
        log(f"ERROR: File not found -> {json_path}")
        return {}

    data = load_json(json_path)

    result = {}
    duplicates = {}

    found_any = False

    for quest_dict in iter_dicts_with_key(data, "questName"):
        found_any = True

        quest_name = quest_dict.get("questName")
        if quest_name is None:
            continue

        cleaned_original = clean_whitespace(str(quest_name))
        if not cleaned_original:
            continue

        norm = normalize_name(cleaned_original)

        if norm in result and result[norm] != cleaned_original:
            duplicates.setdefault(norm, set()).update([result[norm], cleaned_original])

        result.setdefault(norm, cleaned_original)

    if not found_any:
        log(f"WARNING: No dicts containing 'questName' were found in {json_path}")

    if duplicates:
        for norm, variants in sorted(duplicates.items()):
            log(f"WARNING: Duplicate questName (normalized='{norm}') with variants: {sorted(variants)}")

    return result

def main():
    log("🔍 Loading quest JSON files...")

    old_map = load_questname_map(OLD_FILE_PATH)
    new_map = load_questname_map(NEW_FILE_PATH)

    old_set = set(old_map.keys())
    new_set = set(new_map.keys())

    log(f"Old bulletin board quests loaded: {len(old_set)}")
    log(f"New bulletin board quests loaded: {len(new_set)}")

    unique_new_norm = sorted(new_set - old_set)
    unique_new_names = [new_map[n] for n in unique_new_norm]

    log(f"✅ Unique new bulletin board quests found: {len(unique_new_names)}")

    os.makedirs(os.path.dirname(OUTPUT_FILE_PATH) or ".", exist_ok=True)

    with open(OUTPUT_FILE_PATH, "w", encoding="utf-8") as f:
        for quest_name in unique_new_names:
            f.write(quest_name + "\n")

    log(f"✅ Output written to: {OUTPUT_FILE_PATH}")

if __name__ == "__main__":
    main()
