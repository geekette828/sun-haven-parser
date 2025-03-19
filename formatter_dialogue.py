import os
import re
import config  # Import configuration file

# Define input and output paths
input_directory = os.path.join(config.INPUT_DIRECTORY, "TextAsset")
output_directory = os.path.join(config.OUTPUT_DIRECTORY, "Wiki Formatted/Dialogues")

# Ensure output directory exists
os.makedirs(output_directory, exist_ok=True)

# Dictionary to store dialogues per character
dialogue_groups = {}

# Function to remove HTML tags
def strip_html(text):
    return re.sub(r"<.*?>", "", text)

# Function to format multiline text correctly
def clean_text(text):
    text = text.replace("XX", "{{PLAYER}}")  # Replace XX with {{PLAYER}}
    text = text.replace("[]", "<br>")  # Replace [] with <br>
    text = strip_html(text)  # Remove HTML
    return text

# Scan for `.txt` files in the input directory
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

    cycle_dialogues = []  # Store cycles first
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

    with open(output_file_path, "w", encoding="utf-8") as outfile:
        for file_path in sorted(files):
            try:
                with open(file_path, "r", encoding="utf-8") as infile:
                    lines = infile.readlines()

                filename = os.path.basename(file_path)

                # Detect cycle numbers
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
                    options = {}
                    responses = {}

                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        # Remove redundant cycle title
                        if f"Cycle {cycle_number}" in line:
                            continue

                        # Replace End with closing brackets
                        if line == "End":
                            if cycle_number == "0":
                                cycle_text += f"|PlayerResponse = {player_response}\n"
                                cycle_text += f"|NPCResponse    = {npc_response} }}\n\n"
                            else:
                                cycle_text += "}}\n\n"
                            cycle_dialogues.append(cycle_text)
                            break

                        # Formatting updates
                        if "::" in line:
                            key, value = line.split("::", 1)
                            key = key.strip()
                            value = clean_text(value.strip())

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

                # Handle One Liners
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
                            chat_text = clean_text(line.replace("Dialogue::", "").strip())

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

        # Write Cycle Dialogues First
        outfile.writelines(cycle_dialogues)

        # Write One Liners below the cycles
        def write_one_liner_section(title, lines, level=2):
            if lines:
                outfile.write(f"{'=' * level} {title} {'=' * level}\n")
                outfile.writelines(lines)
                outfile.write("\n")

        # General One-Liners
        write_one_liner_section("General", one_liners["General"])

        # Platonic One-Liners
        write_one_liner_section("Platonic", one_liners["Platonic"])

        # Dating One-Liners
        write_one_liner_section("Dating", one_liners["Dating"])

        # Married One-Liners
        write_one_liner_section("Married", one_liners["Married"]["General"])

        # Seasonal One-Liners
        for season, lines in one_liners["Seasonal"].items():
            write_one_liner_section(f"General {season}", lines, level=3)

        # Married Seasonal One-Liners
        for season, lines in one_liners["Married"].items():
            if season != "General":
                write_one_liner_section(f"Married {season}", lines, level=3)

print(f"Formatted dialogues generated successfully: {output_file_path}")
