"""
Parse English.prefab (Unity YAML / I2 Localization style) and extract NPC cycles,
then enrich cycle entries with optionEmotion/optionHearts metadata from MonoBehaviour
cycle .asset files.

Rules:
- Cycles are keys matching: (TNPC|NPC|RNPC).<Name>.Cycle*.<Tail>
- Ignore any key ending with .description (case-insensitive)
- Group output by NPC, then by Cycle key (Cycle02, CycleP7, ...), then by Tail
- Dialogue cleaning uses utils.text_utils.clean_game_dialogue()

Metadata rules:
- Scan MonoBehaviour files whose filename contains "cycle" (case-insensitive)
- Extract blocks (block1, block2a, etc.) that contain keyOption/keyResponse and optionEmotion/optionHearts
- Attach emotion/hearts to the NPC response term (keyResponse) when possible
- If response term is missing in extracted cycles JSON, attach to option term (keyOption)
- Conflicts within the same run: keep first applied, log conflicts
"""

import os
import sys
import re
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")

import config.constants as constants
from typing import Dict, List, Optional, Tuple
from utils import json_utils, file_utils
from utils.text_utils import clean_game_dialogue


# Define paths
INPUT_PREFAB_PATH = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")
OUTPUT_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "npc_cycles.json")

monobehaviour_directory = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")

# Setup logging (matches your existing pattern)
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "json", "npc_cycles_debug.txt")
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))
logging.basicConfig(filename=debug_log_path, level=logging.DEBUG, format="%(levelname)s: %(message)s")


TERM_RE = re.compile(r"^\s*-\s*Term:\s*(.+?)\s*$")
LANGUAGES_HEADER_RE = re.compile(r"^\s*Languages:\s*$")
LANG_ITEM_RE = re.compile(r"^\s*-\s*(.*)\s*$")

# (TNPC|NPC|RNPC).<Name>.(Cycle[^.]+).<Tail>
CYCLE_RE = re.compile(r"^(TNPC|RNPC|NPC)\.([^.]+)\.(Cycle[^.]+)\.(.+)$", re.IGNORECASE)

# Tail token must be one of these shapes:
# D, D7, O1, O1a, O2b, R1, R1a, R2b, ...
TAIL_RE = re.compile(r"^(D|O|R)(\d+)?([A-Za-z]*)$", re.IGNORECASE)

# MonoBehaviour indentation-aware parsing:
# Dialogue blocks are at exactly 2 spaces indentation, e.g. "  block2a:"
BLOCK_HEADER_RE = re.compile(r"^  ([A-Za-z0-9_]+)\s*:\s*$")
# Block fields are at exactly 4 spaces indentation, e.g. "    optionEmotion: 2"
BLOCK_KV_RE = re.compile(r"^    ([A-Za-z0-9_]+)\s*:\s*(.*)\s*$")


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


def tail_sort_key(tail: str):
    t = (tail or "").strip()
    m = TAIL_RE.match(t)
    if not m:
        return (9, 9_999_999, 9_999_999, 9_999_999, t.lower())

    kind = m.group(1).upper()
    num_str = m.group(2) or "0"
    suffix = (m.group(3) or "").lower()

    try:
        num = int(num_str)
    except ValueError:
        num = 9_999_999

    if kind == "D":
        return (0, num, 0, 0, t.lower())

    kind_rank = 0 if kind == "O" else 1

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


def cycle_sort_key(cycle_key: str):
    c = (cycle_key or "").strip()
    m = re.match(r"^Cycle(\d+)$", c, flags=re.IGNORECASE)
    if m:
        return (0, int(m.group(1)), c.lower())
    return (1, 9_999_999, c.lower())


def build_cycles(pairs: List[Tuple[str, str]]) -> Dict[str, Dict[str, Dict[str, List[Dict[str, object]]]]]:
    out: Dict[str, Dict[str, Dict[str, List[Dict[str, object]]]]] = {}

    for term, text in pairs:
        if not term or is_description_key(term):
            continue

        m = CYCLE_RE.match(term)
        if not m:
            continue

        npc = m.group(2)
        cycle_key = m.group(3)
        tail = m.group(4).strip()

        npc_map = out.setdefault(npc, {})
        cycle_map = npc_map.setdefault(cycle_key, {})
        cycle_map.setdefault(tail, []).append({"term": term, "text": text})

    return out


