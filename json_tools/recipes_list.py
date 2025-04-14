import os
import re
import config.constants as constants
from utils import file_utils, json_utils

# Define paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
file_utils.ensure_dir_exists(output_directory)

# Define output JSON file path
recipes_json_path = os.path.join(output_directory, "recipes_data.json")

def extract_guid(meta_file_path):
    """Extract GUID from a meta file."""
    try:
        lines = file_utils.read_file_lines(meta_file_path)
        for line in lines:
            match = re.search(r"guid:\s*([a-f0-9]+)", line)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error reading {meta_file_path}: {e}")
    return None

def parse_recipe_asset(file_path):
    """Parse a recipe asset file to extract recipe data."""
    recipe_data = {
        "inputs": [],
        "output": {},
        "hoursToCraft": None,
        "characterProgressTokens": None,
        "worldProgressTokens": None,
        "questProgressTokens": None,
    }

    lines = file_utils.read_file_lines(file_path)
    input_section = False
    output_section = False

    for i, line in enumerate(lines):
        line = line.strip()
        
        if line.startswith("input2:"):
            input_section = True
            output_section = False
            continue
        elif line.startswith("output2:"):
            input_section = False
            output_section = True
            continue

        elif "hoursToCraft:" in line:
            recipe_data["hoursToCraft"] = line.split(":")[-1].strip()
        elif "characterProgressTokens:" in line:
            match = re.search(r'guid: ([\w-]+)', line)
            if match:
                recipe_data["characterProgressTokens"] = match.group(1)
        elif "worldProgressTokens:" in line:
            match = re.search(r'guid: ([\w-]+)', line)
            if match:
                recipe_data["worldProgressTokens"] = match.group(1)
        elif "questProgressTokens:" in line:
            match = re.search(r'guid: ([\w-]+)', line)
            if match:
                recipe_data["questProgressTokens"] = match.group(1)
        
        elif input_section:
            if i + 1 < len(lines) and "id:" in line and "amount:" in lines[i + 1]:
                item_id = line.split(":")[-1].strip()
                amount = lines[i + 1].split(":")[-1].strip()
                name = (lines[i + 2].split(":")[-1].strip() 
                        if (i + 2 < len(lines) and "name:" in lines[i + 2]) 
                        else "Unknown")
                recipe_data["inputs"].append({"id": item_id, "amount": amount, "name": name})
            if "---" in line:
                input_section = False

        elif output_section:
            if i + 1 < len(lines) and "id:" in line and "amount:" in lines[i + 1]:
                item_id = line.split(":")[-1].strip()
                amount = lines[i + 1].split(":")[-1].strip()
                name = (lines[i + 2].split(":")[-1].strip() 
                        if (i + 2 < len(lines) and "name:" in lines[i + 2]) 
                        else "Unknown")
                recipe_data["output"] = {"id": item_id, "amount": amount, "name": name}
            if "---" in line:
                output_section = False

    return recipe_data

# Collect all recipe data
recipe_data_collection = {}
for filename in os.listdir(input_directory):
    if filename.lower().startswith("recipe") and filename.endswith(".asset"):
        asset_path = os.path.join(input_directory, filename)
        meta_path = asset_path + ".meta"
        
        recipe_info = parse_recipe_asset(asset_path)
        if os.path.exists(meta_path):
            recipe_info["guid"] = extract_guid(meta_path)
        
        recipe_data_collection[filename] = recipe_info

# Process workbench recipe lists
workbench_recipes = {}
for workbench_file in os.listdir(input_directory):
    if workbench_file.startswith("RecipeList_") and workbench_file.endswith(".asset"):
        workbench_name = workbench_file.replace("RecipeList_", "").replace(".asset", "")
        workbench_path = os.path.join(input_directory, workbench_file)
        lines = file_utils.read_file_lines(workbench_path)
        for line in lines:
            match = re.search(r'guid: ([\w-]+)', line)
            if match:
                recipe_guid = match.group(1)
                workbench_recipes[recipe_guid] = workbench_name

# Associate recipes with their workbenches
for recipe_name, recipe in recipe_data_collection.items():
    recipe_guid = recipe.get("guid")
    if recipe_guid and recipe_guid in workbench_recipes:
        recipe["workbench"] = workbench_recipes[recipe_guid]

# Save all recipe data into one JSON file using json_utils
json_utils.write_json(recipe_data_collection, recipes_json_path, indent=4)

print("Recipe data extraction completed.")
