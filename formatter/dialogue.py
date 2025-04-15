import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import re
import config.constants as constants
from utils import file_utils, text_utils

# Define input and output paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "TextAsset")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Dialogues")
file_utils.ensure_dir_exists(output_directory)

# Dictionary to store dialogues per character
dialogue_groups = {}

# Define a custom dialogue text cleaning function using text_utils
def clean_dialogue_text(text):
    # Replace placeholders (e.g., "XX" with "{{PLAYER}}")
    text = text_utils.replace_placeholders(text)
    # Replace [] with <br>
    text = text.replace("[]", "<br>")
    # Remove any HTML tags
    text = text_utils.strip_html(text)
    return text

# Scan for .txt files in the input directory
for filename in os.listdir(input_directory):
    if filename.endswith(".txt"):  # Process only .txt files
        character_name = filename.split()[0]  # Extract character name
        file_path = os.path.join(input_directory, filename)

        # Group files by character name
        if character_name not in dialogue_groups:
            dialogue_groups[character_name] = []
        dialogue_groups[character_name].append(file_path)

# Process each character's dialogue files
for character, files in dialogue_groups.items():
    output_file_path = os.path.join(output_directory, f"{character} Dialogue.txt")

    cycle_dialogues = []  # Store cycle dialogues first
    one_liners = {
        "General": [],
        "Platonic": [],
        "Dating": [],
        "Married": {
            "General": [],
            "Spring": [],
            "Summer": [],
            "Fall": [],
            "Winter": []
        },
        "Seasonal": {
            "Spring": [],
            "Summer": [],
            "Fall": [],
            "Winter": []
        }
    }

    output_lines = []

    for file_path in sorted(files):
        try:
            lines = file_utils.read_file_lines(file_path)
            filename = os.path.basename(file_path)

            # Detect cycle numbers from the filename
            match = re.search(r"Cycle (\d+)", filename)
            cycle_number = match.group(1) if match else None

            # Handle cycle dialogues
            if cycle_number:
                if cycle_number == "0":
                    cycle_text = f"{{{{Player Introduction|{character}\n"
                else:
                    cycle_text = f"{{{{Conversation Dialogue|{character}\n"
                    cycle_text += f"|Cycle {cycle_number}\n"

                dialogue_text = ""
                player_response = ""
                npc_response = ""

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Remove redundant cycle title
                    if f"Cycle {cycle_number}" in line:
                        continue

                    # Replace "End" with closing brackets and append the dialogue
                    if line == "End":
                        if cycle_number == "0":
                            cycle_text += f"|PlayerResponse = {player_response}\n"
                            cycle_text += f"|NPCResponse    = {npc_response} }}\n\n"
                        else:
                            cycle_text += "}}\n\n"
                        cycle_dialogues.append(cycle_text)
                        break

                    # Process lines with key-value pairs
                    if "::" in line:
                        key, value = line.split("::", 1)
                        key = key.strip()
                        value = clean_dialogue_text(value.strip())

                        if cycle_number == "0":
                            if key.startswith("Dialogue"):
                                dialogue_text = value
                                cycle_text += f"|Dialogue       = {dialogue_text}\n"
                            elif key.startswith("Option1"):
                                player_response = value
                            elif key.startswith("Response1"):
                                npc_response = value
                        else:
                            cycle_text += f"|{key}={value}\n"

            # Handle One Liner dialogues
            elif "One Liner" in filename:
                one_liner_category = "General"
                season = None

                # Extract category and season from filename
                match = re.search(r"One Liner (Platonic|Dating|Married|Spring|Summer|Fall|Winter)?\s?(Spring|Summer|Fall|Winter)?", filename)
                if match:
                    category_part, season_part = match.groups()
                    if category_part in ["Platonic", "Dating", "Married"]:
                        one_liner_category = category_part
                    if season_part:
                        season = season_part

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith("Dialogue::"):
                        chat_text = clean_dialogue_text(line.replace("Dialogue::", "").strip())
                        formatted_chat = f"{{{{chat||{chat_text}}}}}\n"

                        if season:
                            if one_liner_category == "Married":
                                one_liners["Married"][season].append(formatted_chat)
                            else:
                                one_liners["Seasonal"][season].append(formatted_chat)
                        else:
                            if one_liner_category == "Married":
                                one_liners["Married"]["General"].append(formatted_chat)
                            else:
                                one_liners[one_liner_category].append(formatted_chat)

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    # Write Cycle Dialogues first
    output_lines.extend(cycle_dialogues)

    # Function to write one-liner sections to the output
    def write_one_liner_section(title, lines, level=2):
        if lines:
            output_lines.append(f"{'=' * level}{title}{'=' * level}\n")
            output_lines.extend(lines)
            output_lines.append("\n")

    # Write one-liner sections in desired order
    write_one_liner_section("General", one_liners["General"])
    write_one_liner_section("Platonic", one_liners["Platonic"])
    write_one_liner_section("Dating", one_liners["Dating"])
    write_one_liner_section("Married", one_liners["Married"]["General"])

    for season, lines in one_liners["Seasonal"].items():
        write_one_liner_section(f"General {season}", lines, level=3)

    for season, lines in one_liners["Married"].items():
        if season != "General":
            write_one_liner_section(f"Married {season}", lines, level=3)

    file_utils.write_lines(output_file_path, output_lines)
    print(f"Formatted dialogues generated successfully: {output_file_path}")

print(f"Dialogue processing complete.")
