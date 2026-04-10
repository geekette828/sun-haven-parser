"""
Workbench name aliases for Sun Haven.

Maps raw workbench identifiers (from asset filenames and JSON data) to their
human-readable canonical names. Update this dict when new workbenches are
added in a game patch.
"""

WORKBENCH_ALIASES: dict[str, str] = {
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


def normalize_workbench(name: str) -> str:
    """Normalize a raw workbench identifier into its human-readable name.

    Strips whitespace, lowercases, removes spaces, and strips any trailing
    ``_0`` suffix before looking up the canonical name. Returns the original
    value unchanged when no alias is found, or ``"Unknown"`` for empty input.
    """
    if not name:
        return "Unknown"
    key = name.strip().lower().replace(" ", "").rstrip("_0")
    return WORKBENCH_ALIASES.get(key, name)
