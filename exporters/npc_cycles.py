"""
NPC cycles exporter — Layer 3 of the pipeline.

Reads npc_dialogue.json and quest_data_BB_SQ.json and writes one
"<NPC> cycles.txt" per NPC to Wiki Formatted/NPC Dialogue/.

Usage:
    python exporters/npc_cycles.py
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.stdout.reconfigure(encoding="utf-8")

import config.constants as constants
from utils import json_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_INPUT_JSON   = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "npc_dialogue.json")
_OUTPUT_FOLDER = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Dialogue")
_QUEST_JSON   = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "quest_data_BB_SQ.json")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EMOTION_MAP = {
    1: "smirk",
    2: "laughing",
    3: "annoyed",
    4: "blushing",
    5: "sad",
}

_CYCLE_NUM_RE = re.compile(r"^Cycle(\d+)$", flags=re.IGNORECASE)
_CYCLE_P_RE   = re.compile(r"^CycleP(\d+)$", flags=re.IGNORECASE)

# ---------------------------------------------------------------------------
# Quest name lookup
# ---------------------------------------------------------------------------

def _load_quest_name_map() -> dict:
    quest_data = json_utils.load_json(_QUEST_JSON)
    quest_map: dict = {}

    if isinstance(quest_data, list):
        for q in quest_data:
            if isinstance(q, dict):
                guid = q.get("guid")
                name = q.get("quest_name") or q.get("questName")
                if guid and name:
                    quest_map[str(guid)] = str(name)
    elif isinstance(quest_data, dict):
        for _, q in quest_data.items():
            if isinstance(q, dict):
                guid = q.get("guid")
                name = q.get("quest_name") or q.get("questName")
                if guid and name:
                    quest_map[str(guid)] = str(name)

    return quest_map

# ---------------------------------------------------------------------------
# Sorting helpers
# ---------------------------------------------------------------------------

def _cycle_sort_key(cycle_key: str) -> Tuple[int, int, str]:
    c = (cycle_key or "").strip()
    mp = _CYCLE_P_RE.match(c)
    if mp:
        return (0, int(mp.group(1)), c.lower())
    mn = _CYCLE_NUM_RE.match(c)
    if mn:
        return (1, int(mn.group(1)), c.lower())
    return (2, 9_999_999, c.lower())


def _cycle_title(cycle_key: str) -> str:
    c = (cycle_key or "").strip()
    mp = _CYCLE_P_RE.match(c)
    if mp:
        return f"Cycle P{int(mp.group(1))}"
    mn = _CYCLE_NUM_RE.match(c)
    if mn:
        return f"Cycle {int(mn.group(1))}"
    return c

# ---------------------------------------------------------------------------
# Key parsing helpers
# ---------------------------------------------------------------------------

def _split_key(k: str) -> Optional[Tuple[str, int, str]]:
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
    return (m.group(1).upper(), int(m.group(2)), (m.group(3) or "").lower())


def _join_text(entries: Any) -> str:
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
    if emotion is None:
        return ""
    try:
        emotion_int = int(emotion)
    except Exception:
        return ""
    if emotion_int == 0:
        return ""
    return _EMOTION_MAP.get(emotion_int, "")

# ---------------------------------------------------------------------------
# Response map builder
# ---------------------------------------------------------------------------

def _build_response_maps(
    cycle_obj: Dict[str, Any],
) -> Tuple[Dict[Tuple[int, str], Dict], Dict[int, Dict]]:
    response_by_num_suffix: Dict[Tuple[int, str], Dict] = {}
    response_base_by_num: Dict[int, Dict] = {}

    for k, v in (cycle_obj or {}).items():
        parsed = _split_key(k)
        if not parsed:
            continue
        kind, num, suf = parsed
        if kind != "R":
            continue

        if isinstance(v, list) and v:
            entry = v[0] if isinstance(v[0], dict) else {"text": _join_text(v)}
        elif isinstance(v, dict):
            entry = v
        else:
            entry = {"text": _join_text(v)}

        payload = {
            "text":       str(entry.get("text", "")).strip(),
            "emotion":    entry.get("emotion", None),
            "hearts":     entry.get("hearts", 0),
            "quest":      entry.get("quest", None),
            "item":       entry.get("item", None),
            "itemAmount": entry.get("itemAmount", None),
        }

        if not suf:
            response_base_by_num[num] = payload
        elif len(suf) > 1:
            for ch in suf:
                response_by_num_suffix[(num, ch)] = payload
        else:
            response_by_num_suffix[(num, suf)] = payload

    return response_by_num_suffix, response_base_by_num


def _select_dialogue_text(cycle_obj: Dict[str, Any]) -> str:
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
    return _join_text(cycle_obj.get(candidates[0][1]))


def _append_response_extras(
    response_text: str,
    npc_name: str,
    resp: Optional[dict],
    quest_name_map: dict,
) -> str:
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

# ---------------------------------------------------------------------------
# Cycle renderer
# ---------------------------------------------------------------------------

def _render_cycle(
    npc: str, cycle_key: str, cycle_obj: Dict[str, Any], quest_name_map: dict
) -> str:
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

    options.sort(key=lambda t: (t[0], 0 if t[1] == "" else 1, t[1]))

    lines: List[str] = [
        "{{Conversation dialogue|npc = " + npc,
        f"|title = {_cycle_title(cycle_key)}",
        "|Dialogue = " + dialogue_text,
    ]

    emitted_emotion: set[str] = set()

    for num, suf, raw_key in options:
        opt_text = _join_text(cycle_obj.get(raw_key))

        hearts = 0
        resp: Optional[dict] = None

        if suf:
            resp = response_by_num_suffix.get((num, suf))
        else:
            resp = response_base_by_num.get(num)
        if resp:
            hearts = resp.get("hearts", 0)

        opt_text_with_hearts = opt_text + _heart_suffix(hearts)
        indent = "   " if suf else ""
        lines.append(f"{indent}|Option{num}{suf} = {opt_text_with_hearts}")

        response_text = ""
        emotion_text  = ""

        if resp:
            response_text = resp.get("text", "")
            emotion_text  = _emotion_value(resp.get("emotion", None))

        if response_text:
            response_text = _append_response_extras(response_text, npc, resp, quest_name_map)
            lines.append(f"{indent}{indent}|Response{num}{suf} = {response_text}")

            emotion_param = f"Response{num}{suf}Emotion"
            if emotion_param not in emitted_emotion:
                lines.append(f"{indent}{indent}|{emotion_param} = {emotion_text}")
                emitted_emotion.add(emotion_param)

    lines.append("}}")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    os.makedirs(_OUTPUT_FOLDER, exist_ok=True)

    data: Dict[str, Any] = json_utils.load_json(_INPUT_JSON)
    if not isinstance(data, dict):
        raise ValueError(f"Expected top-level dict in {_INPUT_JSON}, got {type(data)}")

    quest_name_map = _load_quest_name_map()
    written = 0

    for npc_name in sorted(data.keys(), key=lambda s: s.lower()):
        npc_obj = data.get(npc_name, {})
        if not isinstance(npc_obj, dict):
            continue

        cycles_obj = npc_obj.get("cycles")
        npc_cycles = cycles_obj if isinstance(cycles_obj, dict) else npc_obj

        cycle_keys = [k for k in npc_cycles.keys() if isinstance(k, str) and k.startswith("Cycle")]
        cycle_keys.sort(key=_cycle_sort_key)

        blocks: List[str] = []
        for ck in cycle_keys:
            cycle_obj = npc_cycles.get(ck, {})
            if isinstance(cycle_obj, dict):
                blocks.append(_render_cycle(npc_name, ck, cycle_obj, quest_name_map))

        if not blocks:
            continue

        out_path = os.path.join(_OUTPUT_FOLDER, f"{npc_name} cycles.txt")
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n\n".join(blocks).strip() + "\n")

        written += 1

    print(f"✅ Wrote {written} NPC cycle files to: {_OUTPUT_FOLDER}")


if __name__ == "__main__":
    run()
