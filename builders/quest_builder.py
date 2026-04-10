"""
Quest builder — Layer 1 of the pipeline.

Parses raw MonoBehaviour (.asset) files to extract quest data and writes
three categorized JSON files:
  - quest_data_BB_SQ.json    (Bulletin Board + Side quests, types 0/1)
  - quest_data_MainQuests.json (Main quests, types 2/3/4/8)
  - quest_data_IDK.json       (Uncategorized / unknown types)

Usage:
    python builders/quest_builder.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")

import config.constants as constants
from utils import file_utils, json_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_MONOBEHAVIOUR_DIR = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
_OUTPUT_DIR        = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
_DEBUG_DIR         = os.path.join(constants.DEBUG_DIRECTORY, "json")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_guid(meta_path: str) -> str | None:
    try:
        for line in file_utils.read_file_lines(meta_path):
            match = re.search(r"guid:\s*([a-f0-9]+)", line)
            if match:
                return match.group(1)
    except Exception as exc:
        file_utils.append_line(
            os.path.join(_DEBUG_DIR, "guid_extraction.txt"),
            f"Error reading meta file {meta_path}: {exc}",
        )
    return None


def _parse_quest_asset(file_path: str, guid_lookup: dict) -> dict:
    quest_data: dict = {
        "quest_name":                    None,
        "filename":                      os.path.basename(file_path),
        "guid":                          guid_lookup.get(os.path.basename(file_path)),
        "quest_type":                    None,
        "npc_to_turn_in_to":             None,
        "item_requirements":             [],
        "quest_progress_requirements":   [],
        "days_to_do":                    None,
        "character_progress_requirements": [],
        "world_progress_requirements":   [],
        "guarantee_rewards":             [],
        "choice_rewards":                [],
        "give_items_on_complete":        [],
        "end_tex":                       None,
        "quest_description":             None,
        "bulletin_board_description":    None,
        "next_quest":                    None,
    }

    try:
        lines = file_utils.read_file_lines(file_path)
        current_section = None
        pending_id = None

        for line in lines:
            line = line.strip()

            if "questName:" in line:
                quest_data["quest_name"] = line.split(":")[-1].strip()
            elif "questType:" in line:
                quest_data["quest_type"] = int(line.split(":")[-1].strip())
            elif "npcToTurnInTo:" in line:
                quest_data["npc_to_turn_in_to"] = line.split(":")[-1].strip()
            elif "daysToDo:" in line:
                quest_data["days_to_do"] = int(line.split(":")[-1].strip())
            elif "endTex:" in line:
                quest_data["end_tex"] = line.split(":")[-1].strip()
            elif "questDescription:" in line:
                quest_data["quest_description"] = line.split(":")[-1].strip()
            elif "bulletinBoardDescription:" in line:
                quest_data["bulletin_board_description"] = line.split(":")[-1].strip()
            elif "nextQuest:" in line:
                match = re.search(r"{fileID: (\d+), guid: ([a-f0-9]+), type: (\d+)}", line)
                if match:
                    quest_data["next_quest"] = {
                        "file_id": int(match.group(1)),
                        "guid":    match.group(2),
                        "type":    int(match.group(3)),
                    }
            elif "items2:" in line:
                current_section = "item_requirements"
                pending_id = None
            elif "guaranteeRewards2:" in line:
                current_section = "guarantee_rewards"
                pending_id = None
            elif "choiceRewards2:" in line:
                current_section = "choice_rewards"
                pending_id = None
            elif "giveItemsOnComplete2:" in line:
                current_section = "give_items_on_complete"
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

    except Exception as exc:
        file_utils.append_line(
            os.path.join(_DEBUG_DIR, "quest_parsing.txt"),
            f"Error parsing {file_path}: {exc}",
        )

    return quest_data


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(_OUTPUT_DIR)
    file_utils.ensure_dir_exists(_DEBUG_DIR)

    # Build GUID lookup for every asset file
    guid_lookup: dict = {}
    for quest_file in os.listdir(_MONOBEHAVIOUR_DIR):
        if quest_file.endswith(".asset"):
            meta_path = os.path.join(_MONOBEHAVIOUR_DIR, quest_file + ".meta")
            if os.path.exists(meta_path):
                guid = _extract_guid(meta_path)
                guid_lookup[quest_file] = guid

    quest_categories: dict = {
        "quest_data_BB_SQ":      {},
        "quest_data_MainQuests": {},
        "quest_data_IDK":        {},
    }
    guid_to_name: dict = {}
    all_quests: list   = []

    asset_files = [f for f in os.listdir(_MONOBEHAVIOUR_DIR) if f.endswith(".asset")]
    total = len(asset_files)
    step  = max(1, total // 5)

    print("Building quest data...")
    for idx, filename in enumerate(asset_files, start=1):
        if idx % step == 0:
            print(f"  🔄 {int((idx / total) * 100)}% complete...")

        asset_path = os.path.join(_MONOBEHAVIOUR_DIR, filename)
        quest_info = _parse_quest_asset(asset_path, guid_lookup)

        if quest_info["guid"] and quest_info["quest_name"]:
            guid_to_name[quest_info["guid"]] = quest_info["quest_name"]

        all_quests.append(quest_info)

    # Resolve next_quest GUIDs to names and categorize
    for quest in all_quests:
        if quest["next_quest"] and "guid" in quest["next_quest"]:
            quest["next_quest"] = guid_to_name.get(quest["next_quest"]["guid"])

        quest_type = quest["quest_type"]
        if quest_type in (0, 1):
            category = "quest_data_BB_SQ"
        elif quest_type in (2, 3, 4, 8):
            category = "quest_data_MainQuests"
        else:
            category = "quest_data_IDK"

        if quest_type not in quest_categories[category]:
            quest_categories[category][quest_type] = []
        quest_categories[category][quest_type].append(quest)

    # Write one JSON file per category
    for category, data in quest_categories.items():
        output_path = os.path.join(_OUTPUT_DIR, f"{category}.json")
        try:
            json_utils.write_json(data, output_path, indent=4)
            total_quests = sum(len(v) for v in data.values())
            print(f"  ✅ {category}.json — {total_quests} quests")
        except Exception as exc:
            file_utils.append_line(
                os.path.join(_DEBUG_DIR, "json_writing.txt"),
                f"Error writing {output_path}: {exc}",
            )

    print("✅ Quest build complete.")


if __name__ == "__main__":
    run()
