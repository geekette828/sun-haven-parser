import os
import re
import sys
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils, text_utils

# Paths
input_dir = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
output_dir = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Dialogue")
file_utils.ensure_dir_exists(output_dir)

# Memory Loss Potion source (must preserve [] and <i>...</i>)
english_prefab_path = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")

# Load item ID to name map
with open(json_file_path, encoding="utf-8") as f:
    json_data = json.load(f)

id_to_name = {
    str(data["ID"]): data["Name"]
    for name, data in json_data.items()
    if "ID" in data and "Name" in data
}

# Prefab parsing helpers (minimal decoding, preserve tags)
TERM_RE = re.compile(r"^\s*-\s*Term:\s*(.+?)\s*$")
LANGUAGES_HEADER_RE = re.compile(r"^\s*Languages:\s*$")
LANG_ITEM_RE = re.compile(r"^\s*-\s*(.*)\s*$")

MLP_TERM_RE = re.compile(r"^RNPC\.([^.]+)\.MLP(?:\.Married)?$", re.IGNORECASE)

def decode_yaml_scalar(value: str) -> str:
    v = value.strip()

    # YAML single-quoted
    if len(v) >= 2 and v[0] == "'" and v[-1] == "'":
        inner = v[1:-1]
        inner = inner.replace("''", "'")
        return inner

    # YAML double-quoted
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        inner = v[1:-1]
        inner = (
            inner.replace(r"\\", "\\")
            .replace(r"\"", '"')
            .replace(r"\n", "\n")
            .replace(r"\t", "\t")
        )
        return inner

    return v


def load_memory_loss_lines(prefab_path: str):
    """
    Reads English.prefab and returns:
      {
        "Claude": {
          "normal": "<raw text with [] and <i>...>",
          "married": "<raw text with [] and <i>...>"
        },
        ...
      }
    We intentionally DO NOT run clean_dialogue/clean_game_dialogue here because we need the markers.
    """
    out = {}

    current_term = None
    waiting_for_language_value = False

    with open(prefab_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m_term = TERM_RE.match(line)
            if m_term:
                current_term = m_term.group(1).strip()
                waiting_for_language_value = False
                continue

            if current_term and LANGUAGES_HEADER_RE.match(line):
                # English is first entry under Languages:
                waiting_for_language_value = True
                continue

            if current_term and waiting_for_language_value:
                m_lang = LANG_ITEM_RE.match(line)
                if m_lang:
                    raw_value = m_lang.group(1)
                    english_raw = decode_yaml_scalar(raw_value)

                    m_mlp = MLP_TERM_RE.match(current_term)
                    if m_mlp:
                        npc_name = m_mlp.group(1)

                        npc_map = out.setdefault(npc_name, {})
                        if current_term.lower().endswith(".mlp.married"):
                            npc_map["married"] = english_raw
                        else:
                            npc_map["normal"] = english_raw

                waiting_for_language_value = False
                continue

    return out


def parse_memory_loss_text(npc_name: str, text: str, is_married: bool):
    """
    Input text format (from prefab) is like:
      Dialogue[]<i>PotionAction</i>[]Post...
    Where:
      - Dialogue is before first []
      - PotionAction is inside <i>...</i>
      - For normal MLP, trailing text is PostPlatonic
      - For MLP.Married, trailing text is PostDialogue

    Also replace 'XX' with '{{PLAYER}}' in Dialogue, matching your example.
    """
    if not text:
        return {
            "Dialogue": "",
            "PotionAction": "",
            "PostPlatonic": "",
            "PostDialogue": ""
        }

    # Replace XX -> {{PLAYER}} (only requested for the Dialogue portion, but safe to do globally)
    text = text.replace("XX", "{{PLAYER}}").strip()

    # Dialogue: up to first [] if present
    dialogue = ""
    if "[]" in text:
        dialogue = text.split("[]", 1)[0].strip()
    else:
        # Fallback: if no [], use up to <i> or whole string
        if "<i>" in text:
            dialogue = text.split("<i>", 1)[0].strip()
        else:
            dialogue = text.strip()

    # PotionAction: inside italics
    potion_action = ""
    m_i = re.search(r"<i>(.*?)</i>", text, flags=re.DOTALL)
    if m_i:
        potion_action = m_i.group(1).strip()

    # After italics: prefer exact "</i>[]", fallback "</i>"
    after = ""
    if "</i>[]" in text:
        after = text.split("</i>[]", 1)[1].strip()
    elif "</i>" in text:
        after = text.split("</i>", 1)[1].strip()
        # strip a leading [] if present
        if after.startswith("[]"):
            after = after[2:].lstrip()

    post_platonic = ""
    post_dialogue = ""

    if is_married:
        post_dialogue = after
    else:
        post_platonic = after

    return {
        "Dialogue": dialogue,
        "PotionAction": potion_action,
        "PostPlatonic": post_platonic,
        "PostDialogue": post_dialogue
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
                rows.append(f"| {{{{icon|{item_name} }}}} || {response}\n|-")
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


def build_dialogue_shell(npc_name, general_lines, unique_rows, birthday_block, memory_loss_fields):
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
|Dialogue = {memory_loss_fields.get("Dialogue","")}
|PotionAction = {memory_loss_fields.get("PotionAction","")}
|PostPlatonic = {memory_loss_fields.get("PostPlatonic","")}
|PostDialogue = {memory_loss_fields.get("PostDialogue","")}   }}}}

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


# Load all memory loss lines once (fast, avoids re-reading prefab per NPC)
memory_loss_map = {}
if os.path.exists(english_prefab_path):
    memory_loss_map = load_memory_loss_lines(english_prefab_path)
else:
    print(f"🔍 English.prefab not found for Memory Loss Potion parsing: {english_prefab_path}")

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

    mlp_text_normal = memory_loss_map.get(npc_name, {}).get("normal", "")
    mlp_text_married = memory_loss_map.get(npc_name, {}).get("married", "")

    fields_normal = parse_memory_loss_text(npc_name, mlp_text_normal, is_married=False)
    fields_married = parse_memory_loss_text(npc_name, mlp_text_married, is_married=True)

    # Combine:
    # - Dialogue should be the shared first segment; use married if available else normal
    # - PotionAction: prefer married if available else normal
    # - PostPlatonic: from normal
    # - PostDialogue: from married
    memory_loss_fields = {
        "Dialogue": fields_married.get("Dialogue") or fields_normal.get("Dialogue") or "",
        "PotionAction": fields_married.get("PotionAction") or fields_normal.get("PotionAction") or "",
        "PostPlatonic": fields_normal.get("PostPlatonic") or "",
        "PostDialogue": fields_married.get("PostDialogue") or ""
    }

    content = build_dialogue_shell(npc_name, general_lines, unique_rows, birthday_block, memory_loss_fields)
    file_utils.write_lines(os.path.join(output_dir, f"{npc_name} gifting lines.txt"), [content])

print(f"✅ Dialogue gifting lines created in: {output_dir}")
