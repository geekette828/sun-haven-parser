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

def normalize_workbench(wb):
    if not wb:
        return ""
    wb = wb.lower().strip().replace(" ", "")
    wb = re.sub(r"(_0|1)$", "", wb)  # Remove trailing _0 or 1

    aliases = { #json: wiki
        "baker'sstation": "baker's station",
        "basicfurnituretable": "basic furniture table",
        "basicfurnituretable1": "basic furniture table",
        "constructiontable": "construction table",
        "cookingpot": "cooking pot",
        "elvencraftingtable": "elven crafting table",
        "elvenfurnace": "elven furnace",
        "farmerstable": "farmer's table",
        "manacomposter": "mana composter",
        "monsterfurnace": "monster furnace",
        "nurserycraftingtable": "nursery crafting table",
        "keg": "seltzerkeg",
        "ticketcounterfeiter": "ticket counterfeiter",
        "tilemaker": "tile maker",
        "withergateanvil": "withergate anvil",
    }

    return aliases.get(wb, wb)

