"""
Field mapping and formatter for the Item Infobox from items_data.json.
Exports:
  INFOBOX_FIELD_MAP
  INFOBOX_EXTRA_FIELDS
  format_infobox(item, classification, title)
"""

from typing import Dict, Tuple, Callable, Any
from utils.text_utils import clean_whitespace, normalize_apostrophe
import config.constants as constants


# Normalization Helpers
def _text(v: Any) -> str:
    return clean_whitespace(normalize_apostrophe(str(v or "")))

def _int_str(v: Any) -> str:
    return str(int(v)) if v not in (None, "", "null") else ""

def _float_str(v: Any) -> str:
    try:
        return str(round(float(v), 2))
    except:
        return ""


# Item-Specific Utilities
def get_sell_info(item: dict) -> Tuple[str, str]:
    """
    Determine which sell value and currency to use for the infobox.
    """
    if item.get("sellPrice", 0):
        return str(item["sellPrice"]), "coins"
    elif item.get("orbsSellPrice", 0):
        return str(item["orbsSellPrice"]), "orbs"
    elif item.get("ticketSellPrice", 0):
        return str(item["ticketSellPrice"]), "tickets"
    return "", ""


# Computed Field Helpers
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
        value = float(buff.get("value", 0))
        duration = int(buff.get("duration", 0))
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

# Field Map
INFOBOX_FIELD_MAP: Dict[str, Tuple[str, Callable[[Any], str], Callable[[dict, Tuple[str, str, str]], bool]]] = {
    "stack": ("stackSize", _int_str, lambda item, cls: True),
    "rarity": ("rarity", _int_str, lambda item, cls: True),
    "hearts": ("hearts", _int_str, lambda item, cls: True),
    "itemType": (None, lambda i, c: c[0], lambda i, c: True),
    "subtype":  (None, lambda i, c: c[1], lambda i, c: True),
    "category": (None, lambda i, c: c[2], lambda i, c: True),
}

# Item Infobox Formatter
def format_infobox(item: dict, classification: Tuple[str, str, str], title: str) -> str:
    itemType, subtype, category = classification
    if itemType == "Furniture" or subtype in ["Pet", "Wild Animal"]:
        return ""  # skip entirely

    lines = ["{{Item infobox"]

    # Core Fields
    name = item.get("Name", title)
    lines.append(f"|name = {name}")

    sell_val, sell_type = get_sell_info(item)
    if sell_val:
        lines.append(f"|sell = {sell_val}")
    if sell_type:
        lines.append(f"|selltype = {sell_type}")

    # Fields shown before classification
    for field in ["stack", "rarity", "hearts"]:
        json_key, norm_fn, condition_fn = INFOBOX_FIELD_MAP[field]
        if condition_fn(item, classification):
            value = norm_fn(item.get(json_key))
            if value:
                lines.append(f"|{field} = {value}")

    # Classification section
    lines.append("<!-- Item Classification -->")
    for field in ["itemType", "subtype", "category"]:
        _, norm_fn, _ = INFOBOX_FIELD_MAP[field]
        value = norm_fn(item, classification)
        lines.append(f"|{field} = {value}")

    dlc = item.get("isDLCItem", 0)
    lines.append(f"|dlc = {'True' if dlc == 1 else 'False'}")

    # Data section
    lines.append("<!-- Item Data-->")

    if subtype == "Barn Animal":
        lines.append("|region = ")
        lines.append("|produces = ")
        lines.append("|capacity = ")

    elif subtype == "Food":
        lines.append(f"|restores = {compute_restores(item)}")
        lines.append(f"|statInc = {compute_statInc(item)}")
        lines.append(f"|organic = {compute_organic(item)}")

    elif itemType == "Fish":
        lines.append(f"|restores = {compute_restores(item)}")
        lines.append(f"|statInc = {compute_statInc(item)}")
        lines.append("|region = ")
        lines.append(f"|season = {compute_season(item)}")
        lines.append(f"|exp = {compute_exp(item)}")

    elif subtype == "Clothing":
        lines.append("|armorset = ")

    elif subtype in ["Armor", "Accessory"]:
        lines.append("|armorset = ")
        lines.append(f"|effect = {compute_effect(item)}")
        lines.append(f"|requirement = {compute_requirement(item, classification)}")

    elif subtype in ["Tool", "Weapon"]:
        lines.append(f"|requirement = {compute_requirement(item, classification)}")

    # Append closing braces to the last line
    if lines:
        lines[-1] = lines[-1] + "}}"
    return "\n".join(lines)