import os
from utils import json_utils, file_utils, text_utils
import config.constants as constants

from formatter.quest_page.infobox import create_quest_infobox, load_item_lookup, build_guid_lookup
from formatter.quest_page.layout import create_quest_layout

# --- Output Setup ---
def get_output_dir():
    path = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Quest Pages")
    file_utils.ensure_dir_exists(path)
    return path

def clean_filename(name):
    return name.replace(" ", "_").replace("'", "").replace(":", "").strip()

# --- Optional navbox ---
def create_navbox(quest):
    return ""  # Placeholder

# --- Select quests by name ---
def find_quests_by_names(quest_data, names):
    normalized = {n.strip().lower() for n in names}
    results = []
    seen = set()

    for quest_list in quest_data.values():
        for q in quest_list:
            q_name = q.get("questName", "").strip().lower()
            key = (q_name, q.get("questDescription", "").strip(), q.get("npcToTurnInTo", "").strip())
            if q_name in normalized and key not in seen:
                seen.add(key)
                results.append(q)
    return results

# --- Combine nested quest dictionaries ---
def merge_all_quests(quest_files):
    combined = {}
    for data in quest_files.values():
        for k, v in data.items():
            combined.setdefault(k, []).extend(v)
    return combined

# --- Main Execution ---
def main():
    test_quests = [
        "First Date With Claude",
        "Second Date With Anne",
        "Attend the Snowball Fight",
        "Soup On"
    ]

    quest_files = ["quest_data_BB_SQ.json", "quest_data_MainQuests.json"]
    input_dir = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")

    raw_data = {}
    for file in quest_files:
        path = os.path.join(input_dir, file)
        if os.path.exists(path):
            try:
                raw_data[file] = json_utils.load_json(path)
            except Exception as e:
                print(f"Error loading {file}: {e}")

    combined_quests = merge_all_quests(raw_data)
    item_lookup = load_item_lookup()
    guid_lookup = build_guid_lookup(combined_quests)
    output_dir = get_output_dir()

    selected = find_quests_by_names(combined_quests, test_quests)

    for quest in selected:
        name = quest.get("questName", "Unnamed Quest")
        filename = f"_TEST_{clean_filename(name)}_Page.txt"

        # Format item fields
        quest["itemRequirementsFormatted"] = text_utils.clean_text("; ".join(
            f"{item_lookup.get(str(i.get('id')), f'Unknown Item ({i.get('id')})')}*{i.get('amount', 1)}"
            for i in quest.get("itemRequirements", [])
        ))
        quest["guaranteeRewardsFormatted"] = text_utils.clean_text("; ".join(
            f"{item_lookup.get(str(i.get('id')), f'Unknown Item ({i.get('id')})')}*{i.get('amount', 1)}"
            for i in quest.get("guaranteeRewards2", [])
        ))
        quest["choiceRewardsFormatted"] = text_utils.clean_text("; ".join(
            f"{item_lookup.get(str(i.get('id')), f'Unknown Item ({i.get('id')})')}*{i.get('amount', 1)}"
            for i in quest.get("choiceRewards2", [])
        ))

        # Components
        infobox = create_quest_infobox(quest, item_lookup, guid_lookup)
        npc = quest.get("npcToTurnInTo", "")
        bulletin = text_utils.clean_text(quest.get("bulletinBoardDescription", ""))
        end_text = text_utils.format_for_chat(quest.get("endTex", ""))

        layout = create_quest_layout(quest, npc=npc, bulletin=bulletin, end_text=end_text)
        navbox = create_navbox(quest)

        full_page = f"{infobox}\n\n{layout}\n\n{navbox}".strip()
        file_path = os.path.join(output_dir, filename)
        file_utils.write_lines(file_path, [full_page])
        print(f"Wrote: {file_path}")

if __name__ == "__main__":
    main()
