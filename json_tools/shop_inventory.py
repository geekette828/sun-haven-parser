import os
import sys
import re
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants

# Define paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
shops_json_path = os.path.join(output_directory, "shop_data.json")

os.makedirs(output_directory, exist_ok=True)

EDGE_CASE_SHOP_NAMES = [
    "MythsAndMusesMerchat"
]

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
    base = os.path.basename(asset_path).replace(".asset", "")
    # remove "...MerchantTable" or plain "...Table" suffixes
    clean = re.sub(r'(?:Merchant)?Table$', '', base, flags=re.IGNORECASE)

    shop_data = {
        "file_name": os.path.basename(asset_path),
        "shop_name": clean.strip("_"),
        "guid": extract_guid(asset_path + ".meta"),
        "starting_items": [],
        "random_items": []
    }

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

# Gather all relevant .asset files
shop_list = []
for file_name in os.listdir(input_directory):
    if not file_name.endswith(".asset"):
        continue

    lower = file_name.lower()

    is_merchant_like = ("merchant" in lower and not file_name[0].isdigit())
    is_generalstore = "generalstore" in lower

    if is_merchant_like or is_generalstore or any(file_name.startswith(edge) for edge in EDGE_CASE_SHOP_NAMES):
        file_path = os.path.join(input_directory, file_name)
        shop_data = parse_asset_file(file_path)
        shop_list.append(shop_data)

# Write to JSON if data exists
if shop_list:
    with open(shops_json_path, "w", encoding="utf-8") as json_file:
        json.dump(shop_list, json_file, indent=4)
    print(f"Shop JSON data saved to {shops_json_path}")
else:
    print("No valid shop data found. JSON file was not created.")
