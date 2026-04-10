"""
Fish spawn chance exporter — Layer 3 of the pipeline.

Reads fish_spawner_data.json and items_data.json (via _load_cache) and writes
Fish_Spawn_Chance.txt with {{Fish locations}} wikitext.

Usage:
    python exporters/fish_spawn_chance.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from builders.item_builder import _load_cache
from utils import json_utils, file_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_FISH_DATA   = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "fish_spawner_data.json")
_OUTPUT_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Fish_Spawn_Chance.txt")

# ---------------------------------------------------------------------------
# Scene → location display name mapping
# ---------------------------------------------------------------------------

_SCENE_LOCATION_MAPPING = {
    "GCDockDistrict":            "Dock District",
    "GCMainDistrictEasternMarket": "Main Plaza",
}

# ---------------------------------------------------------------------------
# Probability helpers
# ---------------------------------------------------------------------------

def _lerp(a: float, b: float, t: float) -> float:
    return (1 - t) * a + t * b


def _adjusted_odds(rarity: str, level: int) -> float:
    t = level / 120.0
    if rarity == "Rare":
        return _lerp(0.8, 3.35, t)
    if rarity == "Epic":
        return _lerp(0.675, 4.25, t)
    if rarity == "Legendary":
        return _lerp(0.55, 5.0, t)
    return 1.0


def _compute_percentages(
    scene_data: dict,
    items_by_name: dict,
    level: int,
    familiar_waters_value: float = 0.0,
    advanced_fish_mapping_value: float = 0.0,
) -> dict[str, float]:
    drops = scene_data.get("fishDrops", [])

    num = 0.0
    num2 = 0.0
    if familiar_waters_value:
        num += 0.05 * familiar_waters_value
    if advanced_fish_mapping_value:
        num2 += 0.1 * advanced_fish_mapping_value

    rows: list[tuple[str, float]] = []

    for drop in drops:
        fish_name = (drop.get("name") or "").strip()
        chance = float(drop.get("dropChance") or 0)

        if not fish_name or chance <= 0:
            continue

        item = items_by_name.get(fish_name)
        if not item:
            continue

        rarity_value = int(getattr(item, "rarity", 0))
        rarity_str = constants.RARITY_TYPE_MAPPING.get(rarity_value, "Common")

        rarity_adjustment = 1.0
        if rarity_str == "Epic":
            rarity_adjustment += num
        elif rarity_str == "Legendary":
            rarity_adjustment += num + num2

        adjusted = _adjusted_odds(rarity_str, level)
        effective_weight = chance * rarity_adjustment * adjusted
        rows.append((fish_name, effective_weight))

    total = sum(w for _, w in rows)
    if total <= 0:
        return {}
    return {name: (w / total) * 100.0 for name, w in rows}

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_OUTPUT_FILE))

    fish_spawner_data = json_utils.load_json(_FISH_DATA)

    # Build name → ItemData map from item cache
    items = _load_cache()  # dict: display_name.lower() → ItemData
    items_by_name = {item.name: item for item in items.values()}

    fish_to_rows: dict[str, list[dict]] = {}

    for scene_name, location_name in _SCENE_LOCATION_MAPPING.items():
        scene_data = fish_spawner_data.get(scene_name)
        if not scene_data:
            continue

        min_percents = _compute_percentages(scene_data, items_by_name, level=1)
        max_percents = _compute_percentages(
            scene_data,
            items_by_name,
            level=70,
            familiar_waters_value=15,
            advanced_fish_mapping_value=30,
        )

        for fish_name in set(min_percents) | set(max_percents):
            fish_to_rows.setdefault(fish_name, []).append({
                "location": location_name,
                "season":   "Any",
                "min":      round(min_percents.get(fish_name, 0.0), 2),
                "max":      round(max_percents.get(fish_name, 0.0), 2),
            })

    output_lines: list[str] = []
    for fish_name in sorted(fish_to_rows.keys(), key=lambda x: x.lower()):
        output_lines.append("{{Fish locations\n")
        output_lines.append(f"|name = {fish_name}\n")
        rows = sorted(fish_to_rows[fish_name], key=lambda r: (r["location"], r["season"]))
        for idx, row in enumerate(rows, start=1):
            output_lines.append(f"|{idx}_location = {row['location']}\n")
            output_lines.append(f"   |{idx}_season = {row['season']}\n")
            output_lines.append(f"   |{idx}_min = {row['min']}\n")
            output_lines.append(f"   |{idx}_max = {row['max']}\n")
        output_lines.append("}}\n\n")

    file_utils.write_lines(_OUTPUT_FILE, output_lines)
    print(f"✅ Fish spawn chances written to {_OUTPUT_FILE}")


if __name__ == "__main__":
    run()
