import os
import re
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils import file_utils
from utils.text_utils import normalize_for_compare
from collections import defaultdict

# Define paths
entities_data_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "entities_data.json")
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "all_enemy_infobox.txt")
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "all_enemy_infobox_debug.txt")
file_utils.ensure_dir_exists(os.path.dirname(output_file))
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

# Reset debug log
with open(debug_log_path, 'w', encoding='utf-8') as f:
    f.write("")

def load_entities():
    with open(entities_data_file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_damage_type(entry):
    return "Melee" if "damageRange" in entry else "Ranged"

def extract_damage_range(entry):
    if "damageRange" in entry:
        match = re.search(r"{x:\s*(\d+),\s*y:\s*(\d+)}", entry["damageRange"])
        if match:
            return f"{match.group(1)}-{match.group(2)}"
    return ""

def log_discrepancy(prefab, level, a, b):
    with open(debug_log_path, 'a', encoding='utf-8') as f:
        f.write(f"Discrepancy for {prefab} at Lv{level}: health {a['health']} vs {b['health']} / defense {a['defense']} vs {b['defense']}\n")

def log_unmatched_dungeon(key):
    with open(debug_log_path, 'a', encoding='utf-8') as f:
        f.write(f"Unmatched CombatDungeon variant: {key}\n")

def strip_season(name):
    # Remove _Spring, _Summer, _Fall, _Winter regardless of surrounding underscores
    return re.sub(r'_(Spring|Summer|Fall|Winter)', '', name, flags=re.IGNORECASE)

def main():
    data = load_entities()

    grouped = defaultdict(lambda: {
        "title": None,
        "exp": None,
        "damageType": None,
        "levels": {},
        "damage": {},
        "combatDungeon": False
    })

    enemy_to_prefab = {}
    prefab_to_enemy = {}

    # First pass - wild monsters
    for key, entry in data.items():
        if "enemy name" not in entry or "prefab" not in entry:
            continue
        prefab = re.sub(r'_0$', '', entry["prefab"])
        title = entry["enemy name"]
        norm_prefab = normalize_for_compare(prefab)
        norm_title = normalize_for_compare(title)

        enemy_to_prefab[norm_title] = prefab
        prefab_to_enemy[norm_prefab] = title

        grouped[prefab]["title"] = title
        grouped[prefab]["exp"] = entry.get("exp", "")
        grouped[prefab]["damageType"] = get_damage_type(entry)
        if "damageRange" in entry:
            level = entry.get("powerLevel") or entry.get("level")
            if level is not None:
                grouped[prefab]["damage"][f"Lv{level}"] = extract_damage_range(entry)

        level = entry.get("powerLevel") or entry.get("level")
        if level is not None:
            level_key = f"Lv{level}"
            health = entry.get("health", "")
            defense = entry.get("defense", "")
            grouped[prefab]["levels"][level_key] = {"health": health, "defense": defense}

    # Second pass - combat dungeon monsters
    for key, entry in data.items():
        if not re.search(r"_CombatDungeon\d+$", key):
            continue

        base_key = re.sub(r"_CombatDungeon\d+$", "", key)
        base_key = strip_season(base_key)
        norm_base = normalize_for_compare(base_key)
        match_prefab = None

        for candidate in grouped:
            norm_candidate_prefab = normalize_for_compare(candidate)
            norm_candidate_title = normalize_for_compare(grouped[candidate]["title"] or "")
            if norm_candidate_prefab == norm_base or norm_candidate_title == norm_base:
                match_prefab = candidate
                break

        # Fallback: match by normalized enemy name using normalized lookup
        if not match_prefab:
            for norm_key, fallback_prefab in enemy_to_prefab.items():
                if norm_key == norm_base and normalize_for_compare(fallback_prefab) == normalize_for_compare(fallback_prefab) and fallback_prefab in grouped:
                    match_prefab = fallback_prefab
                    break

        if not match_prefab:
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                f.write(f"Trying to match dungeon variant: {key} → stripped: {base_key} → normalized: {norm_base} \n")
            log_unmatched_dungeon(key)
            continue

        grouped[match_prefab]["combatDungeon"] = True

        level = entry.get("powerLevel")
        if level is not None:
            level_key = f"Lv{level}"
            health = entry.get("health", "")
            defense = entry.get("defense", "")
            existing = grouped[match_prefab]["levels"].get(level_key)
            if existing and (existing["health"] != health or existing["defense"] != defense):
                log_discrepancy(match_prefab, level, existing, {"health": health, "defense": defense})
            grouped[match_prefab]["levels"][level_key] = {"health": health, "defense": defense}

    lines = []
    for base, info in sorted(grouped.items()):
        if not info["title"]:
            continue

        lines.append("{{Enemy infobox")
        lines.append(f"|title = {info['title']}")
        lines.append("|region = ")
        lines.append("|subregion = ")
        lines.append(f"|combatDungeon = {'True' if info['combatDungeon'] else 'False'}")
        lines.append(f"|exp = {int(info['exp']) if isinstance(info['exp'], float) and info['exp'].is_integer() else info['exp']}")
        lines.append(f"|damageType = {info['damageType']}")

        levels_sorted = sorted(info['levels'].items(), key=lambda x: int(x[0][2:]))
        level_list = [lvl for lvl, _ in levels_sorted]
        if len(level_list) == 1:
            single_lvl = level_list[0]
            lines.append(f"|level = {single_lvl[2:]}")
            lines.append(f"|health = {int(levels_sorted[0][1]['health']) if isinstance(levels_sorted[0][1]['health'], float) and levels_sorted[0][1]['health'].is_integer() else levels_sorted[0][1]['health']}")
            lines.append(f"|defense = {int(levels_sorted[0][1]['defense']) if isinstance(levels_sorted[0][1]['defense'], float) and levels_sorted[0][1]['defense'].is_integer() else levels_sorted[0][1]['defense']}")
            if single_lvl in info['damage']:
                lines.append(f"|damage = {info['damage'][single_lvl]}")
        else:
            lines.append(f"|level = {', '.join(level_list)}")

            for lvl, stats in levels_sorted:
                lines.append(f"|{lvl}_health = {int(stats['health']) if isinstance(stats['health'], float) and stats['health'].is_integer() else stats['health']}")
                lines.append(f"|{lvl}_defense = {int(stats['defense']) if isinstance(stats['defense'], float) and stats['defense'].is_integer() else stats['defense']}")
                if lvl in info['damage']:
                    lines.append(f"|{lvl}_damage = {info['damage'][lvl]}")
            lines.append(f"|{lvl}_health = {int(stats['health']) if isinstance(stats['health'], float) and stats['health'].is_integer() else stats['health']}")
            lines.append(f"|{lvl}_defense = {int(stats['defense']) if isinstance(stats['defense'], float) and stats['defense'].is_integer() else stats['defense']}")
            if lvl in info['damage']:
                lines.append(f"|{lvl}_damage = {info['damage'][lvl]}")

        lines.append("}}\n")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
    main()
