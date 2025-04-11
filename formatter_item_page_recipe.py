import os
import config.constants as constants
from utils import json_utils
from utils.text_utils import clean_whitespace
from utils.recipe_utils import format_recipe

# Load recipe data once using constants
RECIPE_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
RECIPE_DATA = json_utils.load_json(RECIPE_JSON_PATH)

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

    formatted = [format_recipe(r) for r in recipes]
    formatted = [f for f in formatted if f.strip()]  # Remove blanks

    return "\n".join(formatted) if formatted else "{{Recipe/none}}"