def sort_cycles(data: Dict[str, Dict[str, Dict[str, List[Dict[str, object]]]]]):
    ordered = {}
    for npc in sorted(data.keys(), key=lambda s: s.lower()):
        npc_cycles = data[npc]
        ordered[npc] = {}

        for cycle_key in sorted(npc_cycles.keys(), key=cycle_sort_key):
            tails = npc_cycles[cycle_key]
            ordered[npc][cycle_key] = {t: tails[t] for t in sorted(tails.keys(), key=tail_sort_key)}

    return ordered


def index_entries_by_term(cycles: Dict[str, Dict[str, Dict[str, List[Dict[str, object]]]]]) -> Dict[str, List[Dict[str, object]]]:
    idx: Dict[str, List[Dict[str, object]]] = {}
    for npc_cycles in cycles.values():
        for cycle_map in npc_cycles.values():
            for entries in cycle_map.values():
                for entry in entries:
                    term = entry.get("term")
                    if isinstance(term, str) and term:
                        idx.setdefault(term, []).append(entry)
    return idx


def parse_cycle_asset_file(filepath: str) -> List[Dict[str, object]]:
    """
    Extract records from dialogue blocks:
      - keyOption
      - keyResponse
      - optionEmotion (int)
      - optionHearts (int)
    """
    records: List[Dict[str, object]] = []
    current_block: Optional[str] = None
    block_data: Dict[str, object] = {}

    def flush_block():
        nonlocal block_data, current_block
        if not current_block:
            block_data = {}
            return

        # Only consider dialogue blocks (block1, block2a, etc.)
        if not current_block.lower().startswith("block"):
            block_data = {}
            return

        if (
            "keyOption" in block_data
            and "keyResponse" in block_data
            and isinstance(block_data.get("emotion"), int)
            and isinstance(block_data.get("hearts"), int)
        ):
            records.append({
                "file": filepath,
                "block": current_block,
                "keyOption": block_data.get("keyOption"),
                "keyResponse": block_data.get("keyResponse"),
                "emotion": block_data.get("emotion"),
                "hearts": block_data.get("hearts"),
                "quest": block_data.get("quest"),
                "item": block_data.get("item"),
                "itemAmount": block_data.get("itemAmount"),
            })

        block_data = {}

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m_block = BLOCK_HEADER_RE.match(line)
                if m_block:
                    flush_block()
                    current_block = m_block.group(1)
                    continue

                m_kv = BLOCK_KV_RE.match(line)
                if not m_kv:
                    continue

                key = m_kv.group(1)
                value = m_kv.group(2).strip()

                if key == "keyOption":
                    block_data["keyOption"] = value
                elif key == "keyResponse":
                    block_data["keyResponse"] = value
                elif key == "optionEmotion":
                    try:
                        block_data["emotion"] = int(value)
                    except ValueError:
                        pass
                elif key == "optionHearts":
                    try:
                        block_data["hearts"] = int(value)
                    except ValueError:
                        pass
                elif key == "optionQuest":
                    from utils.guid_utils import extract_guid
                    guid = extract_guid(value)
                    if guid:
                        block_data["quest"] = guid
                elif key == "optionItem":
                    if value:
                        block_data["item"] = value
                elif key == "optionItemAmt":
                    try:
                        block_data["itemAmount"] = int(value)
                    except ValueError:
                        pass
        flush_block()
    except Exception as e:
        logging.debug(f"Failed to parse asset file '{filepath}': {e}")

    return records


def collect_cycle_asset_records(mono_dir: str) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []

    if not os.path.exists(mono_dir):
        logging.debug(f"MonoBehaviour directory not found: {mono_dir}")
        return records

    for root, _, files in os.walk(mono_dir):
        for filename in files:
            if "cycle" not in filename.lower():
                continue
            if not filename.lower().endswith(".asset"):
                continue

            path = os.path.join(root, filename)
            file_records = parse_cycle_asset_file(path)
            records.extend(file_records)

    return records


