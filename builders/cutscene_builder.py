"""
Cutscene / conversation builder — Layer 1 of the pipeline.

Parses English.prefab and extracts non-NPC cutscene and conversation
dialogue into cutscenes_convos.json.

NPC dialogue (NPC. / RNPC. prefixes) is handled by npc_dialogue_builder.py.

Usage:
    python builders/cutscene_builder.py
"""

from __future__ import annotations

import os
import re
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")

import config.constants as constants
from utils import json_utils
from utils.text_utils import clean_game_dialogue

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_INPUT_PREFAB = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")
_CACHE_FILE   = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "cutscenes_convos.json")

# ---------------------------------------------------------------------------
# Regex constants
# ---------------------------------------------------------------------------

_TERM_RE             = re.compile(r"^\s*-\s*Term:\s*(.+?)\s*$")
_LANGUAGES_HEADER_RE = re.compile(r"^\s*Languages:\s*$")
_LANG_ITEM_RE        = re.compile(r"^\s*-\s*(.*)\s*$")
_NPC_PREFIX_RE       = re.compile(r"^(R?NPC)\.", re.IGNORECASE)
_TAIL_RE             = re.compile(r"^(D|O|R)(\d+)?([A-Za-z]*)$", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_description_key(term: str) -> bool:
    return term.strip().lower().endswith(".description")


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


def _extract_term_english_pairs(prefab_path: str) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    current_term: Optional[str] = None
    waiting_for_lang = False

    with open(prefab_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m_term = _TERM_RE.match(line)
            if m_term:
                current_term = m_term.group(1).strip()
                waiting_for_lang = False
                continue

            if current_term and _LANGUAGES_HEADER_RE.match(line):
                waiting_for_lang = True
                continue

            if current_term and waiting_for_lang:
                m_lang = _LANG_ITEM_RE.match(line)
                if m_lang:
                    english = clean_game_dialogue(_decode_yaml_scalar(m_lang.group(1)))
                    pairs.append((current_term, english))
                waiting_for_lang = False

    return pairs


def _split_scene_and_tail(term: str) -> Optional[Tuple[str, str]]:
    if "." not in term:
        return None
    scene_key, tail = term.rsplit(".", 1)
    if not scene_key or not tail:
        return None
    if not _TAIL_RE.match(tail.strip()):
        return None
    return scene_key, tail.strip()


def _tail_sort_key(tail: str):
    t = (tail or "").strip()
    m = _TAIL_RE.match(t)
    if not m:
        return (9, 9_999_999, 9_999_999, 9_999_999, t.lower())

    kind     = m.group(1).upper()
    num_str  = m.group(2) or "0"
    suffix   = (m.group(3) or "").lower()

    try:
        num = int(num_str)
    except ValueError:
        num = 9_999_999

    if kind == "D":
        return (0, num, 0, 0, t.lower())

    kind_rank   = 0 if kind == "O" else 1
    suffix_rank = 0
    for ch in suffix:
        if "a" <= ch <= "z":
            suffix_rank = suffix_rank * 26 + (ord(ch) - ord("a") + 1)
        else:
            suffix_rank = 9_999_999

    return (1, num, suffix_rank, kind_rank, t.lower())


def _build_cutscenes(pairs: List[Tuple[str, str]]) -> Dict[str, Dict[str, List[dict]]]:
    out: Dict[str, Dict[str, List[dict]]] = {}

    for term, text in pairs:
        if not term or _is_description_key(term):
            continue
        if _NPC_PREFIX_RE.match(term):
            continue

        split = _split_scene_and_tail(term)
        if not split:
            continue

        scene_key, tail = split
        out.setdefault(scene_key, {}).setdefault(tail, []).append({"term": term, "text": text})

    return out


def _sort_scenes(data: Dict[str, Dict[str, List[dict]]]) -> Dict[str, Dict[str, List[dict]]]:
    ordered = {}
    for scene_key in sorted(data.keys(), key=lambda s: s.lower()):
        tails = data[scene_key]
        ordered[scene_key] = {t: tails[t] for t in sorted(tails.keys(), key=_tail_sort_key)}
    return ordered


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    if not os.path.exists(_INPUT_PREFAB):
        print(f"❌ Input prefab not found: {_INPUT_PREFAB}")
        return

    os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)

    pairs  = _extract_term_english_pairs(_INPUT_PREFAB)
    scenes = _build_cutscenes(pairs)
    scenes = _sort_scenes(scenes)

    json_utils.write_json(scenes, _CACHE_FILE, indent=2, ensure_ascii=False, sort_keys=False)

    line_count  = sum(len(entries) for scene in scenes.values() for entries in scene.values())
    scene_count = len(scenes)
    print(f"✅ {line_count} cutscene/convo lines across {scene_count} scenes written to {_CACHE_FILE}")


if __name__ == "__main__":
    run()
