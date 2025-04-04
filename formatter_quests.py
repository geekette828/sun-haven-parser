import os
import re

from utils import json_utils, file_utils, text_utils
import config.constants as constants

# Construct full paths using the constants from config
input_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted")

# Ensure the output directory exists using the file utility
file_utils.ensure_dir_exists(output_directory)

# Define JSON files
quest_files = ["quest_data_BB_SQ.json", "quest_data_MainQuests.json"]
items_data_file = "items_data.json"

# Hardcoded values for non-tangible items
HARDCODED_ITEMS = {
    "60000": "Coins",
    "60001": "Orbs",
    "60002": "Tickets",
    "60004": "Combat EXP",
    "60005": "Exploration EXP",
    "60006": "Mining EXP",
    "60007": "Bonus Mana",
    "60008": "Fishing EXP",
    "60009": "Fishing EXP",
    "18013": "Community Token",
}

# Load item ID -> Name mappings using json_utils
def load_items_data():
    items_path = os.path.join(input_directory, items_data_file)
    if not os.path.exists(items_path):
        print(f"Error: {items_data_file} not found in {input_directory}")
        return {}

    try:
        items_data = json_utils.load_json(items_path)
    except Exception as e:
        print(f"Error decoding JSON from {items_data_file}: {e}")
        return {}

    # Merge hardcoded items with actual item data
    id_to_name = HARDCODED_ITEMS.copy()
    id_to_name.update(
        {str(item_details["ID"]): item_details["Name"] 
         for item_details in items_data.values() if "ID" in item_details}
    )
    return id_to_name

# Function to replace item IDs with item names
def format_items(items_list, item_lookup):
    """Formats requires, rewards, and bonus sections using the item lookup dictionary."""
    if not items_list:
        return ""

    formatted_items = []
    for item in items_list:
        item_id = str(item.get("id"))
        amount = item.get("amount", 1)
        item_name = item_lookup.get(item_id, f"Unknown Item ({item_id})")
        formatted_items.append(f"{item_name}*{amount}")

    return "; ".join(formatted_items)

# Function to create a lookup dictionary for GUIDs to quest names
def build_guid_lookup(quest_data):
    guid_lookup = {}
    for quest_list in quest_data.values():
        for quest in quest_list:
            if isinstance(quest, dict) and "guid" in quest:
                guid_lookup[quest["guid"]] = quest.get("questName", f"Unknown Quest ({quest['guid']})")
    return guid_lookup

# Function to resolve the next quest name from a GUID using the lookup dictionary
def resolve_next_quest(next_quest, guid_lookup):
    if isinstance(next_quest, dict) and "guid" in next_quest:
        return guid_lookup.get(next_quest["guid"], next_quest["guid"])
    return "None" if not next_quest else next_quest

# Function to process each quest file and store the formatted output
def process_quests(file_name, item_lookup, guid_lookup):
    input_path = os.path.join(input_directory, file_name)
    output_file_path = os.path.join(output_directory, f"{file_name.replace('.json', '.txt')}")

    if not os.path.exists(input_path):
        print(f"Error: {file_name} not found in {input_directory}")
        return

    try:
        quest_data = json_utils.load_json(input_path)
    except Exception as e:
        print(f"Error decoding JSON from {file_name}: {e}")
        return

    formatted_text = ""

    for quest_list in quest_data.values():
        for quest in quest_list:
            quest_name = quest.get("questName", "Unknown Quest")
            quest_filename = quest.get("filename", "Unknown File")
            time_value = "Unlimited" if quest.get("daysToDo", -1) == -1 else f"{quest['daysToDo']} days"
            next_quest_name = resolve_next_quest(quest.get("nextQuest"), guid_lookup)

            # Use text_utils.clean_text and text_utils.format_for_chat
            bulletin_board_desc = text_utils.clean_text(quest.get("bulletinBoardDescription", ""))
            end_tex = text_utils.format_for_chat(quest.get("endTex", ""))
            region = quest.get("region", "Unknown Region")

            formatted_text += f"""\n### {quest_filename} ###
{{{{Quest infobox
|name      = {quest_name}
|objective = {text_utils.clean_text(quest.get("questDescription", ""))}
|type      = {quest.get("questType", "")}
|time      = {time_value}
|npc       = {quest.get("npcToTurnInTo", "")}
|location  = 
|prereq    = 
<!-- Quest Requirements and Rewards -->
|requires  = {format_items(quest.get("itemRequirements", []), item_lookup)}
|rewards   = {format_items(quest.get("guaranteeRewards2", []), item_lookup)}
|bonus     = {format_items(quest.get("choiceRewards2", []), item_lookup)}
<!-- Quest Chronology -->
|prev      = 
|next      = {next_quest_name}
}}}}

{{{{BB quest description|{region}|{bulletin_board_desc}<br>-{quest.get("npcToTurnInTo", "")}}}}}

{{{{Chat|{quest.get("npcToTurnInTo", "")}|{end_tex}}}}}
"""

    file_utils.write_lines(output_file_path, [formatted_text])
    print(f"Formatted quests saved to {output_file_path}")

# Main execution

# Load item data
item_lookup = load_items_data()

# Build GUID lookup table from all quest files
guid_lookup = {}
for json_file in quest_files:
    input_path = os.path.join(input_directory, json_file)
    if os.path.exists(input_path):
        try:
            quest_data = json_utils.load_json(input_path)
            guid_lookup.update(build_guid_lookup(quest_data))
        except Exception:
            print(f"Error decoding {json_file}, skipping GUID mapping.")

# Process each quest file
for json_file in quest_files:
    process_quests(json_file, item_lookup, guid_lookup)
