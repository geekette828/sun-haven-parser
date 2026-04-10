"""
Recipe builder — Layer 1 of the pipeline.

Parses raw MonoBehaviour Recipe*.asset files and RecipeList*.asset files
to produce recipes_data.json.

Depends on the item builder cache (items_data.json) for ID → display name
lookups. Run item_builder.py first if the cache doesn't exist.

Usage:
    python builders/recipe_builder.py
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from builders.item_builder import _CACHE_FILE as _ITEM_CACHE_FILE, _load_cache
from mappings.workbench_aliases import normalize_workbench
from utils import file_utils, json_utils, text_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_MONOBEHAVIOUR_DIR = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
_CACHE_FILE        = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
_DEBUG_LOG         = os.path.join(constants.DEBUG_DIRECTORY, "json", "recipe_builder_debug.txt")

# ---------------------------------------------------------------------------
# ID → name lookup (built from item builder cache)
# ---------------------------------------------------------------------------

def _build_id_to_names() -> defaultdict[str, list[str]]:
    """Load ItemData cache and return a dict mapping item_id → [canonical names]."""
    if not os.path.exists(_ITEM_CACHE_FILE):
        raise FileNotFoundError(
            f"❌ Missing item cache. Run the item builder first:\n"
            f"   python builders/item_builder.py"
        )
    items = _load_cache()
    id_to_names: defaultdict[str, list[str]] = defaultdict(list)
    for item in items.values():
        id_to_names[str(item.item_id)].append(item.name)
    return id_to_names


def _get_canonical_name(item_id, fallback_name: str, recipe_name: str, id_to_names: defaultdict) -> str:
    id_str = str(item_id).strip()
    names  = id_to_names.get(id_str)

    if not names:
        file_utils.append_line(_DEBUG_LOG, f"[MISSING] ID {item_id} not found for '{fallback_name}' in {recipe_name}")
        return fallback_name

    norm_names = set(text_utils.normalize_for_compare(n) for n in names)
    if len(norm_names) > 1:
        file_utils.append_line(_DEBUG_LOG, f"[CONFLICT] ID {item_id} has conflicting names {names} in {recipe_name}")
        return fallback_name

    return names[0]

# ---------------------------------------------------------------------------
# Asset parsers
# ---------------------------------------------------------------------------

def _extract_guid(meta_path: str) -> str | None:
    try:
        for line in file_utils.read_file_lines(meta_path):
            match = re.search(r"guid:\s*([a-f0-9]+)", line)
            if match:
                return match.group(1)
    except Exception as exc:
        print(f"  ⚠️  Error reading {meta_path}: {exc}")
    return None


def _parse_recipe_asset(file_path: str, id_to_names: defaultdict) -> dict:
    recipe_data: dict = {
        "inputs":                  [],
        "output":                  {},
        "hours_to_craft":          None,
        "character_progress_tokens": None,
        "world_progress_tokens":   None,
        "quest_progress_tokens":   None,
    }

    lines = file_utils.read_file_lines(file_path)
    input_section  = False
    output_section = False

    for i, line in enumerate(lines):
        line = line.strip()

        if line.startswith("input2:"):
            input_section  = True
            output_section = False
            continue
        elif line.startswith("output2:"):
            input_section  = False
            output_section = True
            continue

        if "hoursToCraft:" in line:
            recipe_data["hours_to_craft"] = line.split(":")[-1].strip()
        elif "characterProgressTokens:" in line:
            match = re.search(r'guid: ([\w-]+)', line)
            if match:
                recipe_data["character_progress_tokens"] = match.group(1)
        elif "worldProgressTokens:" in line:
            match = re.search(r'guid: ([\w-]+)', line)
            if match:
                recipe_data["world_progress_tokens"] = match.group(1)
        elif "questProgressTokens:" in line:
            match = re.search(r'guid: ([\w-]+)', line)
            if match:
                recipe_data["quest_progress_tokens"] = match.group(1)

        elif input_section:
            if i + 1 < len(lines) and "id:" in line and "amount:" in lines[i + 1]:
                item_id = line.split(":")[-1].strip()
                amount  = lines[i + 1].split(":")[-1].strip()
                name    = (
                    lines[i + 2].split(":")[-1].strip()
                    if (i + 2 < len(lines) and "name:" in lines[i + 2])
                    else "Unknown"
                )
                recipe_data["inputs"].append({
                    "id":     item_id,
                    "amount": amount,
                    "name":   _get_canonical_name(item_id, name, file_path, id_to_names),
                })
            if "---" in line:
                input_section = False

        elif output_section:
            if i + 1 < len(lines) and "id:" in line and "amount:" in lines[i + 1]:
                item_id = line.split(":")[-1].strip()
                amount  = lines[i + 1].split(":")[-1].strip()
                name    = (
                    lines[i + 2].split(":")[-1].strip()
                    if (i + 2 < len(lines) and "name:" in lines[i + 2])
                    else "Unknown"
                )
                recipe_data["output"] = {
                    "id":     item_id,
                    "amount": amount,
                    "name":   _get_canonical_name(item_id, name, file_path, id_to_names),
                }
            if "---" in line:
                output_section = False

    return recipe_data

# ---------------------------------------------------------------------------
# ID / disambiguation helpers
# ---------------------------------------------------------------------------

def _normalize_workbench_camel(wb: str) -> str:
    wb    = re.sub(r"[^a-zA-Z0-9 ]", "", wb)
    parts = wb.strip().split()
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:]) if parts else "unknownWorkbench"


def _camel_case(text: str) -> str:
    parts = re.sub(r"[^a-zA-Z0-9 ]", "", text).strip().split()
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:]) if parts else "unknown"


def _extract_disambiguation(filename: str) -> str | None:
    match = re.search(r"\(([^)]+)\)\.asset$", filename)
    return _camel_case(match.group(1)) if match else None


def _generate_recipe_id(parsed_id: int, workbench_name: str, output_id) -> str:
    return f"{parsed_id}_{_normalize_workbench_camel(workbench_name)}_{output_id}"

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_CACHE_FILE))
    file_utils.ensure_dir_exists(os.path.dirname(_DEBUG_LOG))

    print("Loading item data for ID → name lookup...")
    id_to_names = _build_id_to_names()

    # Parse all Recipe*.asset files
    print("Parsing recipe assets...")
    raw_recipes: dict = {}
    for filename in os.listdir(_MONOBEHAVIOUR_DIR):
        if filename.lower().startswith("recipe") and filename.endswith(".asset"):
            asset_path = os.path.join(_MONOBEHAVIOUR_DIR, filename)
            meta_path  = asset_path + ".meta"

            recipe_info = _parse_recipe_asset(asset_path, id_to_names)
            if os.path.exists(meta_path):
                recipe_info["guid"] = _extract_guid(meta_path)

            id_match = re.search(r"[Rr]ecipe\s+(\d+)", filename)
            recipe_info["parsed_recipe_id"] = int(id_match.group(1)) if id_match else 0
            raw_recipes[filename] = recipe_info

    # Map recipe GUIDs → workbenches via RecipeList*.asset files
    guid_to_workbenches: defaultdict[str, set] = defaultdict(set)
    for filename in os.listdir(_MONOBEHAVIOUR_DIR):
        m = re.match(r"^RecipeList[_ ]+(.+)\.asset$", filename)
        if not m:
            continue
        workbench = normalize_workbench(m.group(1))
        path      = os.path.join(_MONOBEHAVIOUR_DIR, filename)
        for line in file_utils.read_file_lines(path):
            match = re.search(r'guid: ([\w-]+)', line)
            if match:
                guid_to_workbenches[match.group(1)].add(workbench)

    # Assign recipes to workbenches and generate stable IDs
    final_recipes: dict = {}
    recipe_id_tracker: defaultdict[str, list] = defaultdict(list)

    for name, data in raw_recipes.items():
        guid       = data.get("guid")
        workbenches = guid_to_workbenches.get(guid, set())

        if not workbenches:
            output_name = data.get("output", {}).get("name", "")
            if " Jam" in output_name:
                file_utils.append_line(_DEBUG_LOG, f"[INFERRED] {name} → Jam Maker")
                workbenches.add("Jam Maker")
            else:
                workbenches.add("Unknown Workbench")

        for wb in workbenches:
            data_copy   = dict(data)
            data_copy["workbench"] = wb
            output_id   = data.get("output", {}).get("id", "unknown")
            base_id     = _generate_recipe_id(data["parsed_recipe_id"], wb, output_id)

            inputs_sig       = tuple((i["id"], i["amount"]) for i in data.get("inputs", []))
            existing_sigs    = recipe_id_tracker[base_id]

            if inputs_sig in existing_sigs:
                recipe_id = base_id
            else:
                if existing_sigs:
                    dis = _extract_disambiguation(name)
                    recipe_id = f"{base_id}_{dis}" if dis else f"{base_id}_{len(existing_sigs) + 1}"
                else:
                    recipe_id = base_id
                recipe_id_tracker[base_id].append(inputs_sig)

            data_copy["recipe_id"]   = recipe_id
            data_copy["source_file"] = name
            final_recipes[recipe_id] = data_copy

    json_utils.write_json(final_recipes, _CACHE_FILE, indent=4)
    print(f"✅ {len(final_recipes)} recipes written to {_CACHE_FILE}")


if __name__ == "__main__":
    run()
