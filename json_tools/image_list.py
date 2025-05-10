import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import json_utils, file_utils

# Define paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "Sprite")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
output_file = os.path.join(output_directory, "images_data.json")

file_utils.ensure_dir_exists(output_directory)

# Get all .meta files in the input directory
meta_files = [f for f in os.listdir(input_directory) if f.endswith(".meta")]
total_files = len(meta_files)

# Output dictionary (GUID as key)
output_data = {}

# Process each .meta file
for index, filename in enumerate(meta_files, start=1):
    file_path = os.path.join(input_directory, filename)
    
    try:
        lines = file_utils.read_file_lines(file_path)
        guid = None
        for line in lines:
            if line.strip().startswith("guid:"):
                guid = line.strip().split("guid:")[1].strip()
                break
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        continue

    if guid:
        base_name = filename.replace(".asset.meta", "")
        output_data[guid] = {
            "file": base_name,
            "image": f"{base_name}.png"
        }
    
    # Progress update every 10%
    if total_files > 0 and index % (total_files // 10 or 1) == 0:
        progress = (index / total_files) * 100
        print(f"Progress: {progress:.0f}% ({index}/{total_files} files processed)")

# Write output using json_utils
json_utils.write_json(output_data, output_file, indent=4)

print(f"Finished! {len(output_data)} entries saved to {output_file}")
