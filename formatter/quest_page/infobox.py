import os
from utils import json_utils, file_utils, text_utils
import config.constants as constants

def ensure_output_dir():
    output_dir = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Quest Pages")
    file_utils.ensure_dir_exists(output_dir)
    return output_dir

def format_items(items_list, item_lookup):
    if not items_list:
        return ""
    formatted_items = []
    for item in items_list:
        item_id = str(item.get("id"))
        amount = item.get("amount", 1)
        item_name = item_lookup.get(item_id, f"Unknown Item ({item_id})")
        formatted_items.append(f"{item_name}*{amount}")
    return "; ".join(formatted_items)

def load_item_lookup():
    hardcoded = {
        "60000": "Coins", "60001": "Orbs", "60002": "Tickets",
        "60004": "Combat EXP", "60005": "Exploration EXP",
        "60006": "Mining EXP", "60007": "Bonus Mana",
        "60008": "Fishing EXP", "60009": "Fishing EXP",
        "18013": "Community Token"
    }
    path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
    if not os.path.exists(path):
        return hardcoded
    try:
        data = json_utils.load_json(path)
        hardcoded.update({str(v["ID"]): v["Name"] for v in data.values() if "ID" in v})
    except Exception:
        pass
    return hardcoded

def resolve_quest_type(quest):
    title = quest.get("questName", "")
    type_number = quest.get("questType")

    if "First Date With" in title or "Second Date With" in title:
        return "Romance"
    elif "Attend the" in title:
        return "Festival"
    elif isinstance(type_number, int):
        return constants.QUEST_TYPES.get(type_number, str(type_number))
    return str(type_number or "")

def create_quest_infobox(quest, item_lookup, next_lookup):
    quest_name = quest.get("questName", "Unknown Quest")
    time_limit = quest.get("daysToDo", -1)
    time_str = "Unlimited" if time_limit == -1 else f"{time_limit} days"
    objective = text_utils.clean_text(quest.get("questDescription", ""))
    npc = quest.get("npcToTurnInTo", "")
    next_quest = quest.get("nextQuest", {})
    next_name = next_lookup.get(next_quest.get("guid", ""), next_quest.get("guid", "None")) if isinstance(next_quest, dict) else ""

    requires = format_items(quest.get("itemRequirements", []), item_lookup)
    rewards = format_items(quest.get("guaranteeRewards2", []), item_lookup)
    bonus = format_items(quest.get("choiceRewards2", []), item_lookup)

    quest_type = resolve_quest_type(quest)

    return f"""{{{{Quest infobox
|name      = {quest_name}
|objective = {objective}
|type      = {quest_type}
|time      = {time_str}
|npc       = {npc}
|location  = 
|prereq    = 
<!-- Quest Requirements and Rewards -->
|requires  = {requires}
|rewards   = {rewards}
|bonus     = {bonus}
<!-- Quest Chronology -->
|prev      = 
|next      = {next_name} }}}}\n"""

def build_guid_lookup(quest_data):
    lookup = {}
    for quests in quest_data.values():
        for q in quests:
            if "guid" in q:
                lookup[q["guid"]] = q.get("questName", q["guid"])
    return lookup

def find_quests_by_names(quest_data, test_names):
    normalized = {name.strip().lower() for name in test_names}
    matched = []
    seen_hashes = set()

    for quest_group in quest_data.values():
        for quest in quest_group:
            name = quest.get("questName", "").strip().lower()
            if name in normalized:
                # Create a unique signature to catch dupes
                unique_signature = (
                    name,
                    quest.get("questDescription", "").strip(),
                    quest.get("npcToTurnInTo", "").strip()
                )
                if unique_signature not in seen_hashes:
                    matched.append(quest)
                    seen_hashes.add(unique_signature)
    return matched

def process_all_quests(test_quests=None):
    quest_files = ["quest_data_BB_SQ.json", "quest_data_MainQuests.json"]
    item_lookup = load_item_lookup()
    output_dir = ensure_output_dir()

    guid_lookup = {}
    all_quests = {}

    for file in quest_files:
        path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", file)
        if os.path.exists(path):
            try:
                data = json_utils.load_json(path)
                all_quests[file] = data
                guid_lookup.update(build_guid_lookup(data))
            except Exception:
                print(f"Error loading {file}, skipping.")

    if test_quests:
        combined = {}
        for qd in all_quests.values():
            for k, v in qd.items():
                combined.setdefault(k, []).extend(v)
        filtered = find_quests_by_names(combined, test_quests)
        output = [create_quest_infobox(q, item_lookup, guid_lookup) for q in filtered]
        file_utils.write_lines(os.path.join(output_dir, "_TEST_quest_infoboxes.txt"), output)
        print("Test output written to TEST_quest_infoboxes.txt")
        return

    for file, data in all_quests.items():
        output_lines = []
        for quests in data.values():
            for quest in quests:
                infobox = create_quest_infobox(quest, item_lookup, guid_lookup)
                output_lines.append(f"### {quest.get('filename', 'Unknown File')}\n{infobox}\n")
        out_file = os.path.join(output_dir, file.replace(".json", "_infobox.txt"))
        file_utils.write_lines(out_file, output_lines)
        print(f"Saved quest infoboxes to {out_file}")

# TEST INFOBOXES - Will not be used if called from formatter_quest_page.py
if __name__ == "__main__":
    test_quests = [
        "First Date With Claude",
        "Second Date With Anne",
        "Attend the Snowball Fight",
        "Soup On"
    ]
    process_all_quests(test_quests=test_quests)
