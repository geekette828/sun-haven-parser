import sys
import os
import json
import config

# Ensure Pywikibot is accessible
sys.path.append(r"C:\Users\marjo\PWB\core") 
import pywikibot

# Define paths
json_data_directory = os.path.join(config.OUTPUT_DIRECTORY, "JSON Data")
file_input_directory = os.path.join(config.OUTPUT_DIRECTORY, "Pywikibot")
output_directory = os.path.join(config.OUTPUT_DIRECTORY, "Pywikibot")

# Define input and output files
comparison_file = os.path.join(file_input_directory, "comparison_summary.txt")
items_data_file = os.path.join(json_data_directory, "items_data.json")
images_data_file = os.path.join(json_data_directory, "images_data.json")
output_comparison_file = os.path.join(output_directory, "sprite to file comparison.txt")

def extract_json_only_items(file_path):
    """Extract items from the '##### JSON Only #####' section in the comparison summary file."""
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    json_only_items = []
    inside_json_section = False

    for line in lines:
        if line.strip() == "##### JSON Only #####":
            inside_json_section = True
            continue
        if inside_json_section:
            if line.strip() == "":  # Stop at an empty line
                break
            json_only_items.append(line.strip())

    return json_only_items

def load_json(file_path):
    """Load JSON data from a file."""
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return {}
    
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def find_icon_guid(items_data, item_name):
    """Find the GUID for a given item name (case-insensitive)."""
    lower_items = {key.lower(): value for key, value in items_data.items()}
    item_data = lower_items.get(item_name.lower())
    return item_data.get("GUID") if item_data else None  # Corrected field name

def find_image_filename(images_data, icon_guid):
    """Find the corresponding image filename for a given GUID (reverse lookup)."""
    for image_name, guid in images_data.items():
        if guid == icon_guid:
            return image_name  # Return the filename mapped to the GUID
    return "No matching image found"

def generate_sprite_comparison():
    """Generate a file listing each JSON-only item with its matching sprite filename."""
    json_items = extract_json_only_items(comparison_file)
    if not json_items:
        print("No JSON-only items found.")
        return

    items_data = load_json(items_data_file)
    images_data = load_json(images_data_file)

    with open(output_comparison_file, "w", encoding="utf-8") as f:
        f.write("### Sprite to File Comparison ###\n\n")

        for item in json_items:
            icon_guid = find_icon_guid(items_data, item)
            if not icon_guid:
                image_filename = "No icon GUID found"
            else:
                image_filename = find_image_filename(images_data, icon_guid)

            f.write(f"{item}: {image_filename}\n")

    print(f"Comparison file saved: {output_comparison_file}")

if __name__ == "__main__":
    generate_sprite_comparison()
