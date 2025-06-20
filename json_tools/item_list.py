import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
import re
import logging
from utils import file_utils, json_utils
from config import skip_items
from math import floor

# Define paths
monobehaviour_directory = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
gamedata_directory = os.path.join(constants.INPUT_DIRECTORY, "GameObject")
en_display_name_file = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")

output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
output_file = "items_data.json"

file_utils.ensure_dir_exists(output_directory)

# Setup logging
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "json", "items_data_debug.txt")
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))
logging.basicConfig(filename=debug_log_path, level=logging.DEBUG, format="%(levelname)s: %(message)s")

def extract_guid(meta_file):
    try:
        content = "\n".join(file_utils.read_file_lines(meta_file))
    except Exception as e:
        print(f"Error reading {meta_file}: {e}")
        return None
    match = re.search(r'guid:\s*([a-f0-9]+)', content)
    return match.group(1) if match else None

def extract_icon_guid(asset_file):
    try:
        lines = file_utils.read_file_lines(asset_file)
    except Exception as e:
        print(f"Error reading {asset_file}: {e}")
        return None
    for line in lines:
        line = line.strip()
        if match := re.match(r'icon:\s*{fileID:\s*\d+,\s*guid:\s*([\da-f]+),', line):
            return match.group(1)
    return None

def extract_item_info(asset_file):
    basename = os.path.basename(asset_file)
    match = re.match(r"(\d+)\s+-\s+(.+)\.asset", basename)
    if match:
        return int(match.group(1)), match.group(2)
    return None, None

def extract_key_display_name(asset_file):
    try:
        lines = file_utils.read_file_lines(asset_file)
        for line in lines:
            if "keyDisplayName:" in line:
                return line.split("keyDisplayName:")[1].strip()
    except Exception as e:
        logging.warning(f"Failed to extract keyDisplayName from {asset_file}: {e}")
    return None

def should_exclude_item(item_name):
    name = item_name.lower()
    for pattern in skip_items.SKIP_ITEMS:
        if name == pattern:
            return True
    for pattern in skip_items.SKIP_PATTERNS:
        cleaned = pattern.strip("*").lower()
        if cleaned in name:
            return True
    return False

def get_display_names(prefab_file):
    display_names = {}
    try:
        lines = file_utils.read_file_lines(prefab_file)
        current_term = None
        capturing_language = False

        for line in lines:
            line = line.strip()

            if line.startswith("- Term:"):
                current_term = line.split(":", 1)[1].strip()
                capturing_language = False

            elif line.startswith("Languages:") and current_term:
                capturing_language = True  # Start watching for language content

            elif capturing_language and line.startswith("- "):
                # Capture the first language entry only
                display_names[current_term] = line[2:].strip()
                capturing_language = False
                current_term = None

    except Exception as e:
        print(f"Error reading display names: {e}")
    return display_names

