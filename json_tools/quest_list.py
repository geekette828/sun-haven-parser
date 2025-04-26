import os
import sys
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils, json_utils

# Construct full paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
debug_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Debug")

# Ensure output and debug directories exist
file_utils.ensure_dir_exists(output_directory)
file_utils.ensure_dir_exists(debug_directory)

def log_debug(filename, message):
    debug_file_path = os.path.join(debug_directory, filename)
    file_utils.append_line(debug_file_path, message)

def extract_guid(meta_file_path):
    try:
        lines = file_utils.read_file_lines(meta_file_path)
        for line in lines:
            match = re.search(r"guid:\s*([a-f0-9]+)", line)
            if match:
                return match.group(1)
    except Exception as e:
        log_debug("guid_extraction.txt", f"Error reading meta file {meta_file_path}: {e}")
    return None

def parse_quest_asset(file_path, guid_lookup):
    quest_data = {
        "questName": None,
        "filename": os.path.basename(file_path),
        "guid": guid_lookup.get(os.path.basename(file_path), None),
        "questType": None,
        "npcToTurnInTo": None,
        "itemRequirements": [],
        "questProgressRequirements": [],
        "daysToDo": None,
        "characterProgressRequirements": [],
        "worldProgressRequirements": [],
        "guaranteeRewards2": [],
        "choiceRewards2": [],
        "giveItemsOnComplete2": [],  # Added new field
        "endTex": None,
        "questDescription": None,
        "bulletinBoardDescription": None,
        "nextQuest": None
    }

    try:
        lines = file_utils.read_file_lines(file_path)
        current_section = None
        pending_id = None

        for index, line in enumerate(lines):
            line = line.strip()

            if "questName:" in line:
                quest_data["questName"] = line.split(":")[-1].strip()
            elif "questType:" in line:
                quest_data["questType"] = int(line.split(":")[-1].strip())
            elif "npcToTurnInTo:" in line:
                quest_data["npcToTurnInTo"] = line.split(":")[-1].strip()
            elif "daysToDo:" in line:
                quest_data["daysToDo"] = int(line.split(":")[-1].strip())
            elif "endTex:" in line:
                quest_data["endTex"] = line.split(":")[-1].strip()
            elif "questDescription:" in line:
                quest_data["questDescription"] = line.split(":")[-1].strip()
            elif "bulletinBoardDescription:" in line:
                quest_data["bulletinBoardDescription"] = line.split(":")[-1].strip()
            elif "nextQuest:" in line:
                match = re.search(r"{fileID: (\d+), guid: ([a-f0-9]+), type: (\d+)}", line)
                if match:
                    quest_data["nextQuest"] = {
                        "fileID": int(match.group(1)),
                        "guid": match.group(2),
                        "type": int(match.group(3))
                    }
            elif "items2:" in line:
                current_section = "itemRequirements"
                pending_id = None
            elif "guaranteeRewards2:" in line:
                current_section = "guaranteeRewards2"
                pending_id = None
            elif "choiceRewards2:" in line:
                current_section = "choiceRewards2"
                pending_id = None
            elif "giveItemsOnComplete2:" in line:
                current_section = "giveItemsOnComplete2"
                pending_id = None
            elif "---" in line:
                current_section = None
                pending_id = None
            elif current_section and "id:" in line:
                pending_id = line.split(":")[-1].strip()
            elif current_section and "amount:" in line and pending_id is not None:
                amount = line.split(":")[-1].strip()
                quest_data[current_section].append({"id": pending_id, "amount": amount})
                pending_id = None

    except Exception as e:
        log_debug("quest_parsing.txt", f"Error parsing {file_path}: {e}")

    return quest_data

# Build GUID lookup for each quest asset
guid_lookup = {}
guid_to_name = {}

for quest_file in os.listdir(input_directory):
    if quest_file.endswith(".asset"):
        meta_path = os.path.join(input_directory, quest_file + ".meta")
        if os.path.exists(meta_path):
            guid = extract_guid(meta_path)
            guid_lookup[quest_file] = guid

quest_categories = {
    "quest_data_BB_SQ": {},
    "quest_data_MainQuests": {},
    "quest_data_IDK": {}
}

all_quests = []

# Progress Tracking
asset_files = [f for f in os.listdir(input_directory) if f.endswith(".asset")]
total_files = len(asset_files)

print("Starting quest processing...")

for idx, filename in enumerate(asset_files, start=1):
    asset_path = os.path.join(input_directory, filename)
    quest_info = parse_quest_asset(asset_path, guid_lookup)

    if quest_info["guid"] and quest_info["questName"]:
        guid_to_name[quest_info["guid"]] = quest_info["questName"]

    all_quests.append(quest_info)

    # Progress print every 20%
    percent_complete = (idx / total_files) * 100
    previous_percent = ((idx - 1) / total_files) * 100

    if (percent_complete // 20) > (previous_percent // 20):
        print(f"  🔄 {int(percent_complete // 20) * 20}% complete...")

print("✅ Quest json processing complete.")

# Resolve nextQuest fields using guid_to_name
for quest in all_quests:
    if quest["nextQuest"] and "guid" in quest["nextQuest"]:
        quest_guid = quest["nextQuest"]["guid"]
        quest["nextQuest"] = guid_to_name.get(quest_guid, None)

    if quest["questType"] in [0, 1]:
        category = "quest_data_BB_SQ"
    elif quest["questType"] in [2, 3, 4, 8]:
        category = "quest_data_MainQuests"
    else:
        category = "quest_data_IDK"

    if quest["questType"] not in quest_categories[category]:
        quest_categories[category][quest["questType"]] = []

    quest_categories[category][quest["questType"]].append(quest)

# Write JSON output for each quest category
for category, data in quest_categories.items():
    output_path = os.path.join(output_directory, f"{category}.json")
    try:
        json_utils.write_json(data, output_path, indent=4)
    except Exception as e:
        log_debug("json_writing.txt", f"Error writing {output_path}: {e}")