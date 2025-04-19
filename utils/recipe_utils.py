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

    workbench = normalize_workbench_for_template(workbench)
    formatted_time = format_time(time)

    ingredients = "; ".join(
        f"{ing.get('name', 'Unknown')}*{ing.get('amount', '1')}" for ing in inputs
    )

    return (
        f"{{{{Recipe\n"
        f"|workbench    = {workbench}\n"
        f"|ingredients  = {ingredients}\n"
        f"|time         = {formatted_time}\n"
        f"|product      = {output_name}\n"
        f"|yield        = {output_amount}\n"
        f"|recipesource = \n"
        f"}}}}"
    )


def normalize_workbench(wb):
    if not wb:
        return ""
    wb = wb.lower().strip().replace(" ", "")
    wb = re.sub(r"(_0|1)$", "", wb)  # Remove trailing _0 or 1

    aliases = {  # JSON → wiki
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


def normalize_workbench_for_template(wb):
    """
    Keeps spacing/capitalization for template output
    """
    normalized = normalize_workbench(wb)
    return normalized.title() if normalized else "Unknown"


def format_time(hours):
    """
    Convert a fractional hour value to a wiki-friendly time string with h/m suffixes.
    Examples:
      0.25 → "15m"
      1.5  → "1h30m"
      2    → "2h"
    """
    try:
        h = float(hours)
    except Exception:
        return str(hours).strip()

    if h < 1:
        minutes = int(round(h * 60))
        return f"{minutes}m"
    hours_part = int(h)
    minutes_part = int(round((h - hours_part) * 60))
    if minutes_part:
        return f"{hours_part}h{minutes_part}m"
    return f"{hours_part}h"


def normalize_time_wiki(value):
    """
    Converts wiki-side time like '1h30m' or '5m' into total minutes for comparison.
    Returns a string of total minutes.
    """
    value = str(value).lower().strip()
    total = 0
    match = re.search(r"(\\d+)h", value)
    if match:
        total += int(match.group(1)) * 60
    match = re.search(r"(\\d+)m", value)
    if match:
        total += int(match.group(1))
    if total == 0:
        try:
            total = int(value)
        except ValueError:
            total = 0
    return str(total)
