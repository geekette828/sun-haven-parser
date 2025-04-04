import os
import config.constants as constants
from utils import json_utils, file_utils

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
    lines.append(f"### {output_name}\n")
    for recipe in recipes_by_output[output_name]:
        ingredients = "; ".join(
            [f"{item.get('name', 'Unknown')}*{item.get('amount', '1')}" for item in recipe.get("inputs", [])]
        )
        recipe_text = (
            f"{{{{Recipe\n"
            f"|recipesource = \n"
            f"|workbench    = \n"
            f"|ingredients  = {ingredients}\n"
            f"|time         = {recipe.get('hoursToCraft', '0')}hr\n"
            f"|product      = {recipe.get('output', {}).get('name', 'Unknown')}\n"
            f"|yield        = {recipe.get('output', {}).get('amount', '1')}}}}}\n\n"
        )
        lines.append(recipe_text)

# Write output to file using file_utils
file_utils.write_lines(output_file_path, lines)

print(f"Formatted recipes saved to {output_file_path}")
