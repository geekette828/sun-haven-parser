"""
Parse English.prefab and extract ALL NPC dialogue into one file:

- NPC / RNPC / TNPC cycles (Cycle00, CycleP6, etc.)
- One-liners (OL, Dating, Proposal, MLP)
- Wedding dialogue:
    Wedding.Vows.NPCNAME
    Wedding.Speech.NPCNAME

Output:
  npc_dialogue.json
"""

import os
import sys
import re
import logging
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")

import config.constants as constants
from utils import json_utils, file_utils
from utils.text_utils import clean_game_dialogue
from utils.guid_utils import extract_guid

# Paths
INPUT_PREFAB_PATH = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")
OUTPUT_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "npc_dialogue.json")

monobehaviour_directory = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")

debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "json", "npc_dialogue_debug.txt")
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

logging.basicConfig(
    filename=debug_log_path,
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s"
)


# Prefab parsing helpers
TERM_RE = re.compile(r"^\s*-\s*Term:\s*(.+?)\s*$")
LANGUAGES_HEADER_RE = re.compile(r"^\s*Languages:\s*$")
LANG_ITEM_RE = re.compile(r"^\s*-\s*(.*)\s*$")


def is_description_key(term: str) -> bool:
    return term.lower().endswith(".description")


def decode_yaml_scalar(value: str) -> str:
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


