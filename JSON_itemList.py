import os
import json
import re
import config

# Construct full paths
input_directory = os.path.join(config.INPUT_DIRECTORY, "MonoBehaviour")
output_directory = os.path.join(config.OUTPUT_DIRECTORY, "JSON Data")
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
        description_lines = []
        seasons_list = []
        crop_stages = []

        for line in lines:
            line = line.strip()

            # Extract numeric attributes
            if match := re.match(r'^(health|mana|requiredLevel|stackSize|sellPrice|orbsSellPrice|ticketSellPrice|rarity|hearts|decorationType|setSeason|experience):\s*(\d+)', line):
                key, value = match.groups()
                attributes[key] = int(value)

            # Extract boolean attributes
            for boolean_field in ["isDLCItem", "isForageable", "isGem", "isAnimalProduct", "isFruit", "isArtisanryItem", "isPotion"]:
                if match := re.match(fr'{boolean_field}:\s*(\d+)', line):
                    attributes[boolean_field] = int(match.group(1))

            # Extract canSell
            if match := re.match(r'canSell:\s*(\d+)', line):
                attributes["canSell"] = int(match.group(1))

            # Extract useDescription
            if match := re.match(r'useDescription:\s*(.+)', line):
                attributes["useDescription"] = match.group(1).strip()

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
    
    # Save JSON output
    output_path = os.path.join(output_directory, output_file)
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(items_data, json_file, indent=4)
    
    print(f"JSON data saved to {output_path}")

if __name__ == "__main__":
    generate_item_data()