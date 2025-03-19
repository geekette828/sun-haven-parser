import os
import json
import re
import config

# Construct full paths
input_directory = os.path.join(config.INPUT_DIRECTORY, "MonoBehaviour")
output_directory = os.path.join(config.OUTPUT_DIRECTORY, "JSON Data")
debug_directory = os.path.join(output_directory, "debug")

# Ensure output and debug directories exist
os.makedirs(output_directory, exist_ok=True)
os.makedirs(debug_directory, exist_ok=True)

def log_debug(filename, message):
    with open(os.path.join(debug_directory, filename), "a", encoding="utf-8") as debug_file:
        debug_file.write(message + "\n")

def extract_guid(meta_file_path):
    try:
        with open(meta_file_path, "r", encoding="utf-8") as meta_file:
            for line in meta_file:
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
        "endTex": None,
        "questDescription": None,
        "bulletinBoardDescription": None,
        "nextQuest": None
    }

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

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
                    quest_data["nextQuest"] = {"fileID": int(match.group(1)), "guid": match.group(2), "type": int(match.group(3))}

            elif "items2:" in line:
                current_section = "itemRequirements"
                pending_id = None  
            elif "guaranteeRewards2:" in line:
                current_section = "guaranteeRewards2"
                pending_id = None
            elif "choiceRewards2:" in line:
                current_section = "choiceRewards2"
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
for filename in os.listdir(input_directory):
    if filename.endswith(".asset"):
        asset_path = os.path.join(input_directory, filename)
        quest_info = parse_quest_asset(asset_path, guid_lookup)

        if quest_info["guid"] and quest_info["questName"]:
            guid_to_name[quest_info["guid"]] = quest_info["questName"]

        all_quests.append(quest_info)

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

for category, data in quest_categories.items():
    output_path = os.path.join(output_directory, f"{category}.json")
    try:
        with open(output_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4)
    except Exception as e:
        log_debug("json_writing.txt", f"Error writing {output_path}: {e}")
