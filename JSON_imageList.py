import os
import json
import config

# Define paths
input_directory = os.path.join(config.INPUT_DIRECTORY, "Sprite")
output_directory = os.path.join(config.OUTPUT_DIRECTORY, "JSON Data")
output_file = os.path.join(output_directory, "images_data.json")

# Ensure output directory exists
os.makedirs(output_directory, exist_ok=True)

# Get only the first 10 .meta files
meta_files = [f for f in os.listdir(input_directory) if f.endswith(".meta")]
total_files = len(meta_files)

# Output dictionary (GUID as key)
output_data = {}

# Process each .meta file
for index, filename in enumerate(meta_files, start=1):
    file_path = os.path.join(input_directory, filename)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("guid:"):
                    guid = line.strip().split("guid:")[1].strip()
                    break
            else:
                guid = None

        if guid:
            base_name = filename.replace(".asset.meta", "")
            output_data[guid] = {
                "file": base_name,
                "image": f"{base_name}.png"
            }

    except Exception as e:
        print(f"Error reading {filename}: {e}")

    # Progress update every 10%
    if total_files > 0 and index % (total_files // 10 or 1) == 0:
        progress = (index / total_files) * 100
        print(f"Progress: {progress:.0f}% ({index}/{total_files} files processed)")

# Write output
with open(output_file, "w", encoding="utf-8") as out:
    json.dump(output_data, out, indent=4)

print(f"Finished! {len(output_data)} entries saved to {output_file}")
