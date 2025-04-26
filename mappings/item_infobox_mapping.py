"""
Field mapping and formatter for the Item Infobox from items_data.json.
Exports:
  FIELD_MAP
  format_infobox(item, classification, title)
"""

from typing import Dict, Tuple, Callable, Any
from mappings.item_classification import classify_item
from utils.text_utils import clean_whitespace, normalize_apostrophe
import config.constants as constants

# ---------------------------
# Normalization Helpers (shared)
# ---------------------------
def _text(v: Any) -> str:
    return clean_whitespace(normalize_apostrophe(str(v or "")))

def _int_str(v: Any) -> str:
    return str(int(v)) if v not in (None, "", "null") else ""

def _float_str(v: Any) -> str:
    try:
        return str(round(float(v), 2))
    except:
        return ""

# ---------------------------
# Top-Level Field Mapping (Raw JSON → Normalized)
# ---------------------------
FIELD_MAP: Dict[str, Tuple[str, Callable[[Any], str]]] = {
    "name": ("Name", _text),
    "sell": ("sellPrice", _int_str),
    "stack": ("stackSize", _int_str),
    "rarity": ("rarity", _int_str),
    "hearts": ("hearts", _int_str),
    "dlc": ("isDLCItem", lambda v: "True" if str(v) in ["1", "True"] else "False"),
    "requiredLevel": ("requiredLevel", _int_str),
    "stats": ("stats", lambda v: v if v else []),
    "foodStat": ("foodStat", lambda v: v if v else []),
    "statBuff": ("statBuff", lambda v: v if v else []),
    "health": ("health", _int_str),
    "mana": ("mana", _int_str),
    "setSeason": ("setSeason", _int_str),
    "experience": ("experience", _int_str),
    "isFruit": ("isFruit", lambda v: "True" if str(v) in ["1", "True"] else "False"),
}

# ---------------------------
# Computed Field Helpers
# ---------------------------

def get_sell_info(item: dict) -> Tuple[str, str]:
    """
    Determines correct sell value and currency.
    """
    if item.get("sellPrice", 0):
        return str(item["sellPrice"]), "Coins"
    if item.get("orbsSellPrice", 0):
        return str(item["orbsSellPrice"]), "Orbs"
    if item.get("ticketSellPrice", 0):
        return str(item["ticketSellPrice"]), "Tickets"
    return "", ""

def compute_sell(item: dict) -> str:
    if item.get("sellPrice", 0):
        return str(item.get("sellPrice"))
    elif item.get("orbsSellPrice", 0):
        return str(item.get("orbsSellPrice"))
    elif item.get("ticketSellPrice", 0):
        return str(item.get("ticketSellPrice"))
    else:
        return ""

def compute_restores(item):
    health = item.get("health", 0)
    mana = item.get("mana", 0)
    parts = []
    if isinstance(health, (int, float)) and health > 0:
        parts.append(f"Health»+{health}")
    if isinstance(mana, (int, float)) and mana > 0:
        parts.append(f"Mana»+{mana}")
    return "; ".join(parts)

def compute_statInc(item):
    parts = []
    for stat in item.get("foodStat", []):
        if stat.get("increase") == "999":
            continue
        stat_id = int(stat.get("stat", -1))
        stat_name = constants.STAT_TYPE_MAPPING.get(stat_id, f"Stat{stat_id}")
        increase = int(stat.get("increase", 0))
        inc_text = constants.FOOD_STAT_INCREASES.get(increase, f"+{increase}")
        parts.append(f"{stat_name}»({inc_text})")

    for buff in item.get("statBuff", []):
        stat_type = int(buff.get("statType", -1))
        value = float(buff.get("value") or 0)
        duration = int(buff.get("duration") or 0)
        stat_name = constants.STAT_TYPE_MAPPING.get(stat_type, f"Stat{stat_type}")
        value_text = f"{int(value * 100)}%" if value <= 1 else str(int(value))
        minutes = duration // 60
        parts.append(f"{stat_name}«{value_text}»({minutes}m)")

    return "; ".join(parts)

def compute_organic(item):
    raw = item.get("isFruit", "")
    try:
        return "True" if int(raw) == 1 else "False"
    except:
        return ""

def compute_season(item):
    has_set = item.get("hasSetSeason")
    try:
        if int(has_set) == 1:
            return constants.SEASONS.get(int(item.get("setSeason", -1)), "")
        elif int(has_set) == 0:
            return "Any"
    except:
        return ""
    return ""

def compute_exp(item):
    return str(item.get("experience", "") or "")

