import os
import json
import config.constants as constants

# Define file paths
input_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Recipes.txt")

# Load the extracted recipe data
with open(input_file_path, "r", encoding="utf-8") as file:
    recipes_data = json.load(file)

# Organize recipes by output name
recipes_by_output = {}
for recipe in recipes_data.values():
    output_name = recipe.get("output", {}).get("name")
    if output_name:
        if output_name not in recipes_by_output:
            recipes_by_output[output_name] = []
        recipes_by_output[output_name].append(recipe)

# Sort output items alphabetically
sorted_outputs = sorted(recipes_by_output.keys())

# Format recipes into the specified format
with open(output_file_path, "w", encoding="utf-8") as output_file:
    for output_name in sorted_outputs:
        output_file.write(f"### {output_name}\n")
        for recipe in recipes_by_output[output_name]:
            ingredients = "; ".join(
                [f"{item.get('name', 'Unknown')}*{item.get('amount', '1')}" for item in recipe.get("inputs", [])]
            )
            output_file.write(
                f"{{{{Recipe\n"
                f"|recipesource = \n"
                f"|workbench    = \n"
                f"|ingredients  = {ingredients}\n"
                f"|time         = {recipe.get('hoursToCraft', '0')}hr\n"
                f"|product      = {recipe.get('output', {}).get('name', 'Unknown')}\n"
                f"|yield        = {recipe.get('output', {}).get('amount', '1')}}}}}\n\n"
            )

print(f"Formatted recipes saved to {output_file_path}")