def apply_emotion_hearts(
    cycles: Dict[str, Dict[str, Dict[str, List[Dict[str, object]]]]],
    records: List[Dict[str, object]]
) -> None:
    term_index = index_entries_by_term(cycles)

    applied: Dict[str, Tuple[int, int, str]] = {}
    applied_count = 0
    fallback_count = 0
    missing_count = 0
    conflict_count = 0

    for rec in records:
        key_response = rec.get("keyResponse")
        key_option = rec.get("keyOption")
        emotion = rec.get("emotion")
        hearts = rec.get("hearts")
        src_file = rec.get("file")
        src_block = rec.get("block")

        if not isinstance(emotion, int) or not isinstance(hearts, int):
            continue

        source_label = f"{src_file}::{src_block}" if src_block else str(src_file)

        target_term = None
        fallback_used = False

        if isinstance(key_response, str) and key_response in term_index:
            target_term = key_response
        elif isinstance(key_option, str) and key_option in term_index:
            target_term = key_option
            fallback_used = True

        if not target_term:
            missing_count += 1
            logging.debug(
                f"Missing cycle entry for metadata. response='{key_response}' option='{key_option}' "
                f"emotion={emotion} hearts={hearts} source={source_label}"
            )
            continue

        if target_term in applied:
            prev_emotion, prev_hearts, prev_source = applied[target_term]
            if prev_emotion != emotion or prev_hearts != hearts:
                conflict_count += 1
                logging.debug(
                    f"Conflict for term='{target_term}'. Keeping first. "
                    f"first(emotion={prev_emotion}, hearts={prev_hearts}, source={prev_source}) "
                    f"new(emotion={emotion}, hearts={hearts}, source={source_label})"
                )
            continue

        for entry in term_index.get(target_term, []):
            entry["emotion"] = emotion
            entry["hearts"] = hearts
            
            if rec.get("quest"):
                entry["quest"] = rec["quest"]

            if rec.get("item"):
                entry["item"] = rec["item"]
                if isinstance(rec.get("itemAmount"), int):
                    entry["itemAmount"] = rec["itemAmount"]

        applied[target_term] = (emotion, hearts, source_label)
        applied_count += 1

        if fallback_used:
            fallback_count += 1
            logging.debug(
                f"Applied metadata to OPTION (response missing). term='{target_term}' "
                f"emotion={emotion} hearts={hearts} source={source_label}"
            )
        else:
            logging.debug(
                f"Applied metadata to RESPONSE. term='{target_term}' "
                f"emotion={emotion} hearts={hearts} source={source_label}"
            )

    logging.debug(
        f"Metadata merge summary: applied={applied_count}, fallback_to_option={fallback_count}, "
        f"missing={missing_count}, conflicts={conflict_count}"
    )


def main() -> None:
    if not os.path.exists(INPUT_PREFAB_PATH):
        raise FileNotFoundError(f"Input prefab not found: {INPUT_PREFAB_PATH}")

    pairs = extract_term_english_pairs(INPUT_PREFAB_PATH)
    cycles = build_cycles(pairs)

    records = collect_cycle_asset_records(monobehaviour_directory)
    logging.debug(f"Found {len(records)} cycle metadata records in MonoBehaviour assets.")
    apply_emotion_hearts(cycles, records)

    cycles = sort_cycles(cycles)

    json_utils.write_json(cycles, OUTPUT_JSON_PATH, indent=2, ensure_ascii=False, sort_keys=False)

    npc_count = len(cycles)
    cycle_count = sum(len(npc_cycles) for npc_cycles in cycles.values())
    line_count = sum(
        len(entries)
        for npc_cycles in cycles.values()
        for cycle in npc_cycles.values()
        for entries in cycle.values()
    )

    print(f"✅ Extracted {line_count} cycle lines across {cycle_count} cycles and {npc_count} NPCs")
    print(f"✅ Wrote: {OUTPUT_JSON_PATH}")
    print(f"📝 Debug log: {debug_log_path}")


if __name__ == "__main__":
    main()