def extract_attributes(asset_file):
    def parse_number(val):
        return float(val) if '.' in val else int(val)

    attributes = {
        "ID": None,
        "description": None,
        "useDescription": None,
        "stackSize": None,
        "canSell": None,
        "sellPrice": None,
        "orbsSellPrice": None,
        "ticketSellPrice": None,
        "rarity": None,
        "hearts": None,
        "decorationType": None,
        "isDLCItem": None,
        "isForageable": None,
        "isGem": None,
        "isAnimalProduct": None,
        "isMeal": None,
        "isFruit": None,
        "isArtisanryItem": None,
        "isPotion": None,
        "hasSetSeason": None,
        "setSeason": None,
        "experience": None,
        "health": None,
        "mana": None,
        "requiredLevel": None,
        "stats": [],
        "maxStats": [],
        "foodStat": [],
        "statBuff": [],
        "cropStages": [],
        "seasons": None,
        "iconGUID": None
    }

    try:
        lines = file_utils.read_file_lines(asset_file)
        capturing_description = False
        capturing_stats = False
        capturing_max_stats = False
        capturing_food_stat = False
        capturing_seasons = False
        capturing_crop_stages = False
        capturing_stat_buff = False
        capturing_stat_buff_stats = False
        stat_buff_duration = None
        description_lines = []
        seasons_list = []
        crop_stages = []

        for line in lines:
            line = line.strip()

            if match := re.match(r'^(health|mana|requiredLevel|stackSize|sellPrice|orbsSellPrice|ticketSellPrice|rarity|hearts|decorationType|hasSetSeason|setSeason|experience):\s*([\d.]+)', line):
                key, value = match.groups()
                attributes[key] = parse_number(value)

            for boolean_field in ["isDLCItem", "isForageable", "isGem", "isAnimalProduct", "isMeal", "isFruit", "isArtisanryItem", "isPotion"]:
                if match := re.match(fr'{boolean_field}:\s*(\d+)', line):
                    attributes[boolean_field] = int(match.group(1))

            if match := re.match(r'canSell:\s*(\d+)', line):
                attributes["canSell"] = int(match.group(1))

            if match := re.match(r'useDescription:\s*(.+)', line):
                attributes["useDescription"] = match.group(1).strip()

            if line.startswith("description:"):
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    attributes["description"] = parts[1].strip()
                else:
                    capturing_description = True
                continue

            if capturing_description:
                if line.startswith("-") or ":" in line:
                    capturing_description = False
                else:
                    description_lines.append(line)
                    continue

            if line.startswith("stats:") and not capturing_stat_buff:
                capturing_stats = True
                continue

            if capturing_stats:
                if match := re.match(r'-\s*statType:\s*(\d+)', line):
                    attributes["stats"].append({"statType": match.group(1), "value": None})
                elif match := re.match(r'value:\s*([\d.]+)', line):
                    if attributes["stats"]:
                        val = match.group(1)
                        attributes["stats"][-1]["value"] = parse_number(val)
                elif re.match(r'^\S', line):
                    capturing_stats = False

            if line.startswith("foodStat:"):
                capturing_food_stat = True
                continue

            if line.startswith("maxStats:"):
                capturing_max_stats = True
                continue

            if capturing_max_stats:
                if match := re.match(r'-\s*statType:\s*(\d+)', line):
                    attributes["maxStats"].append({"statType": match.group(1), "value": None})
                elif match := re.match(r'value:\s*([\d.]+)', line):
                    if attributes["maxStats"]:
                        val = match.group(1)
                        attributes["maxStats"][-1]["value"] = parse_number(val)
                elif re.match(r'^\S', line):
                    capturing_max_stats = False

            if capturing_food_stat:
                if match := re.match(r'increase:\s*([\d.]+)', line):
                    val = match.group(1)
                    attributes["foodStat"].append({"increase": parse_number(val), "stat": None})
                elif match := re.match(r'stat:\s*(\d+)', line):
                    if attributes["foodStat"]:
                        attributes["foodStat"][-1]["stat"] = int(match.group(1))
                elif re.match(r'^\S', line):
                    capturing_food_stat = False

            if line.startswith("statBuff:"):
                capturing_stat_buff = True
                capturing_stat_buff_stats = False
                stat_buff_duration = None
                continue

            if capturing_stat_buff:
                if line.strip() == "stats:":
                    capturing_stat_buff_stats = True
                    continue

                if match := re.match(r'duration:\s*([\d.]+)', line):
                    val = match.group(1)
                    stat_buff_duration = parse_number(val)

                elif capturing_stat_buff_stats:
                    if match := re.match(r'-\s*statType:\s*(\d+)', line):
                        attributes["statBuff"].append({"statType": match.group(1), "value": None, "duration": stat_buff_duration})
                    elif match := re.match(r'value:\s*([\d.]+)', line):
                        if attributes["statBuff"]:
                            val = match.group(1)
                            attributes["statBuff"][-1]["value"] = parse_number(val)
                    elif re.match(r'^\S', line):
                        capturing_stat_buff_stats = False

                elif re.match(r'^\S', line):
                    capturing_stat_buff = False

            if re.match(r'^\s*cropStages:\s*$', line):
                capturing_crop_stages = True
                crop_stages = []
                continue

            if capturing_crop_stages:
                if match := re.match(r'^\s*-\s*daysToGrow:\s*([\d.]+)', line):
                    val = match.group(1)
                    crop_stages.append({"daysToGrow": parse_number(val), "guid": None})
                elif match := re.match(r'sprite:.*guid:\s*([\da-f]+)', line):
                    if crop_stages:
                        crop_stages[-1]["guid"] = match.group(1)
                elif re.match(r'^\S', line):
                    capturing_crop_stages = False

            if re.match(r'^\s*seasons:\s*$', line):
                capturing_seasons = True
                seasons_list = []
                continue

            if capturing_seasons:
                if match := re.match(r'^\s*-\s*(\d+)', line):
                    seasons_list.append(match.group(1))
                elif re.match(r'^\s*\S', line):
                    capturing_seasons = False

        if seasons_list:
            attributes["seasons"] = "; ".join(seasons_list)
        if crop_stages:
            attributes["cropStages"] = crop_stages
        if description_lines:
            attributes["description"] = " ".join(description_lines).strip()

    except Exception as e:
        attributes["error"] = str(e)

    return attributes