def compute_effect(item):
    effects = []
    for stat in item.get("stats", []):
        try:
            stat_type = int(stat.get("statType", 999))
            value = stat.get("value", 0)
            stat_name = constants.STAT_TYPE_MAPPING.get(stat_type, "none")
            effects.append(f"{stat_name}»{value}")
        except:
            continue
    return "; ".join(effects)

def compute_requirement(item, classification):
    required_level = item.get("requiredLevel")
    if not required_level:
        return ""
    itemType, subtype, category = classification
    skill = ""
    if subtype in ["Armor", "Accessory"]:
        skill = "Combat"
    elif category in ["Hoe", "Watering Can"]:
        skill = "Farming"
    elif category == "Pickaxe":
        skill = "Mining"
    elif category == "Axe":
        skill = "Exploration"
    elif category in ["Rod", "Net"]:
        skill = "Fishing"
    if skill:
        return f"{{{{SkillLevel|{skill}|{required_level}}}}}"
    return ""

# ---------------------------
# Computed-only fields (not tied to a single JSON key)
# ---------------------------
FIELD_COMPUTATIONS: Dict[str, Callable[[dict], str]] = {
    "sell": compute_sell,
    "selltype": lambda item: (
        "coins" if item.get("sellPrice", 0) else
        "orbs" if item.get("orbsSellPrice", 0) else
        "tickets" if item.get("ticketSellPrice", 0) else ""
    ),
    "restores": compute_restores,
    "statInc": compute_statInc,
    "season": compute_season,
    "exp": compute_exp,
    "organic": compute_organic,
    "requirement": lambda item: compute_requirement(item, classify_item(item))
}

def format_infobox(item: dict, classification: Tuple[str, str, str], title: str) -> str:
    """
    Generates the complete Item infobox wikitext based on FIELD_MAP and FIELD_COMPUTATIONS.
    """
    itemType, subtype, category = classification

    if itemType == "Furniture" or subtype in ["Pet", "Wild Animal"]:
        return ""  # skip pages we don't format

    lines = ["{{Item infobox"]

    # Core Fields
    name = FIELD_MAP["name"][1](item.get(FIELD_MAP["name"][0], title))
    lines.append(f"|name = {name}")

    sell = FIELD_MAP["sell"][1](item.get(FIELD_MAP["sell"][0]))
    if sell:
        lines.append(f"|sell = {sell}")

    selltype = FIELD_COMPUTATIONS["selltype"](item)
    if selltype:
        lines.append(f"|selltype = {selltype}")

    for key in ["stack", "rarity", "hearts"]:
        json_key, normalize = FIELD_MAP[key]
        value = normalize(item.get(json_key))
        if value:
            lines.append(f"|{key} = {value}")

    # Classification
    lines.append("<!-- Item Classification -->")
    lines.append(f"|itemType = {itemType}")
    lines.append(f"|subtype = {subtype}")
    lines.append(f"|category = {category}")

    dlc = FIELD_MAP["dlc"][1](item.get(FIELD_MAP["dlc"][0], 0))
    lines.append(f"|dlc = {dlc}")

    # Data section
    lines.append("<!-- Item Data-->")

    if subtype == "Barn Animal":
        lines.append("|region = ")
        lines.append("|produces = ")
        lines.append("|capacity = ")
    elif subtype == "Food":
        lines.append(f"|restores = {FIELD_COMPUTATIONS['restores'](item)}")
        lines.append(f"|statInc = {FIELD_COMPUTATIONS['statInc'](item)}")
        lines.append(f"|organic = {FIELD_COMPUTATIONS['organic'](item)}")
    elif itemType == "Fish":
        lines.append(f"|restores = {FIELD_COMPUTATIONS['restores'](item)}")
        lines.append(f"|statInc = {FIELD_COMPUTATIONS['statInc'](item)}")
        lines.append("|region = ")
        lines.append(f"|season = {FIELD_COMPUTATIONS['season'](item)}")
        lines.append(f"|exp = {FIELD_COMPUTATIONS['exp'](item)}")
    elif subtype == "Clothing":
        lines.append("|armorset = ")
    elif subtype in ["Armor", "Accessory"]:
        lines.append("|armorset = ")
        lines.append(f"|effect = {compute_effect(item)}")
        lines.append(f"|requirement = {FIELD_COMPUTATIONS['requirement'](item)}")
    elif subtype in ["Tool", "Weapon"]:
        lines.append(f"|requirement = {FIELD_COMPUTATIONS['requirement'](item)}")

    # Close the template
    if lines:
        lines[-1] = lines[-1] + "}}"
    return "\n".join(lines)
