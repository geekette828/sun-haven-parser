"""
Entity builder — Layer 1 of the pipeline.

Parses raw GameObject (.prefab) files and CombatDungeon (.unity) scene files
to extract enemy and NPC entity data, writing entities_data.json.

Usage:
    python builders/entity_builder.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils, json_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_GAMEDATA_DIR  = os.path.join(constants.INPUT_DIRECTORY, "GameObject")
_SCENES_DIR    = os.path.join(constants.INPUT_DIRECTORY, "Scenes")
_CACHE_FILE    = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "entities_data.json")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_drop_tables(lines: list[str]) -> dict:
    drop_tables = []
    current_table: list[dict] = []
    drop_id = None
    drop_chance = None
    inside_drops2 = False

    for line in lines:
        line = line.rstrip()
        stripped = line.strip()

        if "_drops2:" in stripped:
            inside_drops2 = True
            continue

        if inside_drops2:
            if "- drops:" in stripped:
                if current_table:
                    drop_tables.append(current_table)
                current_table = []
                continue
            elif not line.startswith(" "):
                break

            if "id:" in stripped:
                try:
                    drop_id = int(stripped.split("id:")[1].strip())
                except Exception:
                    drop_id = None
            elif "dropChance:" in stripped:
                try:
                    drop_chance = float(stripped.split("dropChance:")[1].strip())
                except Exception:
                    drop_chance = None
            elif "dropAmount:" in stripped:
                match = re.search(r"x:\s*(\d+),\s*y:\s*(\d+)", stripped)
                if match and drop_id is not None and drop_chance is not None:
                    current_table.append({
                        "id":          drop_id,
                        "drop_chance": drop_chance,
                        "drop_amount": int(match.group(1)),
                    })
                    drop_id = None
                    drop_chance = None

    if current_table:
        drop_tables.append(current_table)

    return {f"drop_table_{i + 1}": table for i, table in enumerate(drop_tables)}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_CACHE_FILE))
    entity_data: dict = {}

    # --- Prefab entities (NPCs, enemies, furniture) ---
    file_list = [f for f in os.listdir(_GAMEDATA_DIR) if f.endswith(".prefab")]
    total = len(file_list)
    step  = max(1, total // 5)

    for i, filename in enumerate(file_list, start=1):
        if i % step == 0:
            print(f"  🔄 {int((i / total) * 100)}% complete...")

        prefab_path = os.path.join(_GAMEDATA_DIR, filename)
        meta_path   = prefab_path + ".meta"
        prefab_name = os.path.splitext(filename)[0]

        try:
            lines   = file_utils.read_file_lines(prefab_path)
            content = "\n".join(lines)

            guid = "UNKNOWN"
            if os.path.exists(meta_path):
                for line in file_utils.read_file_lines(meta_path):
                    if "guid:" in line:
                        guid = line.split("guid:")[1].strip()
                        break

            entity: dict = {"prefab": prefab_name}

            enemy_name = re.search(r'(?<!key)enemyName:\s*"?([^\r\n":]+(?: [^\r\n":]+)*)"?', content)
            if enemy_name:
                name = enemy_name.group(1).strip()
                if name != "keyEnemyName":
                    entity["enemy_name"] = name

            entity["guid"] = guid

            for key, field, cast in [
                ("health",       "_health",              float),
                ("exp",          "_experience",          float),
                ("level",        "_powerLevel",          int),
                ("defense",      "defense",              int),
                ("has_attack",   "_hasAttack",           int),
                ("damage_range", "_damageRange",         str),
                ("damage_type",  "_damageType",          str),
                ("hit_type",     "_hitType",             str),
                ("hit_cooldown", "_hitCooldown",         float),
                ("knock_back",   "_knockBack",           float),
                ("npc_name",     "_npcName",             str),
                ("romanceable",  "_romanceable",         int),
                ("shop_keeper",  "_shopKeeper",          int),
                ("quests",       "_quests",              str),
            ]:
                match = re.search(rf"{field}:\s*(.+)", content)
                if match:
                    value = match.group(1).strip().strip('"')
                    if cast == int:
                        try:
                            value = int(value)
                        except ValueError:
                            continue
                    elif cast == float:
                        try:
                            value = float(value)
                        except ValueError:
                            continue
                    entity[key] = value

            # Skip entries with no health and no furniture placement data
            if "health" not in entity and not any(
                k in entity for k in ["placeable_on_tables", "placeable_on_walls", "placeable_as_rug", "placeable_in_water"]
            ):
                continue

            drop_tables = _extract_drop_tables(lines)
            entity.update(drop_tables)

            entity_data[prefab_name] = entity

        except Exception as exc:
            print(f"  ⚠️  Error processing {filename}: {exc}")

    # --- Combat dungeon enemies from scene files ---
    combat_files = sorted(
        f for f in os.listdir(_SCENES_DIR) if re.match(r"CombatDungeon(\d+)\.unity", f)
    )

    for filename in combat_files:
        filepath = os.path.join(_SCENES_DIR, filename)
        print(f"  🔍 Parsing {filename}...")
        lines   = file_utils.read_file_lines(filepath)
        content = "\n".join(lines)

        floor_match  = re.search(r'CombatDungeon(\d+)', filename)
        floor_number = floor_match.group(1) if floor_match else "?"

        enemy_blocks = re.findall(r'enemySpawnerName:.*?(?=\n\S)', content, flags=re.DOTALL)

        for block in enemy_blocks:
            name_match = re.search(r'enemySpawnerName:\s*([^\n]+)', block)
            if not name_match:
                continue

            name   = name_match.group(1).strip()
            key    = f"{name}_CombatDungeon{floor_number}"
            entity = {
                "enemy_name": name,
                "location":   f"Combat Dungeon Floor {floor_number}",
            }

            for field, cast in [
                ("_health",              float),
                ("_powerLevel",          int),
                ("defense",              int),
                ("_hasAttack",           int),
                ("_attacking",           int),
                ("_attackStateDuration", float),
                ("timeBetweenAttacks",   float),
                ("reflectDamage",        int),
            ]:
                match = re.search(rf"{field}:\s*([^\n]+)", block)
                if match:
                    try:
                        entity[field.lstrip("_")] = cast(match.group(1).strip())
                    except Exception:
                        continue

            entity_data[key] = entity

    json_utils.write_json(entity_data, _CACHE_FILE)
    print(f"✅ {len(entity_data)} entities written to {_CACHE_FILE}")


if __name__ == "__main__":
    run()
