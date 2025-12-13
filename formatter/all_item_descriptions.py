import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils import json_utils, file_utils

# Define paths
input_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted")
file_utils.ensure_dir_exists(output_directory)

input_file_path = os.path.join(input_directory, "items_data.json")

# This is the file you'll paste into Module:Description/data
output_file_path = os.path.join(output_directory, "Module_Description_data.txt")

# Read JSON data using json_utils
data = json_utils.load_json(input_file_path)

# Organize descriptions in a flat map: simplified_name -> description
descriptions = {}
seen_keys = set()  # Set of simplified names we've already added

for item, details in data.items():
    name = details.get("Name", "")
    description = details.get("description", "")

    if not name or not description:
        continue  # Skip entries without name or description

    # Normalize base name: lowercase + underscores -> spaces
    name = name.lower().replace("_", " ")

    # Scrub description: Remove unwanted formatting
    description = description.replace("\\", "")
    description = description.replace("\n", "<br>")
    description = description.replace('"', "")
    description = re.sub(r"<color=[^>]*>", "", description)
    description = description.replace("</color>", "")
    description = re.sub(r"<sprite=[^>]*>", "", description)

    # Normalize item name: remove (Color), trailing numbers, extra whitespace
    simplified_name = re.sub(r"\s?\(.*?\)$", "", name)  # Remove (Green), (Blue), etc.
    simplified_name = re.sub(r"\s\d+$", "", simplified_name)  # Remove "Chair 1", "Chair 101"
    simplified_name = simplified_name.strip()

    if not simplified_name:
        continue

    # Only add if this simplified name hasn't been seen yet
    if simplified_name in seen_keys:
        continue

    seen_keys.add(simplified_name)
    descriptions[simplified_name] = description

# Add hardcoded aliases (after all items are added)
alias_map = {
    "sprinkles": "blueberry sprinkles",
    "shiver": "black shiver",
    "kitty (pet)": "black kitty",
    "cape": "black cape",
}

for alias, original in alias_map.items():
    original_key = original.lower()
    alias_key = alias.lower()

    if original_key in descriptions:
        descriptions[alias_key] = descriptions[original_key]

# Generate Lua /data module output
lua_lines = []
lua_lines.append("local data = {\n")

for item, desc in sorted(descriptions.items()):
    # Keys/descriptions are already scrubbed of quotes; just be safe with backslashes
    safe_item = item.replace("\\", "")
    safe_desc = desc.replace("\\", "")

    lua_lines.append(f'    ["{safe_item}"] = "{safe_desc}",\n')

lua_lines.append("}\n\nreturn data\n")

# Write output to file using file_utils
file_utils.write_lines(output_file_path, lua_lines)

# Print final success message (NO extra terminal spam)
print(f"Lua /data module generated successfully: {output_file_path}")
