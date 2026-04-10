"""
NPC romance dialogue & unique gifts exporter — Layer 3 of the pipeline.

Reads GiftTable.asset files and English.prefab (for Memory Loss Potion dialogue)
and writes one "<NPC> gifting lines.txt" per NPC to Wiki Formatted/NPC Dialogue/.

Item IDs are resolved from the item builder cache via _load_cache().

Usage:
    python exporters/npc_romance_dialogue_unique_gifts.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from builders.item_builder import _load_cache
from utils import file_utils, text_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_INPUT_DIR    = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
_OUTPUT_DIR   = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Dialogue")
_PREFAB_PATH  = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")

# ---------------------------------------------------------------------------
# Prefab parsing (Memory Loss Potion lines)
# ---------------------------------------------------------------------------

_TERM_RE             = re.compile(r"^\s*-\s*Term:\s*(.+?)\s*$")
_LANGUAGES_HEADER_RE = re.compile(r"^\s*Languages:\s*$")
_LANG_ITEM_RE        = re.compile(r"^\s*-\s*(.*)\s*$")
_MLP_TERM_RE         = re.compile(r"^RNPC\.([^.]+)\.MLP(?:\.Married)?$", re.IGNORECASE)


def _decode_yaml_scalar(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == "'" and v[-1] == "'":
        return v[1:-1].replace("''", "'")
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return (
            v[1:-1]
            .replace(r"\\", "\\")
            .replace(r"\"", '"')
            .replace(r"\n", "\n")
            .replace(r"\t", "\t")
        )
    return v


def _load_memory_loss_lines(prefab_path: str) -> dict:
    """Return {npc_name: {"normal": str, "married": str}} from English.prefab."""
    out: dict = {}
    current_term = None
    waiting = False

    with open(prefab_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m_term = _TERM_RE.match(line)
            if m_term:
                current_term = m_term.group(1).strip()
                waiting = False
                continue
            if current_term and _LANGUAGES_HEADER_RE.match(line):
                waiting = True
                continue
            if current_term and waiting:
                m_lang = _LANG_ITEM_RE.match(line)
                if m_lang:
                    raw = _decode_yaml_scalar(m_lang.group(1))
                    m_mlp = _MLP_TERM_RE.match(current_term)
                    if m_mlp:
                        npc = m_mlp.group(1)
                        npc_map = out.setdefault(npc, {})
                        if current_term.lower().endswith(".mlp.married"):
                            npc_map["married"] = raw
                        else:
                            npc_map["normal"] = raw
                waiting = False

    return out


def _parse_memory_loss_text(text: str, is_married: bool) -> dict:
    if not text:
        return {"Dialogue": "", "PotionAction": "", "PostPlatonic": "", "PostDialogue": ""}

    text = text.replace("XX", "{{PLAYER}}").strip()

    dialogue = ""
    if "[]" in text:
        dialogue = text.split("[]", 1)[0].strip()
    elif "<i>" in text:
        dialogue = text.split("<i>", 1)[0].strip()
    else:
        dialogue = text.strip()

    potion_action = ""
    m_i = re.search(r"<i>(.*?)</i>", text, flags=re.DOTALL)
    if m_i:
        potion_action = m_i.group(1).strip()

    after = ""
    if "</i>[]" in text:
        after = text.split("</i>[]", 1)[1].strip()
    elif "</i>" in text:
        after = text.split("</i>", 1)[1].strip()
        if after.startswith("[]"):
            after = after[2:].lstrip()

    return {
        "Dialogue":     dialogue,
        "PotionAction": potion_action,
        "PostPlatonic": after if not is_married else "",
        "PostDialogue": after if is_married else "",
    }

# ---------------------------------------------------------------------------
# Asset helpers
# ---------------------------------------------------------------------------

def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _extract_response_block(lines: list[str], section_header: str) -> list[str]:
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


def _extract_unique_gifts(lines: list[str], id_to_name: dict) -> list[str]:
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


def _extract_birthday_data(lines: list[str], npc_name: str) -> str:
    day = None
    month = None
    responses: list[str] = []
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
    ordinal_day = _ordinal(day)

    output = (
        f"If the player gives {npc_name} a gift on their [[Calendar|birthday]], "
        f"they will get one of these generic responses based on the level of the gift. "
        f"{npc_name}'s birthday is the {ordinal_day} of {month_name}.\n"
    )
    for label, idx in zip(["Loved", "Liked", "Good", "Disliked"], [3, 2, 1, 0]):
        text = responses[idx] if idx < len(responses) else ""
        output += f'* {label}: "{text}"\n'

    return output


def _build_dialogue_shell(
    npc_name: str,
    general_lines: dict,
    unique_rows: list[str],
    birthday_block: str,
    memory_loss_fields: dict,
) -> str:
    general_block = "".join(f'* {k}: "{v}"\n' for k, v in general_lines.items() if v)
    unique_block  = "\n".join(unique_rows) if unique_rows else "|-\n| || '''''No unique gifts.'''''"

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

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(_OUTPUT_DIR)

    # Build id → name from item builder cache
    items = _load_cache()
    id_to_name: dict[str, str] = {str(item.item_id): item.name for item in items.values()}

    # Load Memory Loss Potion lines once
    memory_loss_map: dict = {}
    if os.path.exists(_PREFAB_PATH):
        memory_loss_map = _load_memory_loss_lines(_PREFAB_PATH)
    else:
        print(f"⚠️  English.prefab not found: {_PREFAB_PATH}")

    for filename in os.listdir(_INPUT_DIR):
        if not filename.endswith("GiftTable.asset"):
            continue

        npc_name = filename.replace("GiftTable.asset", "")
        filepath = os.path.join(_INPUT_DIR, filename)
        lines = file_utils.read_file_lines(filepath)

        general_lines = {
            "Loved":    next(iter(_extract_response_block(lines, "loveGiftResponses:")), ""),
            "Liked":    next(iter(_extract_response_block(lines, "likeGiftResponses:")), ""),
            "Good":     next(iter(_extract_response_block(lines, "goodGiftResponses:")), ""),
            "Disliked": next(iter(_extract_response_block(lines, "dislikeGiftResponses:")), ""),
        }

        unique_rows    = _extract_unique_gifts(lines, id_to_name)
        birthday_block = _extract_birthday_data(lines, npc_name)

        mlp_normal  = memory_loss_map.get(npc_name, {}).get("normal",  "")
        mlp_married = memory_loss_map.get(npc_name, {}).get("married", "")

        fields_normal  = _parse_memory_loss_text(mlp_normal,  is_married=False)
        fields_married = _parse_memory_loss_text(mlp_married, is_married=True)

        memory_loss_fields = {
            "Dialogue":     fields_married.get("Dialogue")     or fields_normal.get("Dialogue") or "",
            "PotionAction": fields_married.get("PotionAction") or fields_normal.get("PotionAction") or "",
            "PostPlatonic": fields_normal.get("PostPlatonic") or "",
            "PostDialogue": fields_married.get("PostDialogue") or "",
        }

        content = _build_dialogue_shell(
            npc_name, general_lines, unique_rows, birthday_block, memory_loss_fields
        )
        file_utils.write_lines(
            os.path.join(_OUTPUT_DIR, f"{npc_name} gifting lines.txt"),
            [content],
        )

    print(f"✅ Gifting lines written to: {_OUTPUT_DIR}")


if __name__ == "__main__":
    run()
