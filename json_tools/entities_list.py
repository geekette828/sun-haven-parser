import os
import sys
import re
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils, json_utils

# Define paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "GameObject")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
output_file = "entities_data.json"
output_path = os.path.join(output_directory, output_file)

file_utils.ensure_dir_exists(output_directory)

def extract_drop_tables(lines):
    drop_tables = []
    current_table = []
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
            elif not line.startswith(" "):  # break if we hit non-indented line
                break
            if "id:" in stripped:
                try:
                    drop_id = int(stripped.split("id:")[1].strip())
                except:
                    drop_id = None
            elif "dropChance:" in stripped:
                try:
                    drop_chance = float(stripped.split("dropChance:")[1].strip())
                except:
                    drop_chance = None
            elif "dropAmount:" in stripped:
                match = re.search(r"x:\s*(\d+),\s*y:\s*(\d+)", stripped)
                if match and drop_id is not None and drop_chance is not None:
                    drop_amount = int(match.group(1))
                    current_table.append({
                        "id": drop_id,
                        "drop chance": drop_chance,
                        "drop amount": drop_amount
                    })
                    drop_id = None
                    drop_chance = None

    if current_table:
        drop_tables.append(current_table)
    return {f"dropTable{i+1}": table for i, table in enumerate(drop_tables)}

# Main extraction
entity_data = {}

file_list = [f for f in os.listdir(input_directory) if f.endswith(".prefab")]
total_files = len(file_list)

for i, filename in enumerate(file_list, start=1):
    if total_files > 0 and i % max(1, total_files // 5) == 0:
        print(f"  🔄 {i}/{total_files} files complete — ({int((i / total_files) * 100)}%)")

    prefab_path = os.path.join(input_directory, filename)
    meta_path = prefab_path + ".meta"
    prefab_name = os.path.splitext(filename)[0]

    try:
        lines = file_utils.read_file_lines(prefab_path)
        content = "\n".join(lines)

        guid = "UNKNOWN"
        if os.path.exists(meta_path):
            meta_lines = file_utils.read_file_lines(meta_path)
            for line in meta_lines:
                if "guid:" in line:
                    guid = line.split("guid:")[1].strip()
                    break

        entity = {
            "prefab": prefab_name
        }

        enemy_name = re.search(r'(?<!key)enemyName:\s*"?([^\r\n":]+(?: [^\r\n":]+)*)"?', content)
        if enemy_name:
            name = enemy_name.group(1).strip()
            if name != "keyEnemyName":
                entity["enemy name"] = name

        entity["guid"] = guid

        for key, field, cast in [
            # Core stats
            ("health", "_health", float),
            ("exp", "_experience", float),
            ("level", "_powerLevel", int),
            ("defense", "defense", int),

            # Combat-related
            ("hasAttack", "_hasAttack", int),
            ("damageRange", "_damageRange", str),
            ("damageType", "_damageType", str),
            ("hitType", "_hitType", str),
            ("hitCooldown", "_hitCooldown", float),
            ("knockBack", "_knockBack", float),

            # NPC-specific
            ("npcName", "_npcName", str),
            ("romanceable", "_romanceable", int),
            ("shopKeeper", "_shopKeeper", int),
            ("quests", "_quests", str),
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

        # Determine if the furniture can rotate
        if any(entity.get(dir_key) for dir_key in ["southDecoration", "eastDecoration", "northDecoration", "westDecoration"]):
            entity["canRotate"] = True
        else:
            entity["canRotate"] = False

        if "health" not in entity and not any(k in entity for k in [
            "placeableOnTables", "placeableOnWalls", "placeableAsRug", "placeableInWater"
        ]):
            continue  # skip entries that don't have health or furniture data

        drop_tables = extract_drop_tables(lines)
        entity.update(drop_tables)

        entity_data[prefab_name] = entity

    except Exception as e:
        print(f"Error processing {filename}: {e}")

# 
json_utils.write_json(entity_data, output_path)
print(f"✅ Entity data written to {output_path}")