import re

def normalize_workbench(name):
    """Normalize raw workbench identifiers into human-readable names."""
    if not name:
        return "Unknown"
    # Strip whitespace, lowercase and remove any trailing _0 suffix
    key = name.strip().lower().replace(" ", "").rstrip("_0")
    aliases = {
        "advancedfurnituretable": "Advanced Furniture Table",
        "basicfurnituretable1": "Basic Furniture Table",
        "basicfurnituretable": "Basic Furniture Table",
        "cookingpot": "Cooking Pot",
        "craftingtable": "Crafting Table",
        "elvencraftingtable": "Elven Crafting Table",
        "farmer'stable": "Farmer's Table",
        "seltzerkeg": "Seltzer Keg",
        "keg": "Seltzer Keg",
        "ticketcounterfeiter": "Ticket Counterfeiter",
        "withergateanvil": "Withergate Anvil",
        "withergatefurnace": "Withergate Furnace",
    }
    return aliases.get(key, name)


def format_recipe(recipe):
    """Format a recipe dict into the target wiki template string."""
    output = recipe.get("output", {})
    output_name = output.get("name", "")
    output_amount = output.get("amount", "1")
    workbench_raw = recipe.get("workbench", "")
    workbench = normalize_workbench(workbench_raw)
    time = recipe.get("hoursToCraft", "0")
    recipe_id = recipe.get("recipeID", "")
    inputs = recipe.get("inputs", [])

    if not output_name or not inputs:
        return ""

    ingredients = "; ".join(
        f"{ing.get('name', 'Unknown')}*{ing.get('amount', '1')}" for ing in inputs
    )

    return (
        f"{{{{Recipe\n"
        f"|recipesource = \n"
        f"|workbench = {workbench}\n"
        f"|ingredients = {ingredients}\n"
        f"|time = {time}hr\n"
        f"|product = {output_name}\n"
        f"|yield = {output_amount}\n"
        f"|id = {recipe_id}  }}}}"
    )

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

def parse_time(s):
    s = s.strip().lower().replace(" ", "")
    if "h" in s or "m" in s:
        hours = 0
        minutes = 0
        h_match = re.search(r"(\\d+(\\.\\d+)?)h", s)
        m_match = re.search(r"(\\d+(\\.\\d+)?)m", s)
        if h_match:
            hours = float(h_match.group(1))
        if m_match:
            minutes = float(m_match.group(1))
        return hours + (minutes / 60)
    try:
        return float(s)
    except ValueError:
        return 0
