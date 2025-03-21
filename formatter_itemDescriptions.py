import os
import json
import re
import config

# Define paths
input_directory = os.path.join(config.OUTPUT_DIRECTORY, "JSON Data")
output_directory = os.path.join(config.OUTPUT_DIRECTORY, "Wiki Formatted")
os.makedirs(output_directory, exist_ok=True)

input_file_path = os.path.join(input_directory, "items_data.json")
output_file_path = os.path.join(output_directory, "item_descriptions.txt")

# Read JSON data
with open(input_file_path, "r", encoding="utf-8") as file:
    data = json.load(file)

# Organize descriptions alphabetically, merging similar ones
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

# Write output to file
with open(output_file_path, "w", encoding="utf-8") as file:
    file.write(lua_script)

# Print final success message (NO extra terminal spam)
print(f"Lua script generated successfully: {output_file_path}")
