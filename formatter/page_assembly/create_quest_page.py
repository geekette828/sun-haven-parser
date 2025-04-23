import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from utils import json_utils, file_utils
from mappings.quest_mapping import extract_quest_context
from formatter.quest_infobox import create_quest_infobox, load_item_lookup, build_guid_lookup, resolve_quest_type
from formatter.quest_summary import create_quest_summary
from formatter.quest_sections import (
    create_quest_overview_box,
    create_quest_overview_steps_box,
    create_quest_step_list,
    create_quest_bb_description,
    create_quest_description,
    create_quest_complete_text,
    create_quest_dialogue,
    create_quest_walkthrough,
    create_hidden_block,
)

from config import constants

def create_quest_page(quest, npc="", bulletin="", end_text=""):
    item_lookup = load_item_lookup()
    next_lookup = {}
    quest_type = resolve_quest_type(quest).lower()

    ctx = extract_quest_context(quest, npc=npc, end_text=end_text)
    infobox = create_quest_infobox(quest, item_lookup, next_lookup)
    ctx = extract_quest_context(quest, npc=npc, end_text=end_text)
    summary = create_quest_summary(quest, npc=ctx["npc"], bulletin=ctx["description"], end_text=end_text)

    sections = []

    if "romance" in quest_type:
        sections.append(create_hidden_block(quest))

    elif quest_type in ["bulletin", "bulletin board"]:
        sections.extend([
            create_quest_overview_box(quest),
            create_quest_step_list(quest),
            create_quest_bb_description(quest),
            create_quest_complete_text(quest),
            create_hidden_block(quest)
        ])

    elif quest_type == "character":
        sections.extend([
            create_quest_overview_box(quest),
            create_quest_step_list(quest),
            create_quest_description(quest),
            create_quest_dialogue(quest),
            create_hidden_block(quest)
        ])

    elif "main" in quest_type:
        sections.extend([
            create_quest_overview_steps_box(quest),
            create_quest_step_list(quest),
            create_quest_walkthrough(quest),
            create_hidden_block(quest)
        ])

    else:
        sections.append(create_hidden_block(quest))

    full_page = "\n".join([infobox, summary]) + "\n\n" + "\n".join(sections).strip()
    return full_page

def main():
    json_dir = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
    output_dir = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Quest Pages")
    file_utils.ensure_dir_exists(output_dir)

    # Load both JSON files
    main_quests = json_utils.load_json(os.path.join(json_dir, "quest_data_MainQuests.json"))
    bulletin_quests = json_utils.load_json(os.path.join(json_dir, "quest_data_BB_SQ.json"))

    # Merge all quests into one flat dictionary
    all_quests = {q["questName"]: q for section in main_quests.values() for q in section}
    all_quests.update({q["questName"]: q for section in bulletin_quests.values() for q in section})

    test_items = [
        "DarkWaters1Quest",
        "Claude Wants Soup!",
        "Pirate's Compass",
        "Bad Wing Day",
        "Second Date With Claude",
    ]

    for name, quest in all_quests.items():
        if len(sys.argv) > 1 or name in test_items:
            page_text = create_quest_page(quest)
            filename = os.path.join(output_dir, f"_TEST_{name}_Page.txt")
            file_utils.write_lines(filename, [page_text])
            print(f"✔ Created: {filename}")

if __name__ == "__main__":
    main()
