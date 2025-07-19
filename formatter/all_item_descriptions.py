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
output_file_path = os.path.join(output_directory, "Module_Description.txt")

# Read JSON data using json_utils
data = json_utils.load_json(input_file_path)

# Organize descriptions alphabetically, merging similar ones
descriptions = {}
seen_keys = set()  # Set of simplified names we've already added

for item, details in data.items():
    name = details.get("Name", "").lower().replace("_", " ")
    description = details.get("description", "")

    if not name or not description:
        continue  # Skip entries without name or description

    # Scrub description: Remove unwanted formatting
    description = description.replace("\\", "").replace("\n", "<br>").replace('"', "")
    description = re.sub(r"<color=[^>]*>", "", description)
    description = description.replace("</color>", "")
    description = re.sub(r"<sprite=[^>]*>", "", description)

    # Normalize item name: remove (Color), trailing numbers, extra whitespace
    simplified_name = re.sub(r"\s?\(.*?\)$", "", name)  # Remove (Green), (Blue), etc.
    simplified_name = re.sub(r"\s\d+$", "", simplified_name)  # Remove "Chair 1", "Chair 101"
    simplified_name = simplified_name.strip()

    # Only add if this simplified name hasn't been seen yet
    if simplified_name in seen_keys:
        continue

    seen_keys.add(simplified_name)

    first_letter = simplified_name[0].lower()
    if first_letter not in descriptions:
        descriptions[first_letter] = {}

    descriptions[first_letter][simplified_name] = description

# Add hardcoded aliases (after all items are added)
alias_map = {
    "sprinkles": "blueberry sprinkles",
    "shiver": "black shiver",
    "kitty (pet)": "black kitty",
    "cape": "black cape"
}

for alias, original in alias_map.items():
    original_key = original.lower()
    alias_key = alias.lower()
    orig_letter = original_key[0]
    alias_letter = alias_key[0]

    if orig_letter in descriptions and original_key in descriptions[orig_letter]:
        desc = descriptions[orig_letter][original_key]

        if alias_letter not in descriptions:
            descriptions[alias_letter] = {}

        descriptions[alias_letter][alias_key] = desc

# Generate Lua script output
lua_script = """local p = {}
local lib = require('Module:Feature')

function p.main(frame)
    local args = require('Module:Arguments').getArgs(frame, {
        parentFirst = true,
        wrapper = { 'Template:Description' }
    })

    return p.get_description(args[1] or mw.title.getCurrentTitle().rootText)
end

function p.get_description(item_name)
    local lowercase_name = string.lower(item_name):gsub("_", " ")
    local first_letter = string.sub(lowercase_name, 1, 1)
    
    local description = p.descriptions()[first_letter] and p.descriptions()[first_letter][lowercase_name]
    if description ~= nil then
        return description
    else
        return "Edit in https://sunhaven.wiki.gg/wiki/Module:Description"
    end
end

function p.descriptions()
    return {
"""

for letter, items in sorted(descriptions.items()):
    lua_script += f'    ["{letter}"] = {{\n'
    for item, desc in sorted(items.items()):
        lua_script += f'        ["{item}"] = "{desc}",\n'
    lua_script += "    },\n"

lua_script += """    }
end
return p
"""

# Write output to file using file_utils
file_utils.write_lines(output_file_path, [lua_script])

# Print final success message (NO extra terminal spam)
print(f"Lua script generated successfully: {output_file_path}")
