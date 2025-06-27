import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils import file_utils, text_utils

# Define input and output paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "TextAsset")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Dialogues")
file_utils.ensure_dir_exists(output_directory)

# Dictionary to store dialogues per character
dialogue_groups = {}

# Define a custom dialogue text cleaning function using text_utils
def clean_dialogue_text(text):
    text = text_utils.replace_placeholders(text)
    text = text.replace("[]", "<br>")
    text = text_utils.strip_html(text)
    return text

# Scan for .txt files in the input directory
for filename in os.listdir(input_directory):
    if filename.endswith(".txt"):
        character_name = filename.split()[0]
        file_path = os.path.join(input_directory, filename)

        if character_name not in dialogue_groups:
            dialogue_groups[character_name] = []
        dialogue_groups[character_name].append(file_path)

# Process each character's dialogue files
for character, files in dialogue_groups.items():
    output_file_path = os.path.join(output_directory, f"{character} Dialogue.txt")

    cycle_dialogues = []
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

            match = re.search(r"Cycle (\w+)", filename)
            cycle_number = match.group(1) if match else None

            if cycle_number:
                if cycle_number == "0":
                    cycle_text = f"{{{{Player Introduction|{character}\n"
                else:
                    cycle_text = f"{{{{Conversation Dialogue|npc={character}\n"
                    cycle_text += f"|title = Cycle {cycle_number}\n"

                dialogue_text = ""
                player_response = ""
                npc_response = ""

                option_extras = {}

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    if f"Cycle {cycle_number}" in line:
                        continue

                    if line == "End":
                        if cycle_number == "0":
                            cycle_text += f"|PlayerResponse = {player_response}\n"
                            cycle_text += f"|NPCResponse    = {npc_response} }}\n\n"
                        else:
                            cycle_text += "}}\n\n"
                        cycle_dialogues.append(cycle_text)
                        break

                    if "::" in line:
                        key, value = line.split("::", 1)
                        key = key.strip()
                        raw_value = value.strip()

                        relationship_match = re.search(r"//Relationship\s+\w+\s+([-+]?\d+)\b", raw_value)
                        emotion_match = re.search(r"\b(Embarrassed|Mad|Sad|Happy|Romantic)\b", raw_value, re.IGNORECASE)

                        relationship_val = relationship_match and relationship_match.group(1)
                        emotion_val = emotion_match and emotion_match.group(1).lower()

                        value = clean_dialogue_text(raw_value.split("//")[0].strip())

                        if key.startswith("Option"):
                            option_extras[key] = {
                                "heart": relationship_val,
                                "emotion": emotion_val
                            }

                            if relationship_val:
                                try:
                                    points = int(relationship_val)
                                    sign = "+" if points > 0 else "-"
                                    value += f" {{{{Heart Points|{sign}|{abs(points)}}}}}"
                                except (TypeError, ValueError):
                                    pass

                            cycle_text += f"|{key}={value}\n"

                        elif key.startswith("Response"):
                            cycle_text += f"|{key}={value}\n"
                            matching_option = key.replace("Response", "Option")
                            extras = option_extras.get(matching_option, {})
                            if extras.get("emotion"):
                                cycle_text += f"   |{key}Emotion = {extras['emotion']}\n"

                        else:
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

            elif "One Liner" in filename:
                one_liner_category = "General"
                season = None

                match = re.search(r"One Liner (Platonic|Dating|Married|Spring|Summer|Fall|Winter)?\\s?(Spring|Summer|Fall|Winter)?", filename)
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

    output_lines.extend(cycle_dialogues)

    def write_one_liner_section(title, lines, level=2):
        if lines:
            output_lines.append(f"{'=' * level}{title}{'=' * level}\n")
            output_lines.extend(lines)
            output_lines.append("\n")

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
