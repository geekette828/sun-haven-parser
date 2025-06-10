import os
import re
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import file_utils, text_utils
import config.constants as constants

# Paths
input_dir = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
output_dir = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Dialogues_Gifting_Lines")
file_utils.ensure_dir_exists(output_dir)

# Load item ID to name map
with open(json_file_path, encoding="utf-8") as f:
    json_data = json.load(f)

id_to_name = {
    str(data["ID"]): data["Name"]
    for name, data in json_data.items()
    if "ID" in data and "Name" in data
}

# Helpers
def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

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
                raw = stripped.split(":", 1)[1].strip()
                responses.append(text_utils.clean_dialogue(raw))
    return responses

def extract_unique_gifts(lines):
    rows = []
    in_section = False
    current_id = None
    response = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("uniqueGifts2:"):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("birthDay:"):
                break
            if stripped.startswith("- item:"):
                current_id = None
                response = None
                continue
            if stripped.startswith("id:") and current_id is None:
                current_id = stripped.split(":")[1].strip()
            if stripped.startswith("response:") and current_id:
                response = text_utils.clean_dialogue(stripped.split(":", 1)[1].strip())
                item_name = id_to_name.get(current_id, f"[Unknown {current_id}]")
                rows.append(f"| [[{item_name}]] || '''{response}'''\n|-")
                current_id = None
    return rows

def extract_birthday_data(lines, npc_name):
    day = None
    month = None
    responses = []
    in_section = False

    for line in lines:
        if "birthDay:" in line:
            try:
                day = int(line.split(":")[1].strip())
            except ValueError:
                pass
        elif "birthMonth:" in line:
            try:
                month = int(line.split(":")[1].strip())
            except ValueError:
                pass
        elif "birthdayGiftResponses:" in line:
            in_section = True
            continue
        elif in_section:
            if not line.startswith("  "):
                break
            if line.strip().startswith("- response:"):
                raw = line.split(":", 1)[1].strip()
                responses.append(text_utils.clean_dialogue(raw))

    if day is None or month is None:
        return ""

    month_name = constants.SEASONS.get(month, f"Month{month}")
    ordinal_day = ordinal(day)

    output = f"If the player gives {npc_name} a gift on their [[Calendar|birthday]], they will get one of these generic responses based on the level of the gift. {npc_name}'s birthday is the {ordinal_day} of {month_name}.\n"
    label_order = ["Loved", "Liked", "Good", "Disliked"]
    index_order = [3, 2, 1, 0]

    for label, idx in zip(label_order, index_order):
        text = responses[idx] if idx < len(responses) else ""
        output += f"* {label}: \"{text}\"\n"

    return output

def build_dialogue_shell(npc_name, general_lines, unique_rows, birthday_block):
    general_block = "".join(f"* {k}: \"{v}\"\n" for k, v in general_lines.items() if v)
    unique_block = "\n".join(unique_rows) if unique_rows else "|-\n| || '''''No unique gifts.''''"

    return f"""==Gifting Lines==
===General===
{general_block}
===Birthday Responses===
{birthday_block}
===Memory Loss Potion===
The [[Memory Loss Potion]] is an item that, when gifted to a [[Romance_Candidates|romanceable NPC]], will cause them to forget all about the relationship they have with the player. When used on [[Romance_Candidates|romanceable candidates]] while married, the Memory Loss Potion will only reduce their hearts to ten (the platonic relationship cap), while getting a divorce at [[Town Hall]] will reduce it to 8.

{{{{Memory Loss Dialogue|{npc_name}|Collapse=True
|Dialogue     = 
|PotionAction = 
|PostPlatonic = 
|PostDialogue =   }}}}

===Unique===
{npc_name} has several unique lines for gifts.
{{| class="article-table"
!Gift !! Response
|-
{unique_block}
|}}

===Morning Gifts===
When married to {npc_name}, there is a chance they will have a gift for the player.  
"""

# === Main loop ===
for filename in os.listdir(input_dir):
    if not filename.endswith("GiftTable.asset"):
        continue

    npc_name = filename.replace("GiftTable.asset", "")
    filepath = os.path.join(input_dir, filename)
    lines = file_utils.read_file_lines(filepath)

    general_lines = {
        "Loved": next(iter(extract_response_block(lines, "loveGiftResponses:")), ""),
        "Liked": next(iter(extract_response_block(lines, "likeGiftResponses:")), ""),
        "Good": next(iter(extract_response_block(lines, "goodGiftResponses:")), ""),
        "Disliked": next(iter(extract_response_block(lines, "dislikeGiftResponses:")), "")
    }

    unique_rows = extract_unique_gifts(lines)
    birthday_block = extract_birthday_data(lines, npc_name)
    content = build_dialogue_shell(npc_name, general_lines, unique_rows, birthday_block)

    file_utils.write_lines(os.path.join(output_dir, f"{npc_name}.txt"), [content])

print(f"✅ Dialogue gifting lines created in: {output_dir}")
