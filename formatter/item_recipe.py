import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import json_utils
from utils.text_utils import clean_whitespace
from mappings.recipe_mapping import format_recipe, normalize_workbench

RECIPE_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
RECIPE_DATA = json_utils.load_json(RECIPE_JSON_PATH)

debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "unknown_workbench_recipes.log")
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)

def normalize_name(name):
    """Normalize name for comparison (lowercase + trimmed whitespace)."""
    return clean_whitespace(name).lower()

def get_recipes_by_output_name(name):
    """Return all valid recipes where output.name matches the given name."""
    norm = normalize_name(name)
    return [
        r for r in RECIPE_DATA.values()
        if normalize_name(r.get("output", {}).get("name", "")) == norm
        and r.get("output", {}).get("name")
        and r.get("inputs")
    ]

def get_recipe_markup_for_item(item):
    """Generate recipe wiki markup from item data or return {{Recipe/none}}."""
    name = item.get("name") or item.get("Name", "")
    recipes = get_recipes_by_output_name(name)

    included = []
    for r in recipes:
        workbench = normalize_workbench(r.get("workbench", ""))
        if workbench == "Unknown":
            # Log the unknown workbench case
            with open(debug_log_path, "a", encoding="utf-8") as logf:
                logf.write(f"{name} - RecipeID: {r.get('recipeID', '?')} - RawWorkbench: {r.get('workbench', '')}\n")
            continue
        included.append(r)

    formatted = [format_recipe(r) for r in included]
    formatted = [f for f in formatted if f.strip()]  # Remove blanks

    return "\n".join(formatted) if formatted else "{{Recipe/none}}"
