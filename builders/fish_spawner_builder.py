"""
Fish spawner builder — Layer 1 of the pipeline.

Parses raw Scenes (.unity) files to extract fish spawner data per scene,
writing fish_spawner_data.json.

Usage:
    python builders/fish_spawner_builder.py
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

_SCENES_DIR = os.path.join(constants.INPUT_DIRECTORY, "Scenes")
_CACHE_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "fish_spawner_data.json")
_DEBUG_LOG  = os.path.join(constants.DEBUG_DIRECTORY, "json", "fish_spawner_debug.txt")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_fish_block(block: str) -> tuple[list[dict], dict]:
    """
    Parse a _fish: block and return (named_fish_drops, seasonal_fish).

    named_fish_drops: [{"name": str, "drop_chance": int}, ...]
    seasonal_fish:    {"fish_spring": [...], "fish_summer": [...], ...}
    """
    named_fish = re.findall(r"- drop: (.+?)\n\s+dropChance: (\d+)", block)
    named_fish_drops = [
        {"name": name.strip(), "drop_chance": int(chance)}
        for name, chance in named_fish
    ]

    seasonal: dict = {}
    for season_key, snake_key in [
        ("fishSpring", "fish_spring"),
        ("fishSummer", "fish_summer"),
        ("fishFall",   "fish_fall"),
        ("fishWinter", "fish_winter"),
    ]:
        seasonal[snake_key] = [
            {"guid": guid, "drop_chance": int(chance)}
            for guid, chance in re.findall(
                rf"{season_key}:\s+?drops:\s+?- fish: {{fileID: \d+, guid: ([a-f0-9]+),.*?dropChance: (\d+)",
                block,
            )
        ]

    return named_fish_drops, seasonal


def _process_unity_file(filepath: str) -> dict | None:
    try:
        content = "\n".join(file_utils.read_file_lines(filepath))
        match = re.search(r"_fish:(.*?)--- !u!", content, re.DOTALL)
        if not match:
            return None

        named_fish, seasonal = _parse_fish_block(match.group(1))
        scene_name = os.path.splitext(os.path.basename(filepath))[0]
        return {
            "scene_name":    scene_name,
            "fish_drops":    named_fish,
            "seasonal_fish": seasonal,
        }
    except Exception as exc:
        file_utils.write_debug_log(f"Error processing {filepath}: {exc}", _DEBUG_LOG)
        return None


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_CACHE_FILE))
    file_utils.ensure_dir_exists(os.path.dirname(_DEBUG_LOG))

    results: dict = {}
    unity_files = [f for f in os.listdir(_SCENES_DIR) if f.endswith(".unity")]

    for filename in unity_files:
        filepath = os.path.join(_SCENES_DIR, filename)
        result = _process_unity_file(filepath)
        if result:
            results[result["scene_name"]] = result

    json_utils.write_json(results, _CACHE_FILE, indent=2)
    print(f"✅ {len(results)} scenes written to {_CACHE_FILE}")


if __name__ == "__main__":
    run()
