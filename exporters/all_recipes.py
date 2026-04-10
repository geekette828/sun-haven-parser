"""
All recipes exporter — Layer 3 of the pipeline.

Reads recipes_data.json and writes Recipes.txt with wikitext for every recipe,
grouped alphabetically by output item name.

Usage:
    python exporters/all_recipes.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import json_utils, file_utils
from formatters.item.item_recipe import format_recipe

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_INPUT_FILE  = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
_OUTPUT_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Recipes.txt")

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_OUTPUT_FILE))

    recipes_data = json_utils.load_json(_INPUT_FILE)

    # Group recipes by output item name
    recipes_by_output: dict[str, list] = {}
    for recipe in recipes_data.values():
        output_name = recipe.get("output", {}).get("name")
        if output_name:
            recipes_by_output.setdefault(output_name, []).append(recipe)

    lines: list[str] = []
    for output_name in sorted(recipes_by_output.keys()):
        formatted = [format_recipe(r) for r in recipes_by_output[output_name]]
        formatted = [f for f in formatted if f.strip()]
        if not formatted:
            continue
        lines.append(f"### {output_name}\n")
        lines.extend(r + "\n\n" for r in formatted)

    file_utils.write_lines(_OUTPUT_FILE, lines)
    print(f"✅ Formatted recipes saved to {_OUTPUT_FILE}")


if __name__ == "__main__":
    run()
