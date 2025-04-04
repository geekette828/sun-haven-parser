import os
import re
import config.constants as constants
from utils import file_utils, json_utils

# Define paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
file_utils.ensure_dir_exists(output_directory)

# Define output file
shops_json_path = os.path.join(output_directory, "shop_data.json")

def extract_guid(meta_file_path):
    if os.path.exists(meta_file_path):
        lines = file_utils.read_file_lines(meta_file_path, encoding="utf-8")
        for line in lines:
            match = re.match(r"guid:\s*(\S+)", line)
            if match:
                return match.group(1)
    return None

def parse_asset_file(asset_path):
    shop_data = {
        "file_name": os.path.basename(asset_path),
        "shop_name": os.path.basename(asset_path).replace("MerchantTable", "").replace(".asset", "").strip("_"),
        "guid": extract_guid(asset_path + ".meta"),
        "starting_items": [],
        "random_items": []
    }

    lines = file_utils.read_file_lines(asset_path, encoding="utf-8")
    current_section = None
    item = {}
    for line in lines:
        line = line.strip()
        if line.startswith("startingItems2:"):
            current_section = "starting"
            continue
        elif line.startswith("randomShopItems2:"):
            current_section = "random"
            continue
        elif re.match(r"-\s*id:", line):
            if "id" in item:
                if current_section == "starting":
                    shop_data["starting_items"].append(item)
                elif current_section == "random":
                    shop_data["random_items"].append(item)
            item = {}
        
        match = re.match(r"(?:-\s*)?(id|price|orbs|tickets|isLimited|qty|resetDay|chance|saleItem):\s*(.*)", line)
        if match:
            key, value = match.groups()
            if value.isdigit():
                value = int(value)
            item[key] = value
        elif "itemToUseAsCurrency:" in line:
            guid_match = re.search(r"guid:\s*([a-f0-9]+)", line)
            item["itemToUseAsCurrency"] = guid_match.group(1) if guid_match else None

    if "id" in item:
        if current_section == "starting":
            shop_data["starting_items"].append(item)
        elif current_section == "random":
            shop_data["random_items"].append(item)
    
    return shop_data

# Gather all MerchantTable.asset files
shop_list = []
for file_name in os.listdir(input_directory):
    if file_name.endswith(".asset") and "MerchantTable" in file_name:
        file_path = os.path.join(input_directory, file_name)
        shop_data = parse_asset_file(file_path)
        shop_list.append(shop_data)

# Write to JSON if data exists
if shop_list:
    json_utils.write_json(shop_list, shops_json_path, indent=4)
    print(f"Shop JSON data saved to {shops_json_path}")
else:
    print("No valid shop data found. JSON file was not created.")
