"""
All monster drops exporter — Layer 3 of the pipeline.

Reads entities_data.json and items_data.json (via _load_cache) and writes
"All Monster Drops.txt" with {{Drops}} wikitext for each enemy.

Usage:
    python exporters/all_monster_drops.py
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

_ENTITIES_DATA  = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "entities_data.json")
_OUTPUT_FILE    = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "All Monster Drops.txt")
_DEBUG_LOG      = os.path.join(constants.DEBUG_DIRECTORY, "all_monster_drops_debug.txt")

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_OUTPUT_FILE))
    file_utils.ensure_dir_exists(os.path.dirname(_DEBUG_LOG))

    entities = json_utils.load_json(_ENTITIES_DATA)

    # Build item_id → name from item builder cache
    items = _load_cache()
    item_id_map: dict[int, str] = {item.item_id: item.name for item in items.values()}

    output_lines: list[str] = []

    for key, data in entities.items():
        enemy_name = data.get("enemy_name")
        if enemy_name is None:
            continue

        lines = [
            f"### {enemy_name} ###",
            "{{Drops|sourceType = Monster",
            f" |droppedBy = {enemy_name}",
        ]
        drop_index = 1

        for i in range(1, 5):
            table_name = f"drop_table_{i}"
            drops = data.get(table_name, [])
            if not drops:
                continue

            total_weight = sum(entry.get("drop_chance", 0.0) for entry in drops)

            for entry in drops:
                item_id     = entry.get("id")
                drop_amount = entry.get("drop_amount", 0)
                drop_chance = entry.get("drop_chance", 0.0)

                if item_id == 0 or drop_amount == 0:
                    if item_id != 0:
                        file_utils.append_line(
                            _DEBUG_LOG,
                            f"Skipping 0-qty item: Monster='{enemy_name}' Table='{table_name}' ID={item_id}",
                        )
                    continue

                raw_chance = (drop_chance / total_weight) * 100 if total_weight else 0
                percent_chance = round(raw_chance, 2) if raw_chance < 1 else round(raw_chance, 1)

                item_name = item_id_map.get(item_id, f"Item {item_id}")
                lines.append(
                    f" |{drop_index}_item = {item_name:<20} "
                    f"|{drop_index}_quantity = {drop_amount:<10} "
                    f"|{drop_index}_chance = {percent_chance}"
                )
                drop_index += 1

        lines.append("}}\n")
        output_lines.append("\n".join(lines))

    file_utils.write_lines(_OUTPUT_FILE, [line + "\n\n" for line in output_lines])
    print(f"✅ Monster drops saved to {_OUTPUT_FILE}")


if __name__ == "__main__":
    run()
