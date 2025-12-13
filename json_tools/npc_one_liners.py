"""
Parse English.prefab (Unity YAML / I2 Localization style) and extract NPC one-liners.

Rules:
- One-liners are keys matching: NPC.<Name>.OL[.<Condition>] or RNPC.<Name>.OL[.<Condition>]
- Ignore any key ending with .description (case-insensitive)
- Normalize condition by removing trailing digits: Spring1/Spring2 -> Spring, Dating4 -> Dating
- Group output by NPC, then by condition bucket (including "Unconditional")
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

# Define paths
INPUT_PREFAB_PATH = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")
OUTPUT_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "npc_one_liners.json")
debug_directory = os.path.join(constants.DEBUG_DIRECTORY, "json")

TERM_RE = re.compile(r"^\s*-\s*Term:\s*(.+?)\s*$")
LANGUAGES_HEADER_RE = re.compile(r"^\s*Languages:\s*$")
LANG_ITEM_RE = re.compile(r"^\s*-\s*(.*)\s*$")

ONE_LINER_RE = re.compile(r"^(RNPC|NPC)\.([^.]+)\.OL(?:\.([^.]+))?$", re.IGNORECASE)
TNPC_ONE_LINER_RE = re.compile(r"^TNPC\.([^.]+)(?:\.OL(\d+))?$", re.IGNORECASE) # TNPC has different shapes:
TRAILING_DIGITS_RE = re.compile(r"\d+$")


def is_description_key(term: str) -> bool:
    return term.strip().lower().endswith(".description")


def normalize_condition(cond: Optional[str]) -> str:
    if not cond:
        return "Unconditional"
    cond = cond.strip()
    cond = TRAILING_DIGITS_RE.sub("", cond)
    cond = cond.strip()
    return cond if cond else "Other"


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


def build_one_liners(pairs: List[Tuple[str, str]]) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
    out: Dict[str, Dict[str, List[Dict[str, str]]]] = {}

    for term, text in pairs:
        if not term or is_description_key(term):
            continue

        # NPC/RNPC: ... .OL[.Condition]
        m = ONE_LINER_RE.match(term)
        if m:
            npc = m.group(2)
            cond_raw = m.group(3)
            bucket = normalize_condition(cond_raw)

            npc_map = out.setdefault(npc, {})
            npc_map.setdefault(bucket, []).append({"term": term, "text": text})
            continue

        # TNPC: TNPC.<Name> or TNPC.<Name>.OL#
        m2 = TNPC_ONE_LINER_RE.match(term)
        if m2:
            npc = m2.group(1)
            # TNPC OL1/OL2 are just multiple one-liners, not conditions
            bucket = "Unconditional"

            npc_map = out.setdefault(npc, {})
            npc_map.setdefault(bucket, []).append({"term": term, "text": text})
            continue

    return out

def main() -> None:
    if not os.path.exists(INPUT_PREFAB_PATH):
        raise FileNotFoundError(f"Input prefab not found: {INPUT_PREFAB_PATH}")

    os.makedirs(debug_directory, exist_ok=True)

    pairs = extract_term_english_pairs(INPUT_PREFAB_PATH)
    one_liners = build_one_liners(pairs)

    # Sort NPC keys and condition keys for stable diffs
    one_liners = json_utils.sort_nested(one_liners)

    # Stable ordering: Unconditional first, then alphabetical conditions
    ordered = {}
    for npc in sorted(one_liners.keys(), key=lambda s: s.lower()):
        buckets = one_liners[npc]
        bucket_order = sorted(buckets.keys(), key=lambda s: (s != "Unconditional", s.lower()))
        ordered[npc] = {b: buckets[b] for b in bucket_order}

    json_utils.write_json(ordered, OUTPUT_JSON_PATH, indent=2, ensure_ascii=False, sort_keys=False)

    npc_count = len(ordered)
    line_count = sum(len(lines) for npc_data in ordered.values() for lines in npc_data.values())
    print(f"✅ Extracted {line_count} one-liners across {npc_count} NPCs")
    print(f"✅ Wrote: {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    main()
