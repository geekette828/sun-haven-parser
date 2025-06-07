import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
import re
import json
from utils import file_utils, json_utils
from math import floor

# Define paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "Scenes")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
file_utils.ensure_dir_exists(output_directory)

output_file = "fish_spawner_data.json"
output_file_path = os.path.join(output_directory, output_file)

# Setup logging
debug_log_path = os.path.join(".hidden", "debug_output", "json", "fish_spawner_data_debug.txt")
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

def parse_fish_block(block):
    named_fish = re.findall(r"- drop: (.+?)\n\s+dropChance: (\d+)", block)
    named_fish_drops = [
        {"name": name.strip(), "dropChance": int(chance)} for name, chance in named_fish
    ]

    seasonal = {}
    for season in ["fishSpring", "fishSummer", "fishFall", "fishWinter"]:
        seasonal[season] = [
            {"guid": guid, "dropChance": int(chance)}
            for guid, chance in re.findall(
                rf"{season}:\s+?drops:\s+?- fish: {{fileID: \d+, guid: ([a-f0-9]+),.*?dropChance: (\d+)",
                block
            )
        ]

    return named_fish_drops, seasonal


def process_unity_file(filepath):
    try:
        content = "\n".join(file_utils.read_file_lines(filepath))
        match = re.search(r"_fish:(.*?)--- !u!", content, re.DOTALL)
        if not match:
            return None

        named_fish, seasonal = parse_fish_block(match.group(1))
        scene_name = os.path.splitext(os.path.basename(filepath))[0]
        return {
            "sceneName": scene_name,
            "fishDrops": named_fish,
            "seasonalFish": seasonal
        }
    except Exception as e:
        file_utils.write_debug_log(f"Error processing {filepath}: {e}", debug_log_path)
        return None


def main():
    results = {}
    for filename in os.listdir(input_directory):
        if filename.endswith(".unity"):
            filepath = os.path.join(input_directory, filename)
            result = process_unity_file(filepath)
            if result:
                results[result["sceneName"]] = result

    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("✅ Fish spawner data extraction complete.")


if __name__ == "__main__":
    main()