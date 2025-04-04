import os
import json
import re
import config.constants as constants

# Construct full paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
output_file = "items_data.json"

# Ensure the output directory exists
os.makedirs(output_directory, exist_ok=True)

def extract_guid(meta_file):
    """Extracts GUID from .meta files."""
    with open(meta_file, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'guid:\s*([a-f0-9]+)', content)
    return match.group(1) if match else None

def extract_icon_guid(asset_file):
    """Extracts the icon GUID from .asset files."""
    try:
        with open(asset_file, 'r', encoding='utf-8') as f:
            content = f.readlines()

        for line in content:
            match = re.match(r'icon:\s*{fileID:\s*\d+,\s*guid:\s*([\da-f]+),', line.strip())
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error reading {asset_file}: {e}")
    return None

def extract_item_info(asset_file):
    """Extracts item ID and name from .asset file name."""
    match = re.match(r"(\d+)\s+-\s+(.+)\.asset", os.path.basename(asset_file))
    if match:
        return int(match.group(1)), match.group(2)  # Return both ID (as int) and Name
    return None, None

def should_exclude_item(item_name):
    """Checks if an item should be excluded based on naming patterns."""
    exclude_patterns = [
        "minerock", "ore node", "hiddenchest", "recurringchest", "onetimechest", "sombasu's fortune"
    ]
    return any(pattern in item_name.lower() for pattern in exclude_patterns)

def extract_attributes(asset_file):
    """Extracts relevant attributes from the .asset file."""
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
        "foodStat": [],
        "cropStages": [],
        "seasons": None,
        "iconGUID": None
    }

    try:
        with open(asset_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        capturing_description = False
        capturing_stats = False
        capturing_food_stat = False
        capturing_seasons = False
        capturing_crop_stages = False
        description_lines = []
        seasons_list = []
        crop_stages = []

        for line in lines:
            line = line.strip()

            if match := re.match(r'^(health|mana|requiredLevel|stackSize|sellPrice|orbsSellPrice|ticketSellPrice|rarity|hearts|decorationType|hasSetSeason|setSeason|experience):\s*(\d+)', line):
                key, value = match.groups()
                attributes[key] = int(value)

            for boolean_field in ["isDLCItem", "isForageable", "isGem", "isAnimalProduct", "isFruit", "isArtisanryItem", "isPotion"]:
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

            if line.startswith("stats:"):
                capturing_stats = True
                continue

            if capturing_stats:
                if match := re.match(r'-\s*statType:\s*(\d+)', line):
                    attributes["stats"].append({"statType": match.group(1), "value": None})
                elif match := re.match(r'value:\s*(\d+)', line):
                    if attributes["stats"]:
                        attributes["stats"][-1]["value"] = int(match.group(1))
                elif re.match(r'^\S', line):
                    capturing_stats = False

            if line.startswith("foodStat:"):
                capturing_food_stat = True
                continue

            if capturing_food_stat:
                if match := re.match(r'increase:\s*(\d+)', line):
                    attributes["foodStat"].append({"increase": match.group(1), "stat": None})
                elif match := re.match(r'stat:\s*(\d+)', line):
                    if attributes["foodStat"]:
                        attributes["foodStat"][-1]["stat"] = int(match.group(1))
                elif re.match(r'^\S', line):
                    capturing_food_stat = False

            if re.match(r'^\s*cropStages:\s*$', line):
                capturing_crop_stages = True
                crop_stages = []
                continue

            if capturing_crop_stages:
                if match := re.match(r'^\s*-\s*daysToGrow:\s*(\d+)', line):
                    crop_stages.append({"daysToGrow": int(match.group(1)), "guid": None})
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

def generate_item_data():
    """Scans the input directory, extracts item names, GUIDs, and attributes, and saves them to a JSON file."""
    items_data = {}

    for file in os.listdir(input_directory):
        if file.endswith(".asset.meta"):
            asset_file = os.path.join(input_directory, file.replace(".meta", ""))
            meta_file = os.path.join(input_directory, file)

            if os.path.exists(asset_file):
                item_id, item_name = extract_item_info(asset_file)
                if item_name is None or should_exclude_item(item_name):
                    continue

                guid = extract_guid(meta_file)
                icon_guid = extract_icon_guid(asset_file)
                attributes = extract_attributes(asset_file)
                attributes["ID"] = item_id
                attributes["iconGUID"] = icon_guid

                if item_name and guid:
                    items_data[item_name] = {"Name": item_name, "GUID": guid, **attributes}

    output_path = os.path.join(output_directory, output_file)
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(items_data, json_file, indent=4)

    print(f"JSON data saved to {output_path}")

if __name__ == "__main__":
    generate_item_data()
