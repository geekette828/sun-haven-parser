"""
Wiki field-comparison tables for the Item Infobox template.

Maps infobox template parameters to item JSON fields for the compare and
update tools. Wikitext generation lives in formatters/item/item_infobox.py.

Exports:
  FIELD_MAP          – template_param -> (json_field_key, normalization_fn)
  FIELD_COMPUTATIONS – template_param -> fn(item_dict) -> str
"""

from typing import Dict, Tuple, Callable, Any
from mappings.item_classification import classify_item
from utils.text_utils import clean_whitespace, normalize_apostrophe
import config.constants as constants


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _text(v: Any) -> str:
    return clean_whitespace(normalize_apostrophe(str(v or "")))


def _int_str(v: Any) -> str:
    return str(int(v)) if v not in (None, "", "null") else ""


# ---------------------------------------------------------------------------
# Field map — raw JSON key → normalised string
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Computed field helpers
# ---------------------------------------------------------------------------

def compute_sell(item: dict) -> str:
    sell_values = []
    if item.get("sellPrice", 0):
        sell_values.append(str(item.get("sellPrice")))
    if item.get("orbsSellPrice", 0):
        sell_values.append(str(item.get("orbsSellPrice")))
    if item.get("ticketSellPrice", 0):
        sell_values.append(str(item.get("ticketSellPrice")))
    return "; ".join(sell_values)


def compute_currency(item: dict) -> str:
    sell_types = []
    if item.get("sellPrice", 0):
        sell_types.append("coins")
    if item.get("orbsSellPrice", 0):
        sell_types.append("orbs")
    if item.get("ticketSellPrice", 0):
        sell_types.append("tickets")
    return "; ".join(sell_types)


def compute_restores(item: dict) -> str:
    health = item.get("health", 0)
    mana = item.get("mana", 0)
    parts = []
    if isinstance(health, (int, float)) and health > 0:
        parts.append(f"Health»+{health}")
    if isinstance(mana, (int, float)) and mana > 0:
        parts.append(f"Mana»+{mana}")
    return "; ".join(parts)


def compute_stat_inc(item: dict) -> str:
    parts = []
    for stat in item.get("foodStat", []):
        increase_raw = stat.get("increase")
        if increase_raw is None or str(increase_raw) == "999":
            continue
        stat_id = int(stat.get("stat", -1))
        stat_name = constants.STAT_TYPE_MAPPING.get(stat_id, f"Stat{stat_id}")
        inc_text = constants.FOOD_STAT_INCREASES.get(int(increase_raw), f"+{int(increase_raw)}")
        parts.append(f"{stat_name}»({inc_text})")
    for buff in item.get("statBuff", []):
        value_raw = buff.get("value")
        if value_raw is None or str(value_raw) == "999":
            continue
        value = float(value_raw)
        if value == 999:
            continue
        stat_type = int(buff.get("statType", -1))
        stat_name = constants.STAT_TYPE_MAPPING.get(stat_type, f"Stat{stat_type}")
        duration = int(buff.get("duration") or 0)
        value_text = f"{int(value * 100)}%" if value <= 1 else str(int(value))
        parts.append(f"{stat_name}«{value_text}»({duration // 60}m)")
    for max_stat in item.get("maxStats", []):
        value_raw = max_stat.get("value")
        if value_raw is None or str(value_raw) == "999":
            continue
        try:
            value_f = float(value_raw)
        except (TypeError, ValueError):
            continue
        if value_f == 999:
            continue
        value_text = str(int(value_f)) if value_f.is_integer() else str(round(value_f, 2)).rstrip("0").rstrip(".")
        stat_type = int(max_stat.get("statType", -1))
        stat_name = constants.STAT_TYPE_MAPPING.get(stat_type, f"Stat{stat_type}")
        parts.append(f"{stat_name}»+{value_text}")
    return "; ".join(parts) if parts else ""


def compute_organic(item: dict) -> str:
    try:
        return "True" if int(item.get("isFruit", "")) == 1 else "False"
    except (TypeError, ValueError):
        return ""


def compute_season(item: dict) -> str:
    has_set = item.get("hasSetSeason")
    try:
        if int(has_set) == 1:
            return constants.SEASONS.get(int(item.get("setSeason", -1)), "")
        elif int(has_set) == 0:
            return "Any"
    except (TypeError, ValueError):
        pass
    return ""


def compute_exp(item: dict) -> str:
    return str(item.get("experience", "") or "")


def compute_effect(item: dict) -> str:
    effects = []
    for stat in item.get("stats", []):
        try:
            stat_type = int(stat.get("statType", 999))
            value = stat.get("value", 0)
            stat_name = constants.STAT_TYPE_MAPPING.get(stat_type, "none")
            effects.append(f"{stat_name}»{value}")
        except (TypeError, ValueError):
            continue
    return "; ".join(effects)


def compute_uniformity(item: dict) -> str:
    try:
        return "False" if int(item.get("armorSet", "")) == 0 else "True"
    except (TypeError, ValueError):
        return ""


def compute_requirement(item: dict, classification: tuple) -> str:
    required_level = item.get("requiredLevel")
    if not required_level:
        return ""
    itemType, subtype, category = classification
    skill = ""
    if subtype in ["Armor", "Accessory", "Weapon"]:
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
    return str(required_level)


def compute_placement_type(item: dict) -> str:
    if str(item.get("placeableOnTables", 0)) == "1":
        return "Surface"
    elif str(item.get("placeableOnWalls", 0)) == "1":
        return "Wall"
    return "Floor"


def compute_is_rotatable(item: dict) -> str:
    return "True" if item.get("canRotate") is True else "False"


# ---------------------------------------------------------------------------
# Computed-only fields (not tied to a single JSON key)
# ---------------------------------------------------------------------------

FIELD_COMPUTATIONS: Dict[str, Callable[[dict], str]] = {
    "sell": compute_sell,
    "currency": compute_currency,
    "restores": compute_restores,
    "statInc": compute_stat_inc,
    "season": compute_season,
    "exp": compute_exp,
    "organic": compute_organic,
    "requirement": lambda item: compute_requirement(item, classify_item(item)),
    "placementType": compute_placement_type,
    "isRotatable": compute_is_rotatable,
    "uniformity": compute_uniformity,
}
