import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils import file_utils

# Define paths
en_text_file = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Module_Map_Description.txt")
file_utils.ensure_dir_exists(os.path.dirname(output_file))

lines = file_utils.read_file_lines(en_text_file)

output_lines = []
seen_keys = set()
i = 0
while i < len(lines):
    line = lines[i].strip()

    match_desc = re.match(r"- Term: (.+)\.(Description,Map|Description\.Map)$", line, re.IGNORECASE)
    match_map = re.match(r"- Term: (.+)\.Map$", line, re.IGNORECASE)

    key = None
    if match_desc:
        base_key = match_desc.group(1)
    elif match_map:
        base_key = match_map.group(1)
    else:
        i += 1
        continue

    # Detect region suffix
    region_prefix = ""
    if base_key.lower().endswith(".nv"):
        region_prefix = "Nel'Vari "
        base_key = base_key[:-3]  # Remove '.NV'
    elif base_key.lower().endswith(".wg"):
        region_prefix = "Withergate "
        base_key = base_key[:-3]  # Remove '.WG'

    # Normalize key: insert spaces between camelCase words
    formatted_key = re.sub(r"([a-z])([A-Z])", r"\1 \2", base_key)
    formatted_key = region_prefix + formatted_key.strip()

    if formatted_key in seen_keys:
        i += 1
        continue
    seen_keys.add(formatted_key)

    # Advance to the Languages section
    while i < len(lines) and not lines[i].strip().startswith("Languages:"):
        i += 1

    i += 1  # Move to line after "Languages:"
    if i < len(lines) and lines[i].strip().startswith("-"):
        description = lines[i].strip()[1:].strip()

        # Clean description
        description = description.replace('"', '').replace("\\n", "<br>").replace("\n", "")
        description = re.sub(r"<color=[^>]*>", "", description)
        description = description.replace("</color>", "")
        description = re.sub(r"<sprite=[^>]*>", "", description)
        description = re.sub(r"</?\w+[^>]*>", "", description)  # Strip all HTML-style tags

        output_lines.append(f"{formatted_key} = {description}\n")

    i += 1

file_utils.write_lines(output_file, output_lines)
print(f"Descriptions written to: {output_file}")
