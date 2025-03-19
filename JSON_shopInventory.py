import os
import json
import re
import config

# Define paths
input_directory = os.path.join(config.INPUT_DIRECTORY, "MonoBehaviour")
output_directory = os.path.join(config.OUTPUT_DIRECTORY, "JSON Data")
os.makedirs(output_directory, exist_ok=True)

# Define output file
shops_json_path = os.path.join(output_directory, "shop_data.json")

# Function to extract GUID from .meta file
def extract_guid(meta_file_path):
    if os.path.exists(meta_file_path):
        with open(meta_file_path, "r", encoding="utf-8", errors="ignore") as meta_file:
            for line in meta_file:
                match = re.match(r"guid:\s*(\S+)", line)
                if match:
                    return match.group(1)
    return None

# Function to parse asset file
def parse_asset_file(asset_path):
    shop_data = {
        "file_name": os.path.basename(asset_path),
        "shop_name": os.path.basename(asset_path).replace("MerchantTable", "").replace(".asset", "").strip("_"),
        "guid": extract_guid(asset_path + ".meta"),
        "starting_items": [],
        "random_items": []
    }
    
    # Read asset file
    with open(asset_path, "r", encoding="utf-8", errors="ignore") as asset_file:
        lines = asset_file.readlines()
    
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
            if "id" in item:  # Ensure we capture full items before resetting
                if current_section == "starting":
                    shop_data["starting_items"].append(item)
                elif current_section == "random":
                    shop_data["random_items"].append(item)
            item = {}  # Start a new item
        
        match = re.match(r"(?:-\s*)?(id|price|orbs|tickets|isLimited|qty|resetDay|itemToUseAsCurrency|chance|saleItem):\s*(.*)", line)
        if match:
            key, value = match.groups()
            if value.isdigit():
                value = int(value)
            item[key] = value
    
    # Ensure the last item is appended
    if "id" in item:
        if current_section == "starting":
            shop_data["starting_items"].append(item)
        elif current_section == "random":
            shop_data["random_items"].append(item)
    
    return shop_data

# Find all MerchantTable asset files
shop_list = []
for file_name in os.listdir(input_directory):
    if "MerchantTable" in file_name and file_name.endswith(".asset"):
        file_path = os.path.join(input_directory, file_name)
        shop_data = parse_asset_file(file_path)
        shop_list.append(shop_data)

# Ensure data is not empty before writing JSON
if shop_list:
    with open(shops_json_path, "w", encoding="utf-8") as json_file:
        json.dump(shop_list, json_file, indent=4)
    print(f"Shop JSON data saved to {shops_json_path}")
else:
    print("No valid shop data found. JSON file was not created.")
