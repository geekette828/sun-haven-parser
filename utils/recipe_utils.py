def format_recipe(recipe):
    output = recipe.get("output", {})
    output_name = output.get("name", "")
    output_amount = output.get("amount", "1")
    workbench = recipe.get("workbench", "Unknown")
    time = recipe.get("hoursToCraft", "0")
    inputs = recipe.get("inputs", [])

    if not output_name or not inputs:
        return ""

    # Normalize workbench name
    if workbench == "CraftingTable":
        workbench = "Crafting Table"
    elif workbench == "CookingPot":
        workbench = "Cooking Pot"
    elif workbench == "Basic Furniture Table 1":
        workbench = "Basic Furniture Table"
    elif "_0" in workbench:
        workbench = workbench.replace("_0", "")

    ingredients = "; ".join(
        f"{ing.get('name', 'Unknown')}*{ing.get('amount', '1')}" for ing in inputs
    )

    return (
        f"{{{{Recipe\n"
        f"|recipesource = \n"
        f"|workbench    = {workbench}\n"
        f"|ingredients  = {ingredients}\n"
        f"|time         = {time}hr\n"
        f"|product      = {output_name}\n"
        f"|yield        = {output_amount}}}}}"
    )
