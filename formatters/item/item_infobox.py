"""
Item infobox exporter.

Accepts an ItemData object and returns wikitext for the appropriate
infobox template (Item / Equipment / Clothing / Furniture / Fish /
Consumable / Animal).

Replaces: mappings/item_infobox_mapping.py + formatter/page_section/item_infobox.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import config.constants as constants
from builders.item_data import ItemClassification, ItemData
from utils.text_utils import clean_whitespace, normalize_apostrophe


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _text(value: object) -> str:
    return clean_whitespace(normalize_apostrophe(str(value or "")))


def _int_str(value: object) -> str:
    try:
        return str(int(value)) if value not in (None, "", "null") else ""
    except (TypeError, ValueError):
        return ""


# ---------------------------------------------------------------------------
# Computed field functions  (all accept ItemData directly)
# ---------------------------------------------------------------------------

def compute_sell(item: ItemData) -> str:
    """Semicolon-separated sell prices for all nonzero sell fields."""
    parts = []
    if item.sell_price:
        parts.append(str(item.sell_price))
    if item.orbs_sell_price:
        parts.append(str(item.orbs_sell_price))
    if item.ticket_sell_price:
        parts.append(str(item.ticket_sell_price))
    return "; ".join(parts)


def compute_currency(item: ItemData) -> str:
    """Semicolon-separated currency types for all nonzero sell fields."""
    parts = []
    if item.sell_price:
        parts.append("coins")
    if item.orbs_sell_price:
        parts.append("orbs")
    if item.ticket_sell_price:
        parts.append("tickets")
    return "; ".join(parts)


def compute_restores(item: ItemData) -> str:
    parts = []
    if item.health and item.health > 0:
        parts.append(f"Health»+{item.health}")
    if item.mana and item.mana > 0:
        parts.append(f"Mana»+{item.mana}")
    return "; ".join(parts)


def compute_stat_inc(item: ItemData) -> str:
    parts = []

    for food in item.food_stat:
        if food.increase is None or str(food.increase) == "999":
            continue
        stat_name = constants.STAT_TYPE_MAPPING.get(food.stat, f"Stat{food.stat}")
        tier_name = constants.FOOD_STAT_INCREASES.get(int(food.increase))
        if tier_name is not None:
            parts.append(f"{stat_name}»({tier_name.lower()})")
        else:
            parts.append(f"{stat_name}»{int(food.increase)}")

    for buff in item.stat_buff:
        if buff.value is None or str(buff.value) == "999" or buff.value == 999:
            continue
        stat_name = constants.STAT_TYPE_MAPPING.get(buff.stat_type, f"Stat{buff.stat_type}")
        value_text = (
            f"{int(buff.value * 100)}%" if buff.value <= 1 else str(int(buff.value))
        )
        minutes = buff.duration // 60
        parts.append(f"{stat_name}«{value_text}»({minutes}m)")

    for max_stat in item.max_stats:
        if max_stat.value is None or str(max_stat.value) == "999" or max_stat.value == 999:
            continue
        value_f = float(max_stat.value)
        value_text = str(int(value_f)) if value_f.is_integer() else str(round(value_f, 2)).rstrip("0").rstrip(".")
        stat_name = constants.STAT_TYPE_MAPPING.get(max_stat.stat_type, f"Stat{max_stat.stat_type}")
        parts.append(f"{stat_name}»+{value_text}")

    for exp_entry in item.exps:
        if not exp_entry.amount:
            continue
        profession_name = constants.PROFESSION_EXP.get(exp_entry.profession, f"Profession{exp_entry.profession}")
        parts.append(f"{profession_name} EXP»{exp_entry.amount}")

    return "; ".join(parts)


def compute_organic(item: ItemData) -> str:
    return "True" if item.is_fruit else "False"


def compute_season(item: ItemData) -> str:
    if item.has_set_season is None:
        return ""
    try:
        if int(item.has_set_season) == 1:
            return constants.SEASONS.get(int(item.set_season or -1), "")
        elif int(item.has_set_season) == 0:
            return "Any"
    except (TypeError, ValueError):
        pass
    return ""


def compute_exp(item: ItemData) -> str:
    return str(item.exp) if item.exp is not None else ""


def compute_effect(item: ItemData) -> str:
    parts = []
    for stat in item.stats:
        stat_name = constants.STAT_TYPE_MAPPING.get(stat.stat_type, "none")
        parts.append(f"{stat_name}»{stat.value}")
    return "; ".join(parts)


def compute_uniformity(item: ItemData) -> str:
    if item.armor_set is None:
        return ""
    return "False" if int(item.armor_set) == 0 else "True"


def compute_requirement(item: ItemData) -> str:
    if not item.required_level:
        return ""
    cls = item.classification
    if not cls:
        return str(item.required_level)
    skill_map = {
        ("Armor",): "Combat",
        ("Accessory",): "Combat",
        ("Weapon",): "Combat",
        ("Hoe",): "Farming",
        ("Watering Can",): "Farming",
        ("Pickaxe",): "Mining",
        ("Axe",): "Exploration",
        ("Rod",): "Fishing",
        ("Net",): "Fishing",
    }
    skill = ""
    for keys, skill_name in skill_map.items():
        if cls.subtype in keys or cls.category in keys:
            skill = skill_name
            break
    if skill:
        return f"{{{{SkillLevel|{skill}|{item.required_level}}}}}"
    return str(item.required_level)


def compute_placement_type(item: ItemData) -> str:
    if item.placeable_on_tables:
        return "Surface"
    if item.placeable_on_walls:
        return "Wall"
    return "Floor"


def compute_is_rotatable(item: ItemData) -> str:
    return "True" if item.can_rotate else "False"


# ---------------------------------------------------------------------------
# Infobox template selection
# ---------------------------------------------------------------------------

def _choose_infobox(cls: ItemClassification) -> tuple[str, bool]:
    """Return (template_name, needs_review_flag)."""
    if cls.item_type == "Animal":
        return "Animal infobox", False
    if cls.item_type == "Equipment":
        if cls.subtype == "Clothing":
            return "Clothing infobox", False
        return "Equipment infobox", False
    if cls.item_type == "Furniture":
        return "Furniture infobox", False
    if cls.item_type == "Fish":
        return "Fish infobox", False
    if cls.item_type == "Consumable":
        return "Consumable infobox", False
    if cls.item_type == "Forageables" and cls.subtype == "Food":
        return "Consumable infobox", False
    if cls.item_type == "Item":
        known_subtypes = {"Mount", "Record", "House Customization", "Forageables"}
        if cls.subtype in known_subtypes:
            return "Item infobox", False
        return "Item infobox", True
    return "Item infobox", True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_infobox(item: ItemData) -> str:
    """
    Generate the complete infobox wikitext for the given item.

    Returns an empty string if the item has no classification.
    """
    cls = item.classification
    if cls is None:
        return ""

    template_name, needs_review = _choose_infobox(cls)
    dlc_value = "True" if item.is_dlc else "False"

    lines = [f"{{{{{template_name}"]

    # --- Core fields shared across all infoboxes ---
    sell = compute_sell(item)
    if sell:
        lines.append(f"|sell = {sell}")

    currency = compute_currency(item)
    if currency:
        lines.append(f"|currency = {currency}")

    for label, value in [
        ("stack", _int_str(item.stack_size)),
        ("rarity", _int_str(item.rarity)),
        ("hearts", _int_str(item.hearts)),
    ]:
        if value:
            lines.append(f"|{label} = {value}")

    # --- Classification block (varies by template) ---
    lines.append("<!-- Item Classification -->")

    if template_name == "Item infobox":
        lines.append(f"|itemType = {cls.item_type}")
        lines.append(f"|subtype = {cls.subtype}")
        lines.append(f"|category = {cls.category}")
        lines.append(f"|dlc = {dlc_value}")

    elif template_name == "Animal infobox":
        if cls.subtype:
            lines.append(f"|subtype = {cls.subtype}")
        lines.append(f"|dlc = {dlc_value}")

    elif template_name == "Equipment infobox":
        if cls.subtype:
            lines.append(f"|subtype = {cls.subtype}")
        if cls.category:
            lines.append(f"|category = {cls.category}")
        lines.append(f"|dlc = {dlc_value}")

    elif template_name == "Clothing infobox":
        if cls.category:
            lines.append(f"|category = {cls.category}")
        lines.append(f"|dlc = {dlc_value}")

    elif template_name == "Furniture infobox":
        if cls.subtype:
            lines.append(f"|subtype = {cls.subtype}")
        if cls.category:
            lines.append(f"|category = {cls.category}")
        lines.append(f"|dlc = {dlc_value}")

    elif template_name == "Consumable infobox":
        if cls.subtype:
            lines.append(f"|subtype = {cls.subtype}")
        if cls.category:
            lines.append(f"|category = {cls.category}")

    # --- Early close for items with no data section ---
    no_data_subtypes = {"Pet", "Wild Animal", "Mount", "Record", "House Customization"}
    if cls.subtype in no_data_subtypes:
        lines[-1] = lines[-1] + "  }}"
        result = "\n".join(lines)
        if needs_review:
            result += "\n[[Category:Review item infobox]]"
        return result

    # --- Data section ---
    lines.append("<!-- Item Data-->")

    if cls.item_type == "Furniture":
        lines.append(f"|placementType = {compute_placement_type(item)}")
        lines.append(f"|isRotatable = {compute_is_rotatable(item)}")
        lines.append("|set = ")

    elif cls.subtype == "Barn Animal":
        lines.append("|region = ")
        lines.append("|produces = ")
        lines.append("|capacity = ")

    elif cls.subtype == "Potion":
        lines.append(f"|restores = {compute_restores(item)}")
        lines.append(f"|statInc = {compute_stat_inc(item)}")

    elif cls.subtype == "Food":
        lines.append(f"|restores = {compute_restores(item)}")
        lines.append(f"|statInc = {compute_stat_inc(item)}")
        lines.append(f"|organic = {compute_organic(item)}")

    elif cls.item_type == "Fish":
        lines.append(f"|restores = {compute_restores(item)}")
        lines.append(f"|statInc = {compute_stat_inc(item)}")
        lines.append("|region = ")
        lines.append(f"|season = {compute_season(item)}")
        lines.append(f"|exp = {compute_exp(item)}")

    elif cls.subtype == "Clothing":
        lines.append("|set = ")

    elif cls.subtype in ("Armor", "Accessory"):
        lines.append(f"|effect = {compute_effect(item)}")
        lines.append(f"|requirement = {compute_requirement(item)}")
        lines.append("|set = ")
        lines.append(f"|uniformity = {compute_uniformity(item)}")

    elif cls.subtype in ("Tool", "Weapon"):
        lines.append(f"|requirement = {compute_requirement(item)}")

    # --- Shared flags ---
    if item.is_animal_product:
        lines.append("|topShelf = true")
    if item.is_forageable:
        lines.append("|rareFinds = true")

    # --- Close template ---
    lines[-1] = lines[-1] + "  }}"
    result = "\n".join(lines)
    if needs_review:
        result += "\n[[Category:Review item infobox]]"
    return result
