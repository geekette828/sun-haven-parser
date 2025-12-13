"""
Parse English.prefab (Unity YAML / I2 Localization style) and extract non-NPC cutscenes/conversations.

Rules:
- Only include keys where the final segment (after the last dot) matches dialogue tails:
  D / D7, O1 / O1a / O2b, R1 / R1a / R2b, etc.
- Ignore any key ending with .description (case-insensitive)
- Ignore any key starting with NPC. or RNPC. (those are handled by one-liners/cycles)
- Group output by "scene key" (everything before the last .Tail), then by Tail
- Dialogue cleaning uses utils.text_utils.clean_game_dialogue()
"""

import os
import sys
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")

import config.constants as constants
from typing import Dict, List, Optional, Tuple
from utils import json_utils
from utils.text_utils import clean_game_dialogue


# Paths
INPUT_PREFAB_PATH = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")
OUTPUT_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "cutscenes_convos.json")
debug_directory = os.path.join(constants.DEBUG_DIRECTORY, "json")

TERM_RE = re.compile(r"^\s*-\s*Term:\s*(.+?)\s*$")
LANGUAGES_HEADER_RE = re.compile(r"^\s*Languages:\s*$")
LANG_ITEM_RE = re.compile(r"^\s*-\s*(.*)\s*$")

NPC_PREFIX_RE = re.compile(r"^(R?NPC)\.", re.IGNORECASE)

# Tail token must be one of these shapes:
# D, D7, O1, O1a, O2b, R1, R1a, R2b, ...
TAIL_RE = re.compile(r"^(D|O|R)(\d+)?([A-Za-z]*)$", re.IGNORECASE)


def is_description_key(term: str) -> bool:
    return term.strip().lower().endswith(".description")


def decode_yaml_scalar(value: str) -> str:
    """
    Handles common Unity/YAML scalar cases seen in I2 localization dumps:
    - Plain scalars
    - Single-quoted scalars: 'It''s fine' -> It's fine
    - Double-quoted scalars: "Hello \"there\"" -> Hello "there"
    """
    v = value.strip()

    if len(v) >= 2 and v[0] == "'" and v[-1] == "'":
        inner = v[1:-1]
        inner = inner.replace("''", "'")  # YAML single-quote escaping
        return inner

    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        inner = v[1:-1]
        inner = inner.replace(r"\\", "\\").replace(r"\"", '"').replace(r"\n", "\n").replace(r"\t", "\t")
        return inner

    return v


def extract_term_english_pairs(prefab_path: str) -> List[Tuple[str, str]]:
    """
    Stream-scan the prefab and yield (term, english_text) pairs.
    Assumption: English is the first entry under `Languages:` for each term.
    """
    pairs: List[Tuple[str, str]] = []

    current_term: Optional[str] = None
    waiting_for_language_value = False

    with open(prefab_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m_term = TERM_RE.match(line)
            if m_term:
                current_term = m_term.group(1).strip()
                waiting_for_language_value = False
                continue

            if current_term and LANGUAGES_HEADER_RE.match(line):
                waiting_for_language_value = True
                continue

            if current_term and waiting_for_language_value:
                m_lang = LANG_ITEM_RE.match(line)
                if m_lang:
                    raw_value = m_lang.group(1)
                    english_raw = decode_yaml_scalar(raw_value)
                    english = clean_game_dialogue(english_raw)
                    pairs.append((current_term, english))
                waiting_for_language_value = False
                continue

    return pairs


def split_scene_and_tail(term: str) -> Optional[Tuple[str, str]]:
    """
    Returns (scene_key, tail) if the term ends with a valid dialogue tail token.
    Example: "AHerosHarvest1B.D7" -> ("AHerosHarvest1B", "D7")
    """
    if "." not in term:
        return None
    scene_key, tail = term.rsplit(".", 1)
    if not scene_key or not tail:
        return None
    if not TAIL_RE.match(tail.strip()):
        return None
    return scene_key, tail.strip()


def tail_sort_key(tail: str):
    """
    Sort tails like:
      D / D7 first (numeric D ordered)
      then O before R, ordered by number then suffix ("" then a then b...)
    """
    t = (tail or "").strip()
    m = TAIL_RE.match(t)
    if not m:
        return (9, 9_999_999, 9_999_999, 9_999_999, t.lower())

    kind = m.group(1).upper()      # D/O/R
    num_str = m.group(2) or "0"
    suffix = (m.group(3) or "").lower()

    try:
        num = int(num_str)
    except ValueError:
        num = 9_999_999

    if kind == "D":
        # D first; D0 (plain D) before D1/D2...
        return (0, num, 0, 0, t.lower())

    kind_rank = 0 if kind == "O" else 1  # O before R

    if suffix == "":
        suffix_rank = 0
    else:
        suffix_rank = 0
        for ch in suffix:
            if "a" <= ch <= "z":
                suffix_rank = suffix_rank * 26 + (ord(ch) - ord("a") + 1)
            else:
                suffix_rank = 9_999_999

    return (1, num, suffix_rank, kind_rank, t.lower())


def build_cutscenes_convos(
    pairs: List[Tuple[str, str]]
) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
    """
    Returns:
    {
      "AHerosHarvest1B": {
        "D7":  [ {"term": "AHerosHarvest1B.D7", "text": "..."} ],
        "O1a": [ ... ],
        "R1a": [ ... ]
      },
      ...
    }
    """
    out: Dict[str, Dict[str, List[Dict[str, str]]]] = {}

    for term, text in pairs:
        if not term or is_description_key(term):
            continue

        # Exclude NPC/RNPC content; handled elsewhere
        if NPC_PREFIX_RE.match(term):
            continue

        split = split_scene_and_tail(term)
        if not split:
            continue

        scene_key, tail = split

        scene_map = out.setdefault(scene_key, {})
        scene_map.setdefault(tail, []).append({"term": term, "text": text})

    return out


def sort_scenes(data: Dict[str, Dict[str, List[Dict[str, str]]]]):
    """
    Deterministic ordering:
    - Scene keys alphabetically (case-insensitive)
    - Tails ordered with tail_sort_key (D first, then O/R flow)
    """
    ordered = {}
    for scene_key in sorted(data.keys(), key=lambda s: s.lower()):
        tails = data[scene_key]
        ordered[scene_key] = {t: tails[t] for t in sorted(tails.keys(), key=tail_sort_key)}
    return ordered


def main() -> None:
    if not os.path.exists(INPUT_PREFAB_PATH):
        raise FileNotFoundError(f"Input prefab not found: {INPUT_PREFAB_PATH}")

    os.makedirs(debug_directory, exist_ok=True)

    pairs = extract_term_english_pairs(INPUT_PREFAB_PATH)
    scenes = build_cutscenes_convos(pairs)
    scenes = sort_scenes(scenes)

    json_utils.write_json(scenes, OUTPUT_JSON_PATH, indent=2, ensure_ascii=False, sort_keys=False)

    scene_count = len(scenes)
    line_count = sum(len(entries) for scene in scenes.values() for entries in scene.values())

    print(f"✅ Extracted {line_count} cutscene/convo lines across {scene_count} scene keys")
    print(f"✅ Wrote: {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    main()
