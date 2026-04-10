"""
NPC dialogue builder — Layer 1 of the pipeline.

Parses English.prefab and MonoBehaviour cycle .asset files to extract all
NPC dialogue (cycles, one-liners, wedding vows/speeches) into npc_dialogue.json.

Usage:
    python builders/npc_dialogue_builder.py
"""

from __future__ import annotations

import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")

import config.constants as constants
from utils import json_utils, file_utils
from utils.text_utils import clean_game_dialogue
from utils.guid_utils import extract_guid

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_INPUT_PREFAB      = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")
_MONOBEHAVIOUR_DIR = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
_CACHE_FILE        = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "npc_dialogue.json")
_DEBUG_LOG         = os.path.join(constants.DEBUG_DIRECTORY, "json", "npc_dialogue_debug.txt")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("npc_dialogue_builder")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    file_utils.ensure_dir_exists(os.path.dirname(_DEBUG_LOG))
    handler = logging.FileHandler(_DEBUG_LOG, mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
    return logger

_log = _setup_logger()

# ---------------------------------------------------------------------------
# Regex constants
# ---------------------------------------------------------------------------

_TERM_RE             = re.compile(r"^\s*-\s*Term:\s*(.+?)\s*$")
_LANGUAGES_HEADER_RE = re.compile(r"^\s*Languages:\s*$")
_LANG_ITEM_RE        = re.compile(r"^\s*-\s*(.*)\s*$")
_CYCLE_RE            = re.compile(r"^(TNPC|RNPC|NPC)\.([^.]+)\.(Cycle[^.]+)\.(.+)$", re.IGNORECASE)
_TAIL_RE             = re.compile(r"^(D|O|R)(\d+)?([A-Za-z]*)$", re.IGNORECASE)
_ONE_LINER_RE        = re.compile(r"^(RNPC|NPC)\.([^.]+)\.OL(?:(\d+)|(?:\.([^.]+)))?$", re.IGNORECASE)
_TNPC_OL_RE          = re.compile(r"^TNPC\.([^.]+)(?:\.OL\d+)?$", re.IGNORECASE)
_EXTRA_RNPC_RE       = re.compile(
    r"^RNPC\.([^.]+)\.(Dating\.Accept|Dating\.Decline|AcceptProposal|DeclineProposal|MLP)(?:\.?(.+))?$",
    re.IGNORECASE,
)
_WEDDING_VOWS_RE   = re.compile(r"^Wedding\.Vows\.([^.]+)$", re.IGNORECASE)
_WEDDING_SPEECH_RE = re.compile(r"^Wedding\.Speech\.([^.]+)$", re.IGNORECASE)
_BLOCK_HEADER_RE   = re.compile(r"^  ([A-Za-z0-9_]+)\s*:\s*$")
_BLOCK_KV_RE       = re.compile(r"^    ([A-Za-z0-9_]+)\s*:\s*(.*)\s*$")

# ---------------------------------------------------------------------------
# Prefab parsing
# ---------------------------------------------------------------------------

def _is_description_key(term: str) -> bool:
    return term.lower().endswith(".description")


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
                    text = clean_game_dialogue(_decode_yaml_scalar(m_lang.group(1)))
                    pairs.append((current_term, text))
                waiting_for_lang = False

    return pairs

# ---------------------------------------------------------------------------
# Cycle building
# ---------------------------------------------------------------------------

def _tail_sort_key(tail: str):
    m = _TAIL_RE.match(tail or "")
    if not m:
        return (9, tail.lower())
    kind, num, suffix = m.group(1), m.group(2), m.group(3) or ""
    return (0 if kind == "D" else 1, int(num or 0), suffix.lower())


def _cycle_sort_key(cycle: str):
    m = re.match(r"^Cycle(\d+)$", cycle, re.IGNORECASE)
    if m:
        return (0, int(m.group(1)))
    return (1, cycle.lower())


def _build_cycles(pairs: List[Tuple[str, str]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for term, text in pairs:
        if not term or _is_description_key(term):
            continue
        m = _CYCLE_RE.match(term)
        if not m:
            continue
        npc, cycle, tail = m.group(2), m.group(3), m.group(4)
        out.setdefault(npc, {}).setdefault(cycle, {}).setdefault(tail, []).append(
            {"term": term, "text": text}
        )
    return out


def _sort_cycles(data: Dict[str, Any]) -> Dict[str, Any]:
    ordered = {}
    for npc in sorted(data, key=str.lower):
        ordered[npc] = {}
        for cycle in sorted(data[npc], key=_cycle_sort_key):
            tails = data[npc][cycle]
            ordered[npc][cycle] = {t: tails[t] for t in sorted(tails, key=_tail_sort_key)}
    return ordered

# ---------------------------------------------------------------------------
# Cycle metadata enrichment from MonoBehaviour .asset files
# ---------------------------------------------------------------------------

def _parse_cycle_asset_file(path: str) -> List[dict]:
    records = []
    block = None
    data: dict = {}

    def flush():
        if block and "keyResponse" in data and "emotion" in data and "hearts" in data:
            records.append({
                "keyResponse": data.get("keyResponse"),
                "keyOption":   data.get("keyOption"),
                "emotion":     data["emotion"],
                "hearts":      data["hearts"],
                "quest":       data.get("quest"),
                "item":        data.get("item"),
                "itemAmount":  data.get("itemAmount"),
            })
        data.clear()

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m_block = _BLOCK_HEADER_RE.match(line)
            if m_block:
                flush()
                block = m_block.group(1)
                continue
            m_kv = _BLOCK_KV_RE.match(line)
            if not m_kv:
                continue
            key, value = m_kv.group(1), m_kv.group(2).strip()
            if key == "keyResponse":
                data["keyResponse"] = value
            elif key == "keyOption":
                data["keyOption"] = value
            elif key == "optionEmotion":
                data["emotion"] = int(value)
            elif key == "optionHearts":
                data["hearts"] = int(value)
            elif key == "optionQuest":
                data["quest"] = extract_guid(value)
            elif key == "optionItem":
                data["item"] = value
            elif key == "optionItemAmt":
                data["itemAmount"] = int(value)

    flush()
    return records


def _enrich_cycles(cycles: Dict[str, Any]) -> None:
    term_index: Dict[str, list] = {}
    for npc in cycles.values():
        for cycle in npc.values():
            for entries in cycle.values():
                for e in entries:
                    term_index.setdefault(e["term"], []).append(e)

    for root, _, files in os.walk(_MONOBEHAVIOUR_DIR):
        for f in files:
            if f.lower().endswith(".asset") and "cycle" in f.lower():
                for rec in _parse_cycle_asset_file(os.path.join(root, f)):
                    key = rec.get("keyResponse") or rec.get("keyOption")
                    if key in term_index:
                        for e in term_index[key]:
                            e["emotion"] = rec["emotion"]
                            e["hearts"]  = rec["hearts"]
                            if rec.get("quest"):
                                e["quest"] = rec["quest"]
                            if rec.get("item"):
                                e["item"]       = rec["item"]
                                e["itemAmount"] = rec.get("itemAmount")

# ---------------------------------------------------------------------------
# One-liners
# ---------------------------------------------------------------------------

def _build_one_liners(pairs: List[Tuple[str, str]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for term, text in pairs:
        if not term or _is_description_key(term):
            continue
        m = _ONE_LINER_RE.match(term)
        if m:
            npc    = m.group(2)
            bucket = "Unconditional" if m.group(3) else (m.group(4) or "Other")
            out.setdefault(npc, {}).setdefault(bucket, []).append({"term": term, "text": text})
            continue
        m2 = _TNPC_OL_RE.match(term)
        if m2:
            out.setdefault(m2.group(1), {}).setdefault("Unconditional", []).append({"term": term, "text": text})
            continue
        m3 = _EXTRA_RNPC_RE.match(term)
        if m3:
            npc    = m3.group(1)
            bucket = m3.group(3) or "Unconditional"
            out.setdefault(npc, {}).setdefault(bucket, []).append({"term": term, "text": text})
    return out

# ---------------------------------------------------------------------------
# Wedding dialogue
# ---------------------------------------------------------------------------

def _build_wedding(pairs: List[Tuple[str, str]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for term, text in pairs:
        m = _WEDDING_VOWS_RE.match(term)
        if m:
            out.setdefault(m.group(1), {})["vows"] = {"term": term, "text": text}
            continue
        m2 = _WEDDING_SPEECH_RE.match(term)
        if m2:
            out.setdefault(m2.group(1), {})["speech"] = {"term": term, "text": text}
    return out

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_CACHE_FILE))

    pairs = _extract_term_english_pairs(_INPUT_PREFAB)

    cycles = _build_cycles(pairs)
    _enrich_cycles(cycles)
    cycles = _sort_cycles(cycles)

    one_liners = _build_one_liners(pairs)
    wedding    = _build_wedding(pairs)

    all_npcs = sorted(set(cycles) | set(one_liners) | set(wedding), key=str.lower)

    output = {
        npc: {
            "cycles":     cycles.get(npc, {}),
            "one_liners": one_liners.get(npc, {}),
            "wedding":    wedding.get(npc, {}),
        }
        for npc in all_npcs
    }

    json_utils.write_json(output, _CACHE_FILE, indent=2, ensure_ascii=False, sort_keys=False)
    print(f"✅ {len(output)} NPCs written to {_CACHE_FILE}")


if __name__ == "__main__":
    run()
