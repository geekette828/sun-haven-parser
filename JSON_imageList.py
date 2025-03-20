import os
import json
import config

# Define paths
input_directory = os.path.join(config.INPUT_DIRECTORY, "Sprite")
output_directory = os.path.join(config.OUTPUT_DIRECTORY, "JSON Data")
output_file = os.path.join(output_directory, "images_data.json")

# Ensure output directory exists
os.makedirs(output_directory, exist_ok=True)

# Get the list of JSON files
json_files = [f for f in os.listdir(input_directory) if f.endswith(".json")]
total_files = len(json_files)

# Dictionary to store image name to GUID mapping
image_data = {}

# Process JSON files
for index, filename in enumerate(json_files, start=1):
    file_path = os.path.join(input_directory, filename)

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Extract name and GUID
        image_name = data.get("m_Name")
        guid = data.get("m_RD", {}).get("m_Texture", {}).get("m_Collection")

        if image_name and guid:
            image_data[image_name] = guid

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON in {filename}: {e}")

    # Print progress every 10%
    if total_files > 0 and index % (total_files // 10 or 1) == 0:
        progress = (index / total_files) * 100
        print(f"Progress: {progress:.0f}% ({index}/{total_files} files processed)")

# Save results to output file
with open(output_file, "w", encoding="utf-8") as output:
    json.dump(image_data, output, indent=4)

print(f"Processing complete! {len(image_data)} images categorized. Data saved to {output_file}.")
