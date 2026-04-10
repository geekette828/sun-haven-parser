"""
Breakable object builder — Layer 1 of the pipeline.

Parses raw GameObject (.prefab) files for objects that have a lootTable,
and writes breakable_objects.json to the JSON Data output directory.

Usage:
    python builders/breakable_object_builder.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils, json_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_GAMEDATA_DIR = os.path.join(constants.INPUT_DIRECTORY, "GameObject")
_CACHE_FILE   = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "breakable_objects.json")
_DEBUG_LOG    = os.path.join(constants.DEBUG_DIRECTORY, "json", "breakable_objects_debug.txt")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_guid_from_meta(prefab_path: str) -> str:
    meta_path = prefab_path + ".meta"
    if not os.path.exists(meta_path):
        return "UNKNOWN"
    try:
        for line in file_utils.read_file_lines(meta_path):
            if "guid:" in line:
                return line.split("guid:")[1].strip()
    except Exception as exc:
        file_utils.write_debug_log(f"Error reading meta for {prefab_path}: {exc}", _DEBUG_LOG)
    return "UNKNOWN"


def _match_line_value(pattern: str, text: str, cast=None):
    """Find a single-line key: value match. Returns cast(value) or raw string."""
    m = re.search(pattern, text, flags=re.MULTILINE)
    if not m:
        return None
    val = m.group(1).strip().strip('"')
    if cast is None:
        return val
    try:
        return cast(val)
    except Exception:
        return None


def _extract_profession_exp_block(lines: list[str]) -> list[dict] | None:
    """Parse an optional professionEXP: block into a list of {profession, exp} dicts."""
    prof_list = []
    inside = False
    current: dict = {}

    for raw in lines:
        line = raw.rstrip("\n")

        if not inside:
            if re.match(r'^\s*professionEXP:\s*$', line):
                inside = True
            continue

        if re.match(r'^\S', line):
            break

        if re.match(r'^\s*-\s*profession\s*:\s*(\d+)', line):
            if current:
                prof_list.append(current)
            current = {}
            m = re.search(r'profession\s*:\s*(\d+)', line)
            current["profession"] = int(m.group(1)) if m else None
            continue

        m = re.search(r'\bexp\s*:\s*(\d+)', line)
        if m:
            current["exp"] = int(m.group(1))

    if current:
        prof_list.append(current)

    return prof_list if inside else None


def _extract_loot_table(lines: list[str]) -> list[list[dict]]:
    """
    Parse a lootTable: section with one or more - drops: blocks.
    Returns a list of drop-table lists, filtered to only tables with valid entries.
    """
    loot_tables = []
    inside_loot_table = False
    inside_drops_block = False
    current_table: list[dict] = []
    loot_indent = None

    for raw in lines:
        line = raw.rstrip("\n")

        if not inside_loot_table:
            if re.match(r'^\s*lootTable:\s*$', line):
                inside_loot_table = True
                loot_indent = len(line) - len(line.lstrip(' '))
            continue

        curr_indent = len(line) - len(line.lstrip(' '))
        if curr_indent <= (loot_indent or 0) and re.match(r'^\S', line):
            if current_table:
                loot_tables.append(current_table)
                current_table = []
            break

        if re.match(r'^\s*-\s*drops\s*:\s*$', line):
            if current_table:
                loot_tables.append(current_table)
                current_table = []
            inside_drops_block = True
            continue

        if not inside_drops_block:
            continue

        if re.match(r'^\s*-\s*drop\s*:\s*(.+)$', line):
            entry: dict = {"drop": None, "dropChance": None, "dropAmount": None}
            entry["drop"] = re.sub(r'^\s*-\s*drop\s*:\s*', '', line).strip()
            current_table.append(entry)
            continue

        m = re.search(r'\bdropChance\s*:\s*([0-9]+(?:\.[0-9]+)?)', line)
        if m and current_table:
            try:
                current_table[-1]["dropChance"] = float(m.group(1))
            except Exception:
                current_table[-1]["dropChance"] = None
            continue

        m = re.search(r'\bdropAmount\s*:\s*\{?\s*x\s*:\s*(\d+)\s*,\s*y\s*:\s*(\d+)\s*\}?', line)
        if m and current_table:
            current_table[-1]["dropAmount"] = {"x": int(m.group(1)), "y": int(m.group(2))}
            continue

    if current_table:
        loot_tables.append(current_table)

    return [
        tbl for tbl in loot_tables
        if any(e.get("dropChance") is not None and e.get("dropAmount") for e in tbl)
    ]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_CACHE_FILE))
    file_utils.ensure_dir_exists(os.path.dirname(_DEBUG_LOG))

    results: dict = {}

    try:
        files = [f for f in os.listdir(_GAMEDATA_DIR) if f.endswith(".prefab")]
    except FileNotFoundError:
        file_utils.write_debug_log(f"Directory not found: {_GAMEDATA_DIR}", _DEBUG_LOG)
        json_utils.write_json(results, _CACHE_FILE)
        print(f"❌ Directory not found: {_GAMEDATA_DIR}")
        return

    total = len(files)
    step = max(1, total // 5)

    for i, fname in enumerate(sorted(files), start=1):
        if i % step == 0:
            print(f"  🔄 {int((i / total) * 100)}% complete...")

        prefab_path = os.path.join(_GAMEDATA_DIR, fname)

        try:
            lines = file_utils.read_file_lines(prefab_path)
            content = "\n".join(lines)

            loot_tables = _extract_loot_table(lines)
            if not loot_tables:
                continue

            respawn_rate = _match_line_value(r'^\s*respawnRate\s*:\s*([^\n]+)$', content, cast=float)
            rarity       = _match_line_value(r'^\s*rarity\s*:\s*([^\n]+)$', content)
            prof_entries = _extract_profession_exp_block(lines)

            prefab_name = os.path.splitext(fname)[0]
            guid        = _read_guid_from_meta(prefab_path)

            results[prefab_name] = {
                "prefab":       prefab_name,
                "guid":         guid,
                "respawn_rate": respawn_rate,
                "rarity":       rarity,
                "profession_exp": prof_entries,
                "loot_table":   loot_tables,
            }

        except Exception as exc:
            file_utils.write_debug_log(f"Error processing {fname}: {exc}", _DEBUG_LOG)

    json_utils.write_json(results, _CACHE_FILE)
    print(f"✅ {len(results)} breakable objects written to {_CACHE_FILE}")


if __name__ == "__main__":
    run()
