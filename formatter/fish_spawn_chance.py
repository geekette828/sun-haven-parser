import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import json_utils


INPUT_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "fish_spawner_data.json")
ITEMS_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
OUTPUT_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Fish_Spawn_Chance.txt")


SCENE_LOCATION_MAPPING = {
    "GCDockDistrict": "Dock District",
    "GCMainDistrictEasternMarket": "Main Plaza",
}


def lerp(a: float, b: float, t: float) -> float:
    return (1 - t) * a + t * b


def adjusted_odds_based_on_rarity_and_level(rarity: str, level: int) -> float:
    t = level / 120.0

    if rarity == "Rare":
        return lerp(0.8, 3.35, t)
    if rarity == "Epic":
        return lerp(0.675, 4.25, t)
    if rarity == "Legendary":
        return lerp(0.55, 5.0, t)

    return 1.0


def compute_percentages(
    scene_data: dict,
    items_data: dict,
    level: int,
    familiar_waters_value: float = 0.0,
    advanced_fish_mapping_value: float = 0.0,
) -> dict:
    drops = scene_data.get("fishDrops", [])

    num = 0.0
    num2 = 0.0
    if familiar_waters_value:
        num += 0.05 * familiar_waters_value
    if advanced_fish_mapping_value:
        num2 += 0.1 * advanced_fish_mapping_value

    rows = []

    for drop in drops:
        fish_name = (drop.get("name") or "").strip()
        chance = float(drop.get("dropChance") or 0)

        if not fish_name or chance <= 0:
            continue

        item = items_data.get(fish_name)
        if not item:
            continue

        rarity_value = int(item.get("rarity", 0))
        rarity_str = constants.RARITY_TYPE_MAPPING.get(rarity_value, "Common")

        rarity_adjustment = 1.0
        if rarity_str == "Epic":
            rarity_adjustment += num
        elif rarity_str == "Legendary":
            rarity_adjustment += num + num2

        adjusted_odds = adjusted_odds_based_on_rarity_and_level(rarity_str, level)

        effective_weight = chance * rarity_adjustment * adjusted_odds
        rows.append((fish_name, effective_weight))

    total_probability = sum(w for _, w in rows)
    if total_probability <= 0:
        return {}

    return {fish_name: (w / total_probability) * 100.0 for fish_name, w in rows}


def main() -> None:
    fish_spawner_data = json_utils.load_json(INPUT_JSON_PATH)
    items_data = json_utils.load_json(ITEMS_JSON_PATH)

    fish_to_rows = {}

    for scene_name, location_name in SCENE_LOCATION_MAPPING.items():
        scene_data = fish_spawner_data.get(scene_name)
        if not scene_data:
            continue

        min_percents = compute_percentages(scene_data, items_data, level=1)
        max_percents = compute_percentages(
            scene_data,
            items_data,
            level=70,
            familiar_waters_value=15,
            advanced_fish_mapping_value=30,
        )

        for fish_name in set(min_percents.keys()) | set(max_percents.keys()):
            fish_to_rows.setdefault(fish_name, []).append({
                "location": location_name,
                "season": "Any",
                "min": round(min_percents.get(fish_name, 0.0), 2),
                "max": round(max_percents.get(fish_name, 0.0), 2),
            })

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for fish_name in sorted(fish_to_rows.keys(), key=lambda x: x.lower()):
            out.write("{{Fish locations\n")
            out.write(f"|name = {fish_name}\n")

            rows = sorted(fish_to_rows[fish_name], key=lambda r: (r["location"], r["season"]))
            for idx, row in enumerate(rows, start=1):
                out.write(f"|{idx}_location = {row['location']}\n")
                out.write(f"   |{idx}_season = {row['season']}\n")
                out.write(f"   |{idx}_min = {row['min']}\n")
                out.write(f"   |{idx}_max = {row['max']}\n")

            out.write("}}\n\n")


if __name__ == "__main__":
    main()