def extract_term_english_pairs(prefab_path: str) -> List[Tuple[str, str]]:
    pairs = []
    current_term = None
    waiting_for_lang = False

    with open(prefab_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m_term = TERM_RE.match(line)
            if m_term:
                current_term = m_term.group(1).strip()
                waiting_for_lang = False
                continue

            if current_term and LANGUAGES_HEADER_RE.match(line):
                waiting_for_lang = True
                continue

            if current_term and waiting_for_lang:
                m_lang = LANG_ITEM_RE.match(line)
                if m_lang:
                    raw = decode_yaml_scalar(m_lang.group(1))
                    text = clean_game_dialogue(raw)
                    pairs.append((current_term, text))
                waiting_for_lang = False

    return pairs



# Cycle extraction
CYCLE_RE = re.compile(r"^(TNPC|RNPC|NPC)\.([^.]+)\.(Cycle[^.]+)\.(.+)$", re.IGNORECASE)
TAIL_RE = re.compile(r"^(D|O|R)(\d+)?([A-Za-z]*)$", re.IGNORECASE)


def tail_sort_key(tail: str):
    m = TAIL_RE.match(tail or "")
    if not m:
        return (9, tail.lower())

    kind, num, suffix = m.group(1), m.group(2), m.group(3) or ""
    return (0 if kind == "D" else 1, int(num or 0), suffix.lower())


def cycle_sort_key(cycle: str):
    m = re.match(r"^Cycle(\d+)$", cycle, re.IGNORECASE)
    if m:
        return (0, int(m.group(1)))
    return (1, cycle.lower())


def build_cycles(pairs):
    out = {}

    for term, text in pairs:
        if not term or is_description_key(term):
            continue

        m = CYCLE_RE.match(term)
        if not m:
            continue

        npc, cycle, tail = m.group(2), m.group(3), m.group(4)

        out.setdefault(npc, {}).setdefault(cycle, {}).setdefault(tail, []).append({
            "term": term,
            "text": text
        })

    return out


def sort_cycles(data):
    ordered = {}
    for npc in sorted(data, key=str.lower):
        ordered[npc] = {}
        for cycle in sorted(data[npc], key=cycle_sort_key):
            tails = data[npc][cycle]
            ordered[npc][cycle] = {
                t: tails[t] for t in sorted(tails, key=tail_sort_key)
            }
    return ordered


# MonoBehaviour cycle metadata (emotion / hearts / quest / item)
BLOCK_HEADER_RE = re.compile(r"^  ([A-Za-z0-9_]+)\s*:\s*$")
BLOCK_KV_RE = re.compile(r"^    ([A-Za-z0-9_]+)\s*:\s*(.*)\s*$")


def parse_cycle_asset_file(path):
    records = []
    block = None
    data = {}

    def flush():
        if block and "keyResponse" in data and "emotion" in data and "hearts" in data:
            records.append({
                "keyResponse": data.get("keyResponse"),
                "keyOption": data.get("keyOption"),
                "emotion": data["emotion"],
                "hearts": data["hearts"],
                "quest": data.get("quest"),
                "item": data.get("item"),
                "itemAmount": data.get("itemAmount"),
            })
        data.clear()

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m_block = BLOCK_HEADER_RE.match(line)
            if m_block:
                flush()
                block = m_block.group(1)
                continue

            m_kv = BLOCK_KV_RE.match(line)
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


def enrich_cycles(cycles):
    term_index = {}
    for npc in cycles.values():
        for cycle in npc.values():
            for entries in cycle.values():
                for e in entries:
                    term_index.setdefault(e["term"], []).append(e)

    for root, _, files in os.walk(monobehaviour_directory):
        for f in files:
            if f.lower().endswith(".asset") and "cycle" in f.lower():
                for rec in parse_cycle_asset_file(os.path.join(root, f)):
                    key = rec.get("keyResponse") or rec.get("keyOption")
                    if key in term_index:
                        for e in term_index[key]:
                            e["emotion"] = rec["emotion"]
                            e["hearts"] = rec["hearts"]
                            if rec.get("quest"):
                                e["quest"] = rec["quest"]
                            if rec.get("item"):
                                e["item"] = rec["item"]
                                e["itemAmount"] = rec.get("itemAmount")



# One-liners
ONE_LINER_RE = re.compile(r"^(RNPC|NPC)\.([^.]+)\.OL(?:(\d+)|(?:\.([^.]+)))?$", re.IGNORECASE)
TNPC_OL_RE = re.compile(r"^TNPC\.([^.]+)(?:\.OL\d+)?$", re.IGNORECASE)
EXTRA_RNPC_RE = re.compile(
    r"^RNPC\.([^.]+)\.(Dating\.Accept|Dating\.Decline|AcceptProposal|DeclineProposal|MLP)(?:\.?(.+))?$",
    re.IGNORECASE
)


def build_one_liners(pairs):
    out = {}

    for term, text in pairs:
        if not term or is_description_key(term):
            continue

        m = ONE_LINER_RE.match(term)
        if m:
            npc = m.group(2)
            bucket = "Unconditional" if m.group(3) else (m.group(4) or "Other")
            out.setdefault(npc, {}).setdefault(bucket, []).append({"term": term, "text": text})
            continue

        m2 = TNPC_OL_RE.match(term)
        if m2:
            npc = m2.group(1)
            out.setdefault(npc, {}).setdefault("Unconditional", []).append({"term": term, "text": text})
            continue

        m3 = EXTRA_RNPC_RE.match(term)
        if m3:
            npc = m3.group(1)
            bucket = m3.group(3) or "Unconditional"
            out.setdefault(npc, {}).setdefault(bucket, []).append({"term": term, "text": text})

    return out


# Wedding dialogue
WEDDING_VOWS_RE = re.compile(r"^Wedding\.Vows\.([^.]+)$", re.IGNORECASE)
WEDDING_SPEECH_RE = re.compile(r"^Wedding\.Speech\.([^.]+)$", re.IGNORECASE)


def build_wedding(pairs):
    out = {}

    for term, text in pairs:
        m = WEDDING_VOWS_RE.match(term)
        if m:
            out.setdefault(m.group(1), {})["vows"] = {"term": term, "text": text}
            continue

        m2 = WEDDING_SPEECH_RE.match(term)
        if m2:
            out.setdefault(m2.group(1), {})["speech"] = {"term": term, "text": text}

    return out


# Main
def main():
    pairs = extract_term_english_pairs(INPUT_PREFAB_PATH)

    cycles = build_cycles(pairs)
    enrich_cycles(cycles)
    cycles = sort_cycles(cycles)

    one_liners = build_one_liners(pairs)
    wedding = build_wedding(pairs)

    all_npcs = sorted(set(cycles) | set(one_liners) | set(wedding), key=str.lower)

    output = {}
    for npc in all_npcs:
        output[npc] = {
            "cycles": cycles.get(npc, {}),
            "one_liners": one_liners.get(npc, {}),
            "wedding": wedding.get(npc, {}),
        }

    json_utils.write_json(output, OUTPUT_JSON_PATH, indent=2, ensure_ascii=False, sort_keys=False)

    print(f"✅ NPCs written: {len(output)}")
    print(f"📄 Output: {OUTPUT_JSON_PATH}")
    print(f"🛠 Debug log: {debug_log_path}")


if __name__ == "__main__":
    main()
