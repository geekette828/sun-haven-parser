import os
import sys
import re
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils

# === Setup paths ===
input_dir = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "npc_gift_preferences.txt")
debug_log_path = os.path.join(".hidden", "debug_output", "create_npc_gift_debug.txt")

file_utils.ensure_dir_exists(os.path.dirname(output_file_path))
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

# === Load item ID to name map ===
with open(json_file_path, encoding="utf-8") as f:
    json_data = json.load(f)

id_to_name = {}
for name, data in json_data.items():
    item_id = data.get("ID")
    item_name = data.get("Name")
    if item_id is not None and item_name:
        id_to_name[str(item_id)] = item_name

# === Items to skip from output ===
SKIP_ITEMS = {"red rose bouquet", "blue rose bouquet"}

# === Utility: extract IDs from section ===
def extract_ids_between_sections(lines, section_header):
    ids = []
    in_section = False
    for line in lines:
        line = line.strip()
        if line.startswith(section_header):
            in_section = True
            continue
        if in_section:
            if re.match(r"^[a-zA-Z0-9_]+:", line):
                break
            match = re.match(r"- id:\s*(\d+)", line)
            if match:
                ids.append(match.group(1))
    return ids

# === Utility: extract response texts from section ===
def extract_response_block(lines, section_header):
    responses = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(section_header):
            in_section = True
            continue
        if in_section:
            if re.match(r"^[a-zA-Z0-9_]+:", stripped):
                break
            if stripped.startswith("- response:"):
                response_text = (
                    stripped.split(":", 1)[1]
                    .strip()
                    .replace("ITEM", "[''item'']")
                    .replace("XX", "{{PLAYER}}")
                    .replace("PPP", "{{PARENT}}")
                )
                responses.append(response_text)
    return " / ".join(responses)

# === Utility: convert ID list to name list ===
def convert_ids_to_names(id_list):
    names = []
    for item_id in id_list:
        name = id_to_name.get(item_id)
        if name:
            if name.lower() not in SKIP_ITEMS:
                names.append(name)
        else:
            names.append(f"[Unknown {item_id}]")
    return "; ".join(names)

# === Process each GiftTable.asset file ===
results = []

for filename in os.listdir(input_dir):
    if not filename.endswith("GiftTable.asset"):
        continue

    npc_name = filename.replace("GiftTable.asset", "")
    filepath = os.path.join(input_dir, filename)
    lines = file_utils.read_file_lines(filepath)

    love_ids = extract_ids_between_sections(lines, "love2:")
    like_ids = extract_ids_between_sections(lines, "like2:")
    dislike_ids = extract_ids_between_sections(lines, "dislike2:")

    love_response = extract_response_block(lines, "loveGiftResponses:")
    like_response = extract_response_block(lines, "likeGiftResponses:")
    good_response = extract_response_block(lines, "goodGiftResponses:")
    dislike_response = extract_response_block(lines, "dislikeGiftResponses:")

    block = [
        f"### {npc_name} ###",
        "{{NPC Gift Preferences",
        f"|loveResponse = {love_response}",
        f"|love = {convert_ids_to_names(love_ids)}",
        "|loveGroups = [[:Category:Universally loved gifts|Universally Loved Items]]",
        "",
        f"|likeResponse = {like_response}",
        f"|like = {convert_ids_to_names(like_ids)}",
        "|likeGroups = [[:Category:Universally liked gifts|Universally Liked Items]]",
        "",
        f"|goodResponse = {good_response}",
        "",
        f"|dislikeResponse = {dislike_response}",
        f"|dislike = {convert_ids_to_names(dislike_ids)}",
        "|dislikeGroups = [[:Category:Universally disliked gifts|Universally Disliked Items]]",
        "}}\n"
    ]

    results.append("\n".join(block))

file_utils.write_lines(output_file_path, [line + "\n" for line in results])
print(f"✅ Gift tables written to: {output_file_path}")
