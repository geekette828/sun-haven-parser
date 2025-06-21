import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import json_utils, file_utils

# Define file paths
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "All Monster Drops.txt")
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "all_monster_drops_debug.txt")

entities_data = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "entities_data.json")
items_data = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")

# Load entity data
entities = json_utils.load_json(entities_data)
items = json_utils.load_json(items_data)

# Create a map from ID → Name
item_id_map = {
    item.get("ID"): item.get("Name")
    for item in items.values()
    if isinstance(item, dict) and "ID" in item and "Name" in item
}

# Initialize output lines
output_lines = []

# Process each entity
enemy_count = 0
for key, data in entities.items():
    enemy_name = data.get("enemy name")
    if enemy_name is None:
        continue

    enemy_count += 1

    lines = [f"### {enemy_name} ###", "{{Drops|sourceType = Monster", f" |droppedBy = {enemy_name}"]
    drop_index = 1

    for i in range(1, 5):
        table_name = f"dropTable{i}"
        drops = data.get(table_name, [])
        if not drops:
            continue

        total_weight = sum(entry.get("drop chance", 0.0) for entry in drops)

        for entry in drops:
            item_id = entry.get("id")
            drop_amount = entry.get("drop amount", 0)
            drop_chance = entry.get("drop chance", 0.0)

            if item_id == 0 or drop_amount == 0:
                # Still counts toward weight, but is skipped in output
                if item_id != 0:
                    file_utils.write_debug_log(
                        f"Skipping item with 0 quantity: Monster='{enemy_name}' Table='{table_name}' ID={item_id}",
                        debug_log_path
                    )
                continue

            raw_chance = (drop_chance / total_weight) * 100
            if raw_chance < 1:
                percent_chance = round(raw_chance, 2)
            else:
                percent_chance = round(raw_chance, 1)

            item_name = item_id_map.get(item_id, f"Item {item_id}")
            lines.append(f" |{drop_index}_item = {item_name:<20} |{drop_index}_quantity = {drop_amount:<10} |{drop_index}_chance = {percent_chance}")
            drop_index += 1

    lines.append("}}\n")
    output_lines.append("\n".join(lines))

# Write to output file
file_utils.write_lines(output_file_path, [line + "\n\n" for line in output_lines])

print(f"✅ Monster drops saved to {output_file_path}")