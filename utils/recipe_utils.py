# Function builds a string that uses specific recipe formatting rules
def format_recipe(recipe):
    ingredients = "; ".join(
        f"{ing.get('name', 'Unknown')}*{ing.get('amount', '1')}"
        for ing in recipe.get("inputs", [])
    )
    recipe_text = (
        f"{{{{Recipe\n"
        f"|recipesource = \n"
        f"|workbench    = \n"
        f"|ingredients  = {ingredients}\n"
        f"|time         = {recipe.get('hoursToCraft', '0')}hr\n"
        f"|product      = {recipe.get('output', {}).get('name', 'Unknown')}\n"
        f"|yield        = {recipe.get('output', {}).get('amount', '1')}}}}}"
    )
    return recipe_text
