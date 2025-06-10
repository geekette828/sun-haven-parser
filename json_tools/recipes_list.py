import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils, json_utils
from utils.recipe_utils import normalize_workbench

# Define paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
recipes_json_path = os.path.join(output_directory, "recipes_data.json")
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "json", "recipe_list_debug.txt")

file_utils.ensure_dir_exists(output_directory)
def extract_guid(meta_file_path):
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

        if "hoursToCraft:" in line:
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

def normalize_workbench_camel_case(wb):
    wb = re.sub(r"[^a-zA-Z0-9 ]", "", wb)
    parts = wb.strip().split()
    return parts[0].lower() + ''.join(p.capitalize() for p in parts[1:]) if parts else "unknownWorkbench"

def camel_case(text):
    parts = re.sub(r"[^a-zA-Z0-9 ]", "", text).strip().split()
    return parts[0].lower() + ''.join(p.capitalize() for p in parts[1:]) if parts else "unknown"

def extract_disambiguation(filename):
    match = re.search(r"\(([^)]+)\)\.asset$", filename)
    return camel_case(match.group(1)) if match else None

def generate_base_recipe_id(parsed_id, workbench_name, output_id):
    return f"{parsed_id}_{normalize_workbench_camel_case(workbench_name)}_{output_id}"

# Build recipe data
raw_recipes = {}
for filename in os.listdir(input_directory):
    if filename.lower().startswith("recipe") and filename.endswith(".asset"):
        asset_path = os.path.join(input_directory, filename)
        meta_path = asset_path + ".meta"

        recipe_info = parse_recipe_asset(asset_path)
        if os.path.exists(meta_path):
            recipe_info["guid"] = extract_guid(meta_path)

        id_match = re.search(r"[Rr]ecipe\s+(\d+)", filename)
        parsed_id = int(id_match.group(1)) if id_match else 0
        recipe_info["parsedRecipeID"] = parsed_id
        raw_recipes[filename] = recipe_info

# Map multiple workbenches to GUIDs
guid_to_workbenches = defaultdict(set)
for filename in os.listdir(input_directory):
    m = re.match(r"^RecipeList[_ ]+(.+)\.asset$", filename)
    if not m:
        continue
    workbench = normalize_workbench(m.group(1))
    path = os.path.join(input_directory, filename)
    for line in file_utils.read_file_lines(path):
        match = re.search(r'guid: ([\w-]+)', line)
        if match:
            guid_to_workbenches[match.group(1)].add(workbench)

# Assign recipes per workbench
final_recipes = {}
recipe_id_tracker = defaultdict(list)

for name, data in raw_recipes.items():
    guid = data.get("guid")
    workbenches = guid_to_workbenches.get(guid, set())

    if not workbenches:
        output_name = data.get("output", {}).get("name", "")
        if " Jam" in output_name:
            debug_lines = []
            debug_lines.append(f"[INFERRED] {name} Assigned workbench: Jam Maker")
            with open(debug_log_path, "a", encoding="utf-8") as log:
                log.write("\n".join(debug_lines) + "\n")
            workbenches.add("Jam Maker")
        else:
            workbenches.add("Unknown Workbench")

    for wb in workbenches:
        data_copy = dict(data)
        data_copy["workbench"] = wb
        output_id = data.get("output", {}).get("id", "unknown")
        base_id = generate_base_recipe_id(data["parsedRecipeID"], wb, output_id)

        inputs_signature = tuple((i["id"], i["amount"]) for i in data.get("inputs", []))
        existing_signatures = recipe_id_tracker[base_id]

        if inputs_signature in existing_signatures:
            recipe_id = base_id
        else:
            if existing_signatures:
                dis = extract_disambiguation(name)
                if dis:
                    recipe_id = f"{base_id}_{dis}"
                else:
                    recipe_id = f"{base_id}_{len(existing_signatures)+1}"
            else:
                recipe_id = base_id

            recipe_id_tracker[base_id].append(inputs_signature)

        data_copy["recipeID"] = recipe_id
        key = recipe_id
        data_copy["sourceFile"] = name
        final_recipes[recipe_id] = data_copy


# Write to JSON
json_utils.write_json(final_recipes, recipes_json_path, indent=4)
print("✅ Recipe data extraction completed with unique, stable recipeIDs.")
