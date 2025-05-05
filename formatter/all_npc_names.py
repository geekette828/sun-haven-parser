import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils, text_utils

# Define input and output paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "TextAsset")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted")
file_utils.ensure_dir_exists(output_directory)

# Output files
output_file_path = os.path.join(output_directory, "npc_list.txt")
debug_log_path = os.path.join(".hidden", "debug_output", "npc_list_debug.txt")
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

def extract_npc_names(directory):
    npc_names = set()
    for filename in os.listdir(directory):
        if not filename.endswith(".txt"):
            continue
        if " " not in filename:
            file_utils.write_debug_log(f"[SKIP] No space: {filename}", debug_log_path)
            continue
        name = filename.split(" ")[0].strip()
        if name:
            npc_names.add(name)
    return sorted(npc_names)

# Extract and save
npc_list = extract_npc_names(input_directory)
file_utils.write_lines(output_file_path, [name + '\n' for name in npc_list])

print(f"✅ Extracted {len(npc_list)} unique NPCs.")
print(f"📝 Debug log saved to: {debug_log_path}")