# scripts/prefab_loot_filter.py

import os
import sys
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils, json_utils

# Define paths
object_directory = os.path.join(constants.INPUT_DIRECTORY, "GameObject")  # match your convention
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "breakable_objects.json")
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "breakable_objects_debug.txt")
file_utils.ensure_dir_exists(os.path.dirname(output_file))
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)

# Helpers
def _read_guid_from_meta(prefab_path: str) -> str:
    meta_path = prefab_path + ".meta"
    if not os.path.exists(meta_path):
        return "UNKNOWN"
    try:
        for line in file_utils.read_file_lines(meta_path):
            if "guid:" in line:
                return line.split("guid:")[1].strip()
    except Exception as e:
        file_utils.write_debug_log(f"Error reading meta for {prefab_path}: {e}", debug_log_path)
    return "UNKNOWN"


def _match_line_value(pattern: str, text: str, cast=None):
    """
    Find a single-line `key: value` match using regex pattern with one capturing group.
    If cast is provided, apply it; on failure return None.
    """
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


def _extract_profession_exp_block(lines):
    """
    Parse an optional `professionEXP:` block into a list of dicts:
    [{"profession": 4, "exp": 5}, ...]
    Return None if the block is absent.
    """
    prof_list = []
    inside = False
    current = {}

    for raw in lines:
        line = raw.rstrip("\n")

        # Enter the block
        if not inside:
            if re.match(r'^\s*professionEXP:\s*$', line):
                inside = True
            continue

        # If we hit a new top-level key, stop
        if re.match(r'^\S', line):
            break

        # New list item: "- profession: <num>"
        if re.match(r'^\s*-\s*profession\s*:\s*(\d+)', line):
            if current:
                prof_list.append(current)
            current = {}
            m = re.search(r'profession\s*:\s*(\d+)', line)
            current["profession"] = int(m.group(1)) if m else None
            continue

        # "exp: <num>"
        m = re.search(r'\bexp\s*:\s*(\d+)', line)
        if m:
            current["exp"] = int(m.group(1))

    if current:
        prof_list.append(current)

    return prof_list if inside else None


def _extract_loot_table(lines):
    """
    Parse a `lootTable:` section with one or more `- drops:` blocks.
    Returns a list of drop-table lists, each containing entries with:
    {"drop": <raw>, "dropChance": <float|None>, "dropAmount": {"x": int, "y": int}|None}
    Only returns non-empty tables that have at least one entry with dropChance and dropAmount.
    """
    loot_tables = []
    inside_loot_table = False
    inside_drops_block = False
    current_table = []
    loot_indent = None

    for raw in lines:
        line = raw.rstrip("\n")

        if not inside_loot_table:
            if re.match(r'^\s*lootTable:\s*$', line):
                inside_loot_table = True
                loot_indent = len(line) - len(line.lstrip(' '))
            continue

        # If indentation suggests a new top-level key, end lootTable
        curr_indent = len(line) - len(line.lstrip(' '))
        if curr_indent <= (loot_indent or 0) and re.match(r'^\S', line):
            if current_table:
                loot_tables.append(current_table)
                current_table = []
            break

        # Start of a new drops block
        if re.match(r'^\s*-\s*drops\s*:\s*$', line):
            if current_table:
                loot_tables.append(current_table)
                current_table = []
            inside_drops_block = True
            continue

        if not inside_drops_block:
            continue

        # New drop entry
        if re.match(r'^\s*-\s*drop\s*:\s*(.+)$', line):
            entry = {"drop": None, "dropChance": None, "dropAmount": None}
            entry["drop"] = re.sub(r'^\s*-\s*drop\s*:\s*', '', line).strip()
            current_table.append(entry)
            continue

        # dropChance
        m = re.search(r'\bdropChance\s*:\s*([0-9]+(?:\.[0-9]+)?)', line)
        if m and current_table:
            try:
                current_table[-1]["dropChance"] = float(m.group(1))
            except Exception:
                current_table[-1]["dropChance"] = None
            continue

        # dropAmount
        m = re.search(r'\bdropAmount\s*:\s*\{?\s*x\s*:\s*(\d+)\s*,\s*y\s*:\s*(\d+)\s*\}?', line)
        if m and current_table:
            current_table[-1]["dropAmount"] = {"x": int(m.group(1)), "y": int(m.group(2))}
            continue

    if current_table:
        loot_tables.append(current_table)

    # Keep only tables with at least one valid entry
    return [tbl for tbl in loot_tables if any(e.get("dropChance") is not None and e.get("dropAmount") for e in tbl)]


#  Main
def main():
    results = {}
    try:
        files = [f for f in os.listdir(object_directory) if f.endswith(".prefab")]
    except FileNotFoundError:
        file_utils.write_debug_log(f"Directory not found: {object_directory}", debug_log_path)
        json_utils.write_json(results, output_file)
        print(f"0 files processed. Wrote empty JSON to {output_file}")
        return

    total = len(files)
    for i, fname in enumerate(sorted(files), start=1):
        if total and i % max(1, total // 5) == 0:
            print(f"{i}/{total} ({int((i/total)*100)}%)")

        prefab_path = os.path.join(object_directory, fname)

        try:
            lines = file_utils.read_file_lines(prefab_path)
            content = "\n".join(lines)

            # REQUIRED: lootTable with at least one '- drops:' block
            loot_tables = _extract_loot_table(lines)
            if not loot_tables:
                continue

            # OPTIONAL: respawnRate and rarity (include if present, else None)
            respawn_rate = _match_line_value(r'^\s*respawnRate\s*:\s*([^\n]+)$', content, cast=float)
            rarity = _match_line_value(r'^\s*rarity\s*:\s*([^\n]+)$', content)

            # OPTIONAL: professionEXP (include if present, else None)
            prof_entries = _extract_profession_exp_block(lines)  # may be None

            prefab_name = os.path.splitext(fname)[0]
            guid = _read_guid_from_meta(prefab_path)

            results[prefab_name] = {
                "prefab": prefab_name,
                "guid": guid,
                "respawnRate": respawn_rate if respawn_rate is not None else None,
                "rarity": rarity if rarity is not None else None,
                "professionEXP": prof_entries if prof_entries is not None else None,
                "lootTable": loot_tables
            }

        except Exception as e:
            file_utils.write_debug_log(f"Error processing {fname}: {e}", debug_log_path)

    json_utils.write_json(results, output_file)
    print(f"Saved {len(results)} objects to {output_file}")


if __name__ == "__main__":
    main()