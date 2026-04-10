"""
All enemy infoboxes exporter — Layer 3 of the pipeline.

Reads entities_data.json and writes all_enemy_infobox.txt with
{{Enemy infobox}} wikitext for each enemy.

Usage:
    python exporters/all_enemy_infoboxes.py
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils import file_utils, json_utils
from utils.text_utils import normalize_for_compare

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ENTITIES_DATA = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "entities_data.json")
_OUTPUT_FILE   = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "all_enemy_infobox.txt")
_DEBUG_LOG     = os.path.join(constants.DEBUG_DIRECTORY, "all_enemy_infobox_debug.txt")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_damage_type(entry: dict) -> str:
    return "Melee" if "damage_range" in entry else "Ranged"


def _extract_damage_range(entry: dict) -> str:
    if "damage_range" in entry:
        match = re.search(r"\{x:\s*(\d+),\s*y:\s*(\d+)\}", entry["damage_range"])
        if match:
            return f"{match.group(1)}-{match.group(2)}"
    return ""


def _strip_season(name: str) -> str:
    return re.sub(r"_(Spring|Summer|Fall|Winter)", "", name, flags=re.IGNORECASE)


def _int_or_val(val):
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_OUTPUT_FILE))
    file_utils.ensure_dir_exists(os.path.dirname(_DEBUG_LOG))

    # Reset debug log
    with open(_DEBUG_LOG, "w", encoding="utf-8") as f:
        f.write("")

    data = json_utils.load_json(_ENTITIES_DATA)

    grouped: dict = defaultdict(lambda: {
        "title":       None,
        "exp":         None,
        "damage_type": None,
        "levels":      {},
        "damage":      {},
        "combat_dungeon": False,
    })

    enemy_to_prefab: dict = {}
    prefab_to_enemy: dict = {}

    # First pass — wild monsters
    for key, entry in data.items():
        if "enemy_name" not in entry or "prefab" not in entry:
            continue
        prefab = re.sub(r"_0$", "", entry["prefab"])
        title = entry["enemy_name"]
        norm_prefab = normalize_for_compare(prefab)
        norm_title  = normalize_for_compare(title)

        enemy_to_prefab[norm_title]  = prefab
        prefab_to_enemy[norm_prefab] = title

        grouped[prefab]["title"]       = title
        grouped[prefab]["exp"]         = entry.get("exp", "")
        grouped[prefab]["damage_type"] = _get_damage_type(entry)

        if "damage_range" in entry:
            level = entry.get("powerLevel") or entry.get("level")
            if level is not None:
                grouped[prefab]["damage"][f"Lv{level}"] = _extract_damage_range(entry)

        level = entry.get("powerLevel") or entry.get("level")
        if level is not None:
            grouped[prefab]["levels"][f"Lv{level}"] = {
                "health":  entry.get("health", ""),
                "defense": entry.get("defense", ""),
            }

    # Second pass — combat dungeon monsters
    for key, entry in data.items():
        if not re.search(r"_CombatDungeon\d+$", key):
            continue

        base_key  = re.sub(r"_CombatDungeon\d+$", "", key)
        base_key  = _strip_season(base_key)
        norm_base = normalize_for_compare(base_key)
        match_prefab = None

        for candidate in grouped:
            norm_c = normalize_for_compare(candidate)
            norm_t = normalize_for_compare(grouped[candidate]["title"] or "")
            if norm_c == norm_base or norm_t == norm_base:
                match_prefab = candidate
                break

        if not match_prefab:
            for norm_k, fallback_prefab in enemy_to_prefab.items():
                if norm_k == norm_base and fallback_prefab in grouped:
                    match_prefab = fallback_prefab
                    break

        if not match_prefab:
            with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
                f.write(f"Unmatched CombatDungeon variant: {key} → {base_key}\n")
            continue

        grouped[match_prefab]["combat_dungeon"] = True
        level = entry.get("powerLevel")
        if level is not None:
            level_key = f"Lv{level}"
            health  = entry.get("health", "")
            defense = entry.get("defense", "")
            existing = grouped[match_prefab]["levels"].get(level_key)
            if existing and (existing["health"] != health or existing["defense"] != defense):
                with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
                    f.write(
                        f"Discrepancy for {match_prefab} at Lv{level}: "
                        f"health {existing['health']} vs {health} / "
                        f"defense {existing['defense']} vs {defense}\n"
                    )
            grouped[match_prefab]["levels"][level_key] = {"health": health, "defense": defense}

    lines: list[str] = []
    for base, info in sorted(grouped.items()):
        if not info["title"]:
            continue

        lines.append("{{Enemy infobox")
        lines.append(f"|title = {info['title']}")
        lines.append("|region = ")
        lines.append("|subregion = ")
        lines.append(f"|combatDungeon = {'True' if info['combat_dungeon'] else 'False'}")
        lines.append(f"|exp = {_int_or_val(info['exp'])}")
        lines.append(f"|damageType = {info['damage_type']}")

        levels_sorted = sorted(info["levels"].items(), key=lambda x: int(x[0][2:]))
        level_list = [lvl for lvl, _ in levels_sorted]

        if len(level_list) == 1:
            single_lvl = level_list[0]
            stats = levels_sorted[0][1]
            lines.append(f"|level = {single_lvl[2:]}")
            lines.append(f"|health = {_int_or_val(stats['health'])}")
            lines.append(f"|defense = {_int_or_val(stats['defense'])}")
            if single_lvl in info["damage"]:
                lines.append(f"|damage = {info['damage'][single_lvl]}")
        else:
            lines.append(f"|level = {', '.join(level_list)}")
            for lvl, stats in levels_sorted:
                lines.append(f"|{lvl}_health = {_int_or_val(stats['health'])}")
                lines.append(f"|{lvl}_defense = {_int_or_val(stats['defense'])}")
                if lvl in info["damage"]:
                    lines.append(f"|{lvl}_damage = {info['damage'][lvl]}")

        lines.append("}}\n")

    with open(_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ Enemy infoboxes written to {_OUTPUT_FILE}")


if __name__ == "__main__":
    run()