def extract_prefab_attributes(prefab_file):
    try:
        lines = file_utils.read_file_lines(prefab_file)
    except Exception as e:
        logging.warning(f"Failed to read prefab file {prefab_file}: {e}")
        return {}

    def get_bool(line):
        return line.endswith("1")

    data = {}
    rotate_keys = ["southDecoration", "eastDecoration", "northDecoration", "westDecoration"]
    rotate_count = 0

    for line in lines:
        line = line.strip()
        if match := re.match(r"(pickaxeable|axeable|placeableOnTables|placeableOnWalls|placeableAsRug|placeableInWater):\s*(\d)", line):
            key, val = match.groups()
            data[key] = int(val)
        elif any(k in line for k in rotate_keys):
            rotate_count += 1

    if rotate_count >= 2:
        data["canRotate"] = True

    return data

def extract_stat_buff(lines):
    def parse_number(val):
        return float(val) if '.' in val else int(val)

    capturing_stat_buff = False
    capturing_stats = False
    duration = None
    current_stat = None
    buff_stats = []
    inside_stat_buff = False

    for line in lines:
        line = line.strip()
        logging.debug(f"[statBuff scan] Line: {line}")

        if line.startswith("statBuff:"):
            capturing_stat_buff = True
            inside_stat_buff = True
            logging.debug("--> Found statBuff block")
            continue

        if capturing_stat_buff:
            if line.startswith("stats:"):
                capturing_stats = True
                logging.debug("--> Entering stats section inside statBuff")
                continue

            if match := re.match(r'duration:\s*([\d.]+)', line):
                duration = parse_number(match.group(1))
                logging.debug(f"--> Captured duration: {duration}")
                for entry in buff_stats:
                    if entry.get("duration") is None:
                        entry["duration"] = duration

            if capturing_stats:
                if match := re.match(r'-\s*statType:\s*(\d+)', line):
                    current_stat = {"statType": match.group(1), "value": None, "duration": None}
                    buff_stats.append(current_stat)
                    logging.debug(f"--> New stat entry: {current_stat}")
                elif match := re.match(r'value:\s*([\d.]+)', line):
                    if current_stat:
                        current_stat["value"] = parse_number(match.group(1))
                        logging.debug(f"--> Updated value for stat: {current_stat}")
                elif re.match(r'^\S', line):
                    capturing_stats = False
                    capturing_stat_buff = False
                    logging.debug("--> Leaving statBuff block")

    logging.debug(f"Final statBuff collected: {buff_stats}")
    return buff_stats

def generate_item_data():
    logging.info("Starting item data extraction...")
    prefab_files = [f for f in os.listdir(gamedata_directory) if f.endswith(".prefab")]
    prefab_lookup = {os.path.splitext(f)[0]: os.path.join(gamedata_directory, f) for f in prefab_files}
    display_names = get_display_names(en_display_name_file)
    logging.info(f"Loaded {len(display_names)} display names.")
    all_items = {}

    files = [f for f in os.listdir(monobehaviour_directory) if f.endswith(".asset")]
    total = len(files)
    step = max(1, total // 5)

    from item_list import extract_attributes, extract_stat_buff

    for idx, filename in enumerate(files):
        if idx % step == 0:
            print(f"  🔄 {floor((idx / total) * 100)}% complete...")

        asset_path = os.path.join(monobehaviour_directory, filename)
        item_id, item_name = extract_item_info(asset_path)
        if not item_id or not item_name:
            continue
        if should_exclude_item(item_name):
            continue

        key_display = extract_key_display_name(asset_path)
        display_name = display_names.get(key_display, item_name)

        attributes = extract_attributes(asset_path)
        
        prefab_path = prefab_lookup.get(item_name)
        if prefab_path:
            prefab_data = extract_prefab_attributes(prefab_path)
            attributes.update(prefab_data)
        else:
            logging.debug(f"No prefab match for {item_name}")

        icon_guid = extract_icon_guid(asset_path)
        if icon_guid:
            attributes["iconGUID"] = icon_guid

        stat_buff = extract_stat_buff(file_utils.read_file_lines(asset_path))
        if stat_buff:
            attributes["statBuff"] = stat_buff
            original_stats = attributes.get("stats", [])
            filtered_stats = [s for s in original_stats if not any(sb["statType"] == s["statType"] for sb in stat_buff)]
            attributes["stats"] = filtered_stats

        attributes = {
            "assetName": item_name,
            "Name": display_name,
            "GUID": extract_guid(asset_path + ".meta"),
            **attributes
        }
        attributes["ID"] = item_id
        all_items[display_name] = attributes

    json_utils.write_json(all_items, os.path.join(output_directory, output_file), indent=4)
    logging.info(f"✅ Successfully wrote {len(all_items)} items to {output_file}")

if __name__ == "__main__":
    generate_item_data()