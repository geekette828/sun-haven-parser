"""
Read npc_cycles.json and output one wiki-formatted dialogue file per NPC.

- Hearts live on the *response* entry, but are appended to the *Option* line:
    hearts == -1 -> append " {{Heart Points|-|1}}"
    hearts ==  2 -> append " {{Heart Points|+|2}}"
- Emotion is numeric and must be converted to text:
    1=smirking, 2=laughing, 3=annoyed, 4=blushing, 5=sad
  If missing/0/unknown -> blank
- If response has quest GUID, look up questName in quest_data_BB_SQ.json and append to Response text:
    <br>&nbsp;&nbsp;'''+ Quest: [[NPCNAME/Events|questName]]'''
- If response gives an item, append to Response text:
    <br>&nbsp;&nbsp;'''+ Item: [[item]]'''
"""

import os
import sys
import re
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")

import config.constants as constants
from utils import json_utils


INPUT_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "npc_cycles.json")
OUTPUT_FOLDER = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Dialogue")

QUEST_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "quest_data_BB_SQ.json")

EMOTION_MAP = {
    1: "smirk",
    2: "laughing",
    3: "annoyed",
    4: "blushing",
    5: "sad",
}

def load_quest_name_map() -> dict:
    """
    Returns { guid: questName }
    Handles both list-of-dicts and dict-of-dicts shapes.
    """
    quest_data = json_utils.load_json(QUEST_JSON_PATH)
    quest_map = {}

    if isinstance(quest_data, list):
        for q in quest_data:
            if not isinstance(q, dict):
                continue
            guid = q.get("guid")
            name = q.get("questName")
            if guid and name:
                quest_map[str(guid)] = str(name)

    elif isinstance(quest_data, dict):
        for _, q in quest_data.items():
            if not isinstance(q, dict):
                continue
            guid = q.get("guid")
            name = q.get("questName")
            if guid and name:
                quest_map[str(guid)] = str(name)

    return quest_map


def _join_text(entries: Any) -> str:
    """
    Entries are typically: [{"text": "...", ...}, ...]
    Join multiple lines with <br> to keep them within a single template param.
    """
    if not entries:
        return ""
    if isinstance(entries, list):
        parts = []
        for e in entries:
            if isinstance(e, dict):
                t = e.get("text", "")
                if t:
                    parts.append(str(t))
            elif isinstance(e, str):
                parts.append(e)
        return "<br>".join(parts).strip()
    if isinstance(entries, dict):
        return str(entries.get("text", "")).strip()
    return str(entries).strip()


def _parse_cycle_index(cycle_key: str) -> int:
    """
    "Cycle00" -> 0, "Cycle01" -> 1, etc.
    """
    m = re.match(r"^Cycle(\d+)$", cycle_key or "")
    if not m:
        return 0
    return int(m.group(1))


def _split_key(k: str) -> Optional[Tuple[str, int, str]]:
    """
    Convert keys like:
      O1, O2a, O2B -> ("O", 2, "a")
      R1ab         -> ("R", 1, "ab")
      D, D2        -> ("D", 0, "") or ("D", 2, "")
    """
    if not k or not isinstance(k, str):
        return None
    k = k.strip()
    if not k:
        return None

    md = re.match(r"^(D)(\d*)$", k, flags=re.IGNORECASE)
    if md:
        n = int(md.group(2)) if md.group(2) else 0
        return ("D", n, "")

    m = re.match(r"^([OR])(\d+)([A-Za-z]*)$", k, flags=re.IGNORECASE)
    if not m:
        return None

    kind = m.group(1).upper()
    num = int(m.group(2))
    suf = (m.group(3) or "").lower()
    return (kind, num, suf)


def _heart_suffix(hearts: Any) -> str:
    try:
        h = int(hearts)
    except Exception:
        return ""
    if h == -1:
        return " {{Heart Points|-|1}}"
    if h == 2:
        return " {{Heart Points|+|2}}"
    return ""


def _emotion_value(emotion: Any) -> str:
    """
    Convert numeric emotion codes to text.
    Unknown or zero values return blank.
    """
    if emotion is None:
        return ""
    try:
        emotion_int = int(emotion)
    except Exception:
        return ""
    if emotion_int == 0:
        return ""
    return EMOTION_MAP.get(emotion_int, "")


