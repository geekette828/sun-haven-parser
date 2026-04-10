"""
Item recipe exporter.

Accepts an ItemData object and returns the wikitext recipe markup for
the Crafting section of an item page.

Note: Recipe data is still loaded from the recipes JSON cache produced
by the recipe builder (not yet migrated). Once a RecipeData / recipe
builder exists this module will be updated to accept typed objects.

Replaces: formatter/page_section/item_recipe.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import config.constants as constants
from builders.item_data import ItemData
from mappings.workbench_aliases import normalize_workbench
from utils import json_utils
from utils.text_utils import clean_whitespace

_RECIPE_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")


# ---------------------------------------------------------------------------
# Wikitext formatter
# ---------------------------------------------------------------------------

def format_recipe(recipe: dict) -> str:
    """Format a recipe dict into the target {{Recipe}} wiki template string."""
    output = recipe.get("output", {})
    output_name = output.get("name", "")
    output_amount = output.get("amount", "1")
    workbench_raw = recipe.get("workbench", "")
    workbench = normalize_workbench(workbench_raw)
    time = recipe.get("hours_to_craft", "0")
    recipe_id = recipe.get("recipe_id", "")
    inputs = recipe.get("inputs", [])

    if not output_name or not inputs:
        return ""

    ingredients = "; ".join(
        f"{ing.get('name', 'Unknown')}*{ing.get('amount', '1')}" for ing in inputs
    )

    return (
        f"{{{{Recipe\n"
        f"|product = {output_name}\n"
        f"|yield = {output_amount}\n"
        f"|ingredients = {ingredients}\n"
        f"|workbench = {workbench}\n"
        f"|time = {time}hr\n"
        f"|id = {recipe_id}\n"
        f"|recipesource =   }}}}"
    )
_RECIPE_DATA: dict = json_utils.load_json(_RECIPE_JSON_PATH) or {}

_debug_log_path = os.path.join(
    constants.DEBUG_DIRECTORY, "pywikibot", "unknown_workbench_recipes.log"
)
os.makedirs(os.path.dirname(_debug_log_path), exist_ok=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    return clean_whitespace(name).lower()


def _get_recipes_by_output_name(name: str) -> list[dict]:
    """Return all valid recipe dicts whose output name matches the given name."""
    norm = _normalize_name(name)
    return [
        r for r in _RECIPE_DATA.values()
        if _normalize_name(r.get("output", {}).get("name", "")) == norm
        and r.get("output", {}).get("name")
        and r.get("inputs")
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_recipe(item: ItemData) -> str:
    """
    Generate recipe wikitext for the Crafting section of an item page.

    Returns ``{{Recipe/none}}`` when no valid recipes are found.
    """
    recipes = _get_recipes_by_output_name(item.name)

    valid_recipes = []
    unknown_recipes = []

    for r in recipes:
        raw_workbench = r.get("workbench", "")
        workbench = normalize_workbench(raw_workbench)

        if workbench == "Unknown":
            with open(_debug_log_path, "a", encoding="utf-8") as log:
                log.write(
                    f"{item.name} - RecipeID: {r.get('recipe_id', '?')} "
                    f"- RawWorkbench: {raw_workbench}\n"
                )
            unknown_recipes.append(r)
            continue

        valid_recipes.append(r)

    recipes_to_use = valid_recipes if valid_recipes else unknown_recipes
    formatted = [f for f in (format_recipe(r) for r in recipes_to_use) if f.strip()]

    return "\n".join(formatted) if formatted else "{{Recipe/none}}"
