import os
import json
import re
import config

# Construct full paths
input_directory = os.path.join(config.INPUT_DIRECTORY, "MonoBehaviour")
output_directory = os.path.join(config.OUTPUT_DIRECTORY, "JSON Data")

# Ensure the output directory exists
os.makedirs(output_directory, exist_ok=True)

# Get all .asset files in the input directory
all_assets = [f for f in os.listdir(input_directory) if f.endswith(".asset")]

# Function to exclude unwanted items
def should_exclude_item(item_name):
    exclude_patterns = [
        "minerock", "ore node", "hiddenchest", "recurringchest", "onetimechest", "sombasu's fortune"
    ]
    return any(pattern in item_name.lower() for pattern in exclude_patterns)

# Function to extract GUID from .meta files
def extract_guid(meta_file):
    try:
        with open(meta_file, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'guid:\s*([a-f0-9]+)', content)
        return match.group(1) if match else None
    except Exception as e:
        print(f"Error reading {meta_file}: {e}")
        return None

# Function to extract item name from .asset filenames
def extract_item_info(asset_file):
    """Extracts item ID and name from .asset file name."""
    match = re.match(r"(\d+)\s+-\s+(.+)\.asset", os.path.basename(asset_file))
    if match:
        return int(match.group(1)), match.group(2)  # Return both ID (as int) and Name
    return None, None


# Function to extract attributes from .asset files
def extract_attributes(asset_file):
    attributes = {
        "ID": None,
        "description": None,
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
        "seasons": None
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

            # Extract numeric attributes
            if match := re.match(r'^(health|mana|requiredLevel|ID|stackSize|sellPrice|orbsSellPrice|ticketSellPrice|rarity|hearts|decorationType|setSeason|experience):\s*(\d+)', line):
                key, value = match.groups()
                attributes[key] = int(value)

            # Extract boolean attributes
            for boolean_field in ["isDLCItem", "isForageable", "isGem", "isAnimalProduct", "isFruit", "isArtisanryItem", "isPotion"]:
                if match := re.match(fr'{boolean_field}:\s*(\d+)', line):
                    attributes[boolean_field] = int(match.group(1))

            # Extract canSell
            if match := re.match(r'canSell:\s*(\d+)', line):
                attributes["canSell"] = int(match.group(1))

            # Extract description (multi-line handling)
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

            # Detect start of stats list
            if line.startswith("stats:"):
                capturing_stats = True
                continue

            # Extract statType and value pairs inside stats
            if capturing_stats:
                if match := re.match(r'-\s*statType:\s*(\d+)', line):
                    stat_type = match.group(1)
                    attributes["stats"].append({"statType": stat_type, "value": None})
                elif match := re.match(r'value:\s*(\d+)', line):
                    if attributes["stats"]:
                        attributes["stats"][-1]["value"] = int(match.group(1))

            # Detect start of foodStat list
            if line.startswith("foodStat:"):
                capturing_food_stat = True
                continue

            # Extract foodStat values
            if capturing_food_stat:
                if match := re.match(r'increase:\s*(\d+)', line):
                    attributes["foodStat"].append({"increase": match.group(1), "stat": None})
                elif match := re.match(r'stat:\s*(\d+)', line):
                    if attributes["foodStat"]:
                        attributes["foodStat"][-1]["stat"] = int(match.group(1))

            # Detect start of cropStages list
            if re.match(r'^\s*cropStages:\s*$', line):
                capturing_crop_stages = True
                crop_stages = []
                continue

            # Extract cropStages values
            if capturing_crop_stages:
                if match := re.match(r'^\s*-\s*daysToGrow:\s*(\d+)', line):
                    crop_stage = {"daysToGrow": int(match.group(1)), "guid": None}
                    crop_stages.append(crop_stage)
                elif match := re.match(r'sprite:.*guid:\s*([\da-f]+)', line):
                    if crop_stages:
                        crop_stages[-1]["guid"] = match.group(1)
                elif re.match(r'^\S', line):
                    capturing_crop_stages = False

            # Detect start of seasons list
            if re.match(r'^\s*seasons:\s*$', line):
                capturing_seasons = True
                seasons_list = []
                continue

            # Extract seasons values
            if capturing_seasons:
                if match := re.match(r'^\s*-\s*(\d+)', line):
                    seasons_list.append(match.group(1))
                elif re.match(r'^\s*\S', line):
                    capturing_seasons = False

        # Format extracted values
        if seasons_list:
            attributes["seasons"] = "; ".join(seasons_list)
        if crop_stages:
            attributes["cropStages"] = crop_stages
        if description_lines:
            attributes["description"] = " ".join(description_lines).strip()

    except Exception as e:
        attributes["error"] = str(e)

    return attributes

# Process all asset files dynamically
items_data = {}

for filename in all_assets:
    asset_file = os.path.join(input_directory, filename)
    meta_file = asset_file + ".meta"

    item_id, item_name = extract_item_info(asset_file)  # Extract both ID and Name

    if item_name is None or should_exclude_item(item_name):
        continue

    guid = extract_guid(meta_file)
    attributes = extract_attributes(asset_file)

    attributes["ID"] = item_id  # Assign ID from filename

    if item_name and guid:
        items_data[item_name] = {
            "Name": item_name,
            "GUID": guid,
            **attributes
        }

# Save to JSON file
output_file = os.path.join(output_directory, "items_data.json")
with open(output_file, "w", encoding="utf-8") as json_file:
    json.dump(items_data, json_file, indent=4)

print(f"JSON data saved to {output_file}")
