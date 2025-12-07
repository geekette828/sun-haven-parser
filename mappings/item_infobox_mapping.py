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

def compute_sell(item: dict) -> str:
    """
    Returns semicolon-separated sell prices based on all nonzero sell fields.
    """
    sell_values = []
    if item.get("sellPrice", 0):
        sell_values.append(str(item.get("sellPrice")))
    if item.get("orbsSellPrice", 0):
        sell_values.append(str(item.get("orbsSellPrice")))
    if item.get("ticketSellPrice", 0):
        sell_values.append(str(item.get("ticketSellPrice")))

    return "; ".join(sell_values)

def compute_currency(item: dict) -> str:
    """
    Returns semicolon-separated sell types based on which sell fields are nonzero.
    """
    sell_types = []
    if item.get("sellPrice", 0):
        sell_types.append("coins")
    if item.get("orbsSellPrice", 0):
        sell_types.append("orbs")
    if item.get("ticketSellPrice", 0):
        sell_types.append("tickets")

    return "; ".join(sell_types)

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

    # Handle foodStat
    for stat in item.get("foodStat", []):
        increase_raw = stat.get("increase")
        if increase_raw is None:
            continue
        # Skip sentinel
        if str(increase_raw) == "999":
            continue
        stat_id = int(stat.get("stat", -1))
        stat_name = constants.STAT_TYPE_MAPPING.get(stat_id, f"Stat{stat_id}")
        increase = int(increase_raw)
        inc_text = constants.FOOD_STAT_INCREASES.get(increase, f"+{increase}")
        parts.append(f"{stat_name}»({inc_text})")

    # Handle statBuff
    for buff in item.get("statBuff", []):
        value_raw = buff.get("value")
        if value_raw is None:
            continue
        # Skip sentinel
        if str(value_raw) == "999":
            continue
        value = float(value_raw)
        if value == 999:
            continue
        stat_type = int(buff.get("statType", -1))
        stat_name = constants.STAT_TYPE_MAPPING.get(stat_type, f"Stat{stat_type}")
        duration = int(buff.get("duration") or 0)
        value_text = (
            f"{int(value * 100)}%" if value <= 1 else str(int(value))
        )
        minutes = duration // 60
        parts.append(f"{stat_name}«{value_text}»({minutes}m)")

    # Handle maxStats
    for max_stat in item.get("maxStats", []):
        value_raw = max_stat.get("value")
        if value_raw is None:
            continue
        # Skip sentinel
        if str(value_raw) == "999":
            continue
        value = int(value_raw)
        if value == 999:
            continue
        stat_type = int(max_stat.get("statType", -1))
        stat_name = constants.STAT_TYPE_MAPPING.get(stat_type, f"Stat{stat_type}")
        parts.append(f"{stat_name}»(+{value})")

    # Final output: return blank if nothing valid
    return "; ".join(parts) if parts else ""


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
    else:  # <-- Fallback: even if skill not found, still return the number
        return str(required_level)

def compute_placement_type(item):
    if str(item.get("placeableOnTables", 0)) == "1":
        return "Surface"
    elif str(item.get("placeableOnWalls", 0)) == "1":
        return "Wall"
    else:
        return "Floor"

def compute_is_rotatable(item):
    return "True" if item.get("canRotate") is True else "False"

# ---------------------------
# Computed-only fields (not tied to a single JSON key)
# ---------------------------
FIELD_COMPUTATIONS: Dict[str, Callable[[dict], str]] = {
    "sell": compute_sell,
    "currency": compute_currency,
    "restores": compute_restores,
    "statInc": compute_statInc,
    "season": compute_season,
    "exp": compute_exp,
    "organic": compute_organic,
    "requirement": lambda item: compute_requirement(item, classify_item(item)),
    "placementType": compute_placement_type,
    "isRotatable": compute_is_rotatable,
}

def _choose_infobox(itemType: str, subtype: str, category: str) -> Tuple[str, bool]:
    """
    Decide which infobox template to use based on classification, and whether the
    result should be flagged for manual review.

    Returns:
      (template_name, needs_review_flag)
    """
    # Animal items → Animal infobox.
    if itemType == "Animal":
        return "Animal infobox", False

    # Equipment vs Clothing.
    if itemType == "Equipment":
        if subtype == "Clothing":
            # Clothing subset uses Clothing infobox.
            return "Clothing infobox", False
        # Weapons, Tools, Armor, Accessories → Equipment infobox.
        return "Equipment infobox", False

    # Furniture (including flooring, wallpaper, decor).
    if itemType == "Furniture":
        return "Furniture infobox", False

    # Fish.
    if itemType == "Fish":
        return "Fish infobox", False

    # Consumables (meals, potions, non-forageable food).
    if itemType == "Consumable":
        return "Consumable infobox", False

    # FOOD Forageables → Consumable infobox.
    if itemType == "Forageables" and subtype == "Food":
        return "Consumable infobox", False

    # Generic Item infobox family (Mounts, Records, House Customization, non-food forageables).
    if itemType == "Item":
        known_item_subtypes = {
            "Mount",
            "Record",
            "House Customization",
            "Forageables",  # Non-food forageables become Item/Forageables/Resources
        }
        if subtype in known_item_subtypes:
            return "Item infobox", False
        # Unknown Item subtype → still Item infobox, but mark for review.
        return "Item infobox", True

    # Anything else (including empty classification or legacy "Building") →
    # fall back to Item infobox and flag for review.
    return "Item infobox", True

