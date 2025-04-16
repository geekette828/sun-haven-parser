import re

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
    elif workbench == "SeltzerKeg":
        workbench = "Seltzer Keg"
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

def normalize_workbench(name):
    name = name.strip().lower().replace(" ", "")
    aliases = {
        "craftingtable": "crafting table",
        "basicfurnituretable1": "basic furniture table",
        "basicfurnituretable": "basic furniture table",
        "cookingpot": "cooking pot",
        "keg": "seltzer keg",
        "seltzerkeg": "seltzer keg",
        "ticketcounterfeiter": "ticket counterfeiter",
        "elvencraftingtable": "elven crafting table",
        "elvencraftingtable_0": "elven crafting table",
        "farmer'stable": "farmer's table",
        "advancedfurnituretable": "advanced furniture table",
    }

    # Remove trailing _0
    if name.endswith("_0"):
        name = name[:-2]

    return aliases.get(name, name)

def normalize_time(value):
    value = value.strip().lower().replace("hr", "").replace("h", "").replace("min", "").replace("m", "")
    try:
        if "." in value:
            return str(round(float(value) * 60))  # Convert 0.25 to 15
        return str(int(float(value)))  # Convert 15, 20, 30 etc.
    except ValueError:
        return value  # fallback to raw input