def _build_response_maps(
    cycle_obj: Dict[str, Any]
) -> Tuple[Dict[Tuple[int, str], Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    """
    Returns:
      response_by_num_suffix[(num, suffix)] -> payload dict
      response_base_by_num[num] -> payload dict (for R1, R2, etc.)

    Handles combined keys like R1ab by mapping the same response to (1,'a') and (1,'b').
    """
    response_by_num_suffix: Dict[Tuple[int, str], Dict[str, Any]] = {}
    response_base_by_num: Dict[int, Dict[str, Any]] = {}

    for k, v in (cycle_obj or {}).items():
        parsed = _split_key(k)
        if not parsed:
            continue
        kind, num, suf = parsed
        if kind != "R":
            continue

        entry = None
        if isinstance(v, list) and v:
            entry = v[0] if isinstance(v[0], dict) else {"text": _join_text(v)}
        elif isinstance(v, dict):
            entry = v
        else:
            entry = {"text": _join_text(v)}

        payload = {
            "text": str(entry.get("text", "")).strip(),
            "emotion": entry.get("emotion", None),
            "hearts": entry.get("hearts", 0),
            "quest": entry.get("quest", None),
            "item": entry.get("item", None),
            "itemAmount": entry.get("itemAmount", None),
        }

        if not suf:
            response_base_by_num[num] = payload
        else:
            if len(suf) > 1:
                for ch in suf:
                    response_by_num_suffix[(num, ch)] = payload
            else:
                response_by_num_suffix[(num, suf)] = payload

    return response_by_num_suffix, response_base_by_num


def _select_dialogue_text(cycle_obj: Dict[str, Any]) -> str:
    """
    Prefer D (no number). If missing, choose the smallest-numbered D* (e.g., D2).
    """
    candidates: List[Tuple[int, str]] = []
    for k in (cycle_obj or {}).keys():
        parsed = _split_key(k)
        if not parsed:
            continue
        kind, dnum, _ = parsed
        if kind == "D":
            candidates.append((dnum, k))

    if not candidates:
        return ""

    candidates.sort(key=lambda x: x[0])
    best_key = candidates[0][1]
    return _join_text(cycle_obj.get(best_key))


def _append_response_extras(response_text: str, npc_name: str, resp: Optional[dict], quest_name_map: dict) -> str:
    """
    Appends quest + item notes to the response text, using the exact formatting requested.
    """
    if not resp:
        return response_text

    out = response_text

    quest_guid = resp.get("quest")
    if quest_guid:
        quest_name = quest_name_map.get(str(quest_guid), "")
        if quest_name:
            out += f"<br>&nbsp;&nbsp;'''+ Quest: [[{npc_name}/Events|{quest_name}]]'''"

    item = resp.get("item")
    if item:
        out += f"<br>&nbsp;&nbsp;'''+ Item: [[{item}]]'''"

    return out


def _render_cycle(npc: str, cycle_key: str, cycle_obj: Dict[str, Any], quest_name_map: dict) -> str:
    cycle_number = _parse_cycle_index(cycle_key)
    dialogue_text = _select_dialogue_text(cycle_obj)

    response_by_num_suffix, response_base_by_num = _build_response_maps(cycle_obj)

    options: List[Tuple[int, str, str]] = []
    for k in (cycle_obj or {}).keys():
        parsed = _split_key(k)
        if not parsed:
            continue
        kind, num, suf = parsed
        if kind == "O":
            options.append((num, suf, k))

    def opt_sort_key(t: Tuple[int, str, str]) -> Tuple[int, int, str]:
        num, suf, _ = t
        return (num, 0 if suf == "" else 1, suf)

    options.sort(key=opt_sort_key)

    lines: List[str] = []
    lines.append("{{Conversation dialogue|npc = " + npc)
    lines.append(f"|title = Cycle {cycle_number}")
    lines.append("|Dialogue = " + dialogue_text)

    emitted_emotion: set[str] = set()

    for num, suf, raw_key in options:
        opt_text = _join_text(cycle_obj.get(raw_key))

        hearts = 0
        resp: Optional[dict] = None

        if suf:
            resp = response_by_num_suffix.get((num, suf))
            if resp:
                hearts = resp.get("hearts", 0)
        else:
            resp = response_base_by_num.get(num)
            if resp:
                hearts = resp.get("hearts", 0)

        opt_text_with_hearts = opt_text + _heart_suffix(hearts)

        indent = "   " if suf else ""
        lines.append(f"{indent}|Option{num}{suf} = {opt_text_with_hearts}")

        response_text = ""
        emotion_text = ""

        if resp:
            response_text = resp.get("text", "")
            emotion_text = _emotion_value(resp.get("emotion", None))

        if response_text:
            response_text = _append_response_extras(response_text, npc, resp, quest_name_map)
            lines.append(f"{indent}{indent}|Response{num}{suf} = {response_text}")

            emotion_param_name = f"Response{num}{suf}Emotion"
            if emotion_param_name not in emitted_emotion:
                lines.append(f"{indent}{indent}|{emotion_param_name} = {emotion_text}")
                emitted_emotion.add(emotion_param_name)

    lines.append("}}")
    return "\n".join(lines)


def main() -> None:
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    data: Dict[str, Any] = json_utils.load_json(INPUT_JSON_PATH)
    if not isinstance(data, dict):
        raise ValueError(f"Expected top-level dict in {INPUT_JSON_PATH}, got {type(data)}")

    quest_name_map = load_quest_name_map()

    written = 0

    for npc_name in sorted(data.keys(), key=lambda s: s.lower()):
        npc_obj = data.get(npc_name, {})
        if not isinstance(npc_obj, dict):
            continue

        cycle_keys = [k for k in npc_obj.keys() if isinstance(k, str) and k.startswith("Cycle")]
        cycle_keys.sort(key=lambda ck: (_parse_cycle_index(ck), ck))

        blocks: List[str] = []
        for ck in cycle_keys:
            cycle_obj = npc_obj.get(ck, {})
            if not isinstance(cycle_obj, dict):
                continue
            blocks.append(_render_cycle(npc_name, ck, cycle_obj, quest_name_map))

        if not blocks:
            continue

        out_name = f"{npc_name} cycles.txt"
        out_path = os.path.join(OUTPUT_FOLDER, out_name)

        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n\n".join(blocks).strip() + "\n")

        written += 1

    print(f"✅ Wrote {written} NPC dialogue files to: {OUTPUT_FOLDER}")


if __name__ == "__main__":
    main()