def format_infobox(item: dict, classification: Tuple[str, str, str], title: str) -> str:
    """
    Generates the complete infobox wikitext based on FIELD_MAP and FIELD_COMPUTATIONS.
    Chooses the proper infobox template (Animal / Equipment / Clothing / Furniture /
    Fish / Consumable / Item) based on the classification tuple.
    """
    itemType, subtype, category = classification

    # Decide which infobox to use and whether this needs a review category.
    template_name, needs_review = _choose_infobox(itemType, subtype, category)

    # Start template.
    lines = [f"{{{{{template_name}"]

    # Common core fields (shared across all infoboxes)
    sell = FIELD_COMPUTATIONS["sell"](item)
    if sell:
        lines.append(f"|sell = {sell}")

    currency = FIELD_COMPUTATIONS["currency"](item)
    if currency:
        lines.append(f"|currency = {currency}")

    for key in ["stack", "rarity", "hearts"]:
        json_key, normalize = FIELD_MAP[key]
        value = normalize(item.get(json_key))
        if value:
            lines.append(f"|{key} = {value}")

    # Classification fields per-infobox
    dlc_value = FIELD_MAP["dlc"][1](item.get(FIELD_MAP["dlc"][0], 0))

    # Item infobox keeps the full legacy classification block.
    if template_name == "Item infobox":
        lines.append("<!-- Item Classification -->")
        lines.append(f"|itemType = {itemType}")
        lines.append(f"|subtype = {subtype}")
        lines.append(f"|category = {category}")
        lines.append(f"|dlc = {dlc_value}")

    # Animal infobox: subtype + dlc.
    elif template_name == "Animal infobox":
        lines.append("<!-- Item Classification -->")
        if subtype:
            lines.append(f"|subtype = {subtype}")
        lines.append(f"|dlc = {dlc_value}")

    # Equipment infobox: subtype, category, dlc.
    elif template_name == "Equipment infobox":
        lines.append("<!-- Item Classification -->")
        if subtype:
            lines.append(f"|subtype = {subtype}")
        if category:
            lines.append(f"|category = {category}")
        lines.append(f"|dlc = {dlc_value}")

    # Clothing infobox: category, dlc.
    elif template_name == "Clothing infobox":
        lines.append("<!-- Item Classification -->")
        if category:
            lines.append(f"|category = {category}")
        lines.append(f"|dlc = {dlc_value}")

    # Furniture infobox: subtype, category, dlc.
    elif template_name == "Furniture infobox":
        lines.append("<!-- Item Classification -->")
        if subtype:
            lines.append(f"|subtype = {subtype}")
        if category:
            lines.append(f"|category = {category}")
        lines.append(f"|dlc = {dlc_value}")

    # Fish and Consumable infoboxes currently don’t have dlc in the templates you sent.
    # We only add classification if it makes sense.
    elif template_name == "Consumable infobox":
        lines.append("<!-- Item Classification -->")
        if subtype:
            lines.append(f"|subtype = {subtype}")
        if category:
            lines.append(f"|category = {category}")
        # no dlc field here by default

    # Early close for items that don’t use data section
    if subtype in ["Pet", "Wild Animal", "Mount", "Record", "House Customization"]:
        # Close current last line with braces and return.
        if lines:
            lines[-1] = lines[-1] + "  }}"
        result = "\n".join(lines)
        if needs_review:
            result += "\n[[Category:Review item infobox]]"
        return result

    # Data section (keyed on itemType/subtype)
    lines.append("<!-- Item Data-->")

    # Furniture data → placementType, isRotatable, set
    if itemType == "Furniture":
        placement = ""
        if str(item.get("placeableOnTables", 0)) == "1":
            placement = "Surface"
        elif str(item.get("placeableOnWalls", 0)) == "1":
            placement = "Wall"
        else:
            placement = "Floor"
        lines.append(f"|placementType = {placement}")
        rotatable = "True" if item.get("canRotate") is True else "False"
        lines.append(f"|isRotatable = {rotatable}")
        lines.append("|set = ")

    # Barn Animal data → region, produces, capacity
    elif subtype == "Barn Animal":
        lines.append("|region = ")
        lines.append("|produces = ")
        lines.append("|capacity = ")

    # Potion / Food / Fish data
    elif subtype == "Potion":
        lines.append(f"|restores = {FIELD_COMPUTATIONS['restores'](item)}")
        lines.append(f"|statInc = {FIELD_COMPUTATIONS['statInc'](item)}")
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

    # Clothing / Armor / Accessory / Weapon / Tool data
    elif subtype == "Clothing":
        lines.append("|set = ")
    elif subtype in ["Armor", "Accessory"]:
        lines.append("|set = ")
        lines.append(f"|effect = {compute_effect(item)}")
        lines.append(f"|requirement = {FIELD_COMPUTATIONS['requirement'](item)}")
    elif subtype in ["Tool", "Weapon"]:
        lines.append(f"|requirement = {FIELD_COMPUTATIONS['requirement'](item)}")

    # Flags shared with Consumable / Forageable behavior
    # (topShelf / rareFinds) – appear on Consumable & Item infoboxes
    if str(item.get("isAnimalProduct", 0)) == "1":
        lines.append("|topShelf = true")
    if str(item.get("isForageable", 0)) == "1":
        lines.append("|rareFinds = true")

    # Close template and optionally add review category
    if lines:
        lines[-1] = lines[-1] + "  }}"
    result = "\n".join(lines)
    if needs_review:
        result += "\n[[Category:Review item infobox]]"
    return result
