import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import config.constants as constants

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
    """
    Computes the 'statInc' value from the foodStat field.
    If any foodStat entry has "increase": "999", returns an empty string.
    Otherwise, each entry is formatted as:
         <STAT_NAME>»(<mapped increase>)
    Multiple entries are joined by a semicolon.
    """
    parts = []

    # Handle foodStat
    for stat in item.get("foodStat", []):
        if stat.get("increase") == "999":
            continue
        stat_id = int(stat.get("stat", -1))
        stat_name = constants.STAT_TYPE_MAPPING.get(stat_id, f"Stat{stat_id}")
        increase_text = constants.FOOD_STAT_INCREASES.get(int(stat.get("increase")), f"+{stat.get('increase')}")
        parts.append(f"{stat_name}»({increase_text})")

    # Handle statBuff
    for buff in item.get("statBuff", []):
        stat_type = int(buff.get("statType", -1))
        value = float(buff.get("value", 0))
        duration = int(buff.get("duration", 0))
        stat_name = constants.STAT_TYPE_MAPPING.get(stat_type, f"Stat{stat_type}")
        display_value = f"{int(value * 100)}%" if value <= 1 else f"{int(value)}"
        minutes = int(duration // 60)
        parts.append(f"{stat_name}«{display_value}»({minutes}m)")

    return "; ".join(parts)

def compute_organic(item):
    isFruit = item.get("isFruit")
    if isFruit is None or isFruit == "":
        return ""
    try:
        isFruit = int(isFruit)
    except Exception:
        return ""
    return "True" if isFruit == 1 else "False"

def compute_season(item):
    has_set = item.get("hasSetSeason")
    if has_set is None or has_set == "":
        return ""
    try:
        has_set = int(has_set)
    except Exception:
        return ""
    
    if has_set == 1:
        set_season = item.get("setSeason")
        try:
            set_season = int(set_season)
        except Exception:
            return ""
        return constants.SEASONS.get(set_season, "")
    elif has_set == 0:
        return "Any"
    return ""

def compute_exp(item):
    exp = item.get("experience")
    if exp is None:
        return ""
    return str(exp)

def compute_effect(item):
    stats = item.get("stats", [])
    effects = []
    for stat in stats:
        try:
            stat_type = int(stat.get("statType", 999))
            value = stat.get("value", 0)
        except Exception:
            continue
        stat_name = constants.STAT_TYPE_MAPPING.get(stat_type, "none")
        effects.append(f"{stat_name}»{value}")
    return "; ".join(effects)

def compute_requirement(item, classification):
    required_level = item.get("requiredLevel")
    if required_level is None or required_level == 0 or required_level == "":
        return ""
    
    itemType, subtype, category = classification
    skill = ""
    # For Armor and Accessory, use Combat.
    if subtype in ["Armor", "Accessory"]:
        skill = "Combat"
    # Determine based on category for tools:
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

def format_item_data(classification, item):
    itemType, subtype, _ = classification
    data_lines = []
    
    if subtype == "Barn Animal":
        data_lines.append("<!-- Item Data-->")
        data_lines.append("|region      = ")
        data_lines.append("|produces    = ")
        data_lines.append("|capacity    = ")
    elif itemType == "Furniture":
        return ""
    elif subtype in ["Pet", "Wild Animal"]:
        return ""
    elif subtype == "Food":
        restores = compute_restores(item)
        statInc = compute_statInc(item)
        organic = compute_organic(item)
        data_lines.append("<!-- Item Data-->")
        data_lines.append("|restores    = " + restores)
        data_lines.append("|statInc     = " + statInc)
        data_lines.append("|organic     = " + organic)
    elif itemType == "Fish":
        restores = compute_restores(item)
        statInc = compute_statInc(item)
        season = compute_season(item)
        exp = compute_exp(item)
        data_lines.append("<!-- Item Data-->")
        data_lines.append("|restores    = " + restores)
        data_lines.append("|statInc     = " + statInc)
        data_lines.append("|region      = ")
        data_lines.append("|season      = " + season)
        data_lines.append("|exp         = " + exp)
    elif subtype in ["Clothing"]:
        data_lines.append("<!-- Item Data-->")
        data_lines.append("|armorset    = ")
    elif subtype in ["Armor", "Accessory"]:
        effect_val = compute_effect(item)
        req_val = compute_requirement(item, classification)
        data_lines.append("<!-- Item Data-->")
        data_lines.append("|armorset    = ")
        data_lines.append("|effect      = " + effect_val)
        data_lines.append("|requirement = " + req_val)
    elif subtype in ["Tool", "Weapon"]:
        req_val = compute_requirement(item, classification)
        data_lines.append("<!-- Item Data-->")
        data_lines.append("|requirement = " + req_val)
    
    return "\n".join(data_lines)
