
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import json_utils, file_utils
from utils.recipe_utils import format_recipe

# Define file paths
input_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Recipes.txt")

# Ensure output directory exists
output_directory = os.path.dirname(output_file_path)
file_utils.ensure_dir_exists(output_directory)

# Load the extracted recipe data using json_utils
recipes_data = json_utils.load_json(input_file_path)

# Organize recipes by output name
recipes_by_output = {}
for recipe in recipes_data.values():
    output_name = recipe.get("output", {}).get("name")
    if output_name:
        recipes_by_output.setdefault(output_name, []).append(recipe)

# Sort output items alphabetically
sorted_outputs = sorted(recipes_by_output.keys())

# Prepare the formatted recipe lines
lines = []
for output_name in sorted_outputs:
    recipes = recipes_by_output[output_name]
    formatted = [format_recipe(r) for r in recipes]
    formatted = [f for f in formatted if f.strip()]  # skip blanks

    if not formatted:
        continue  # skip header if nothing to write

    lines.append(f"### {output_name}\n")
    lines.extend(r + "\n\n" for r in formatted)

# Write output to file using file_utils
file_utils.write_lines(output_file_path, lines)

print(f"Formatted recipes saved to {output_file_path}")
