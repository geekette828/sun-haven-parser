"""
Fish spawn chance exporter — Layer 3 of the pipeline.

Reads fish_spawner_data.json and items_data.json (via _load_cache) and writes
Fish_Spawn_Chance.txt with {{Fish locations}} wikitext.

Usage:
    python exporters/fish_spawn_chance.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from builders.item_builder import _load_cache
from utils import json_utils, file_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_FISH_DATA   = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "fish_spawner_data.json")
_OUTPUT_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Fish_Spawn_Chance.txt")

# ---------------------------------------------------------------------------
# Scene → location display name mapping
# ---------------------------------------------------------------------------

_SCENE_LOCATION_MAPPING = {
    # Sun Haven
    "2playerfarm":                   "Farm",
    "BeachTransition":               "Farm",
    "MiyeonEntrance":                "Farm",
    "Town10":                        "Farm",
    "WheatFieldRevamp":              "Farm",
    "BeachHuntingGround1":           "Beach",
    "BeachRevamp":                   "Beach",
    "SunHavenSewer":                 "Sun Haven Sewer",
    "Town10NorthEntrance1A":         "Sandstone Quarry",
    "SmallBridge":                   "Eastern Wilderness",
    "Wilderness2":                   "Eastern Wilderness",
    "Wilderness3Revamp":             "Eastern Wilderness",
    "WildernessTaxi":                "Eastern Wilderness",
    "Wishingwellpath1":              "Eastern Wilderness",
    "Elvenforesttransition":         "Western Forest",
    "ForestC":                       "Western Forest",
    # The Great City
    "GCDockDistrict":                "Dock District",
    "GCMainDistrictEasternMarket":   "Main Plaza",
    # Nel'Vari
    "ElvenForest1":                  "Elven Forest",
    "ElvenForest2":                  "Elven Forest",
    "Elvenforest2A":                 "Elven Forest",
    "GrandTreeEntrance1":            "Nel'Vari Village",
    "NelVari6":                      "Nel'Vari Village",
    "NelvariFarm":                   "Nel'Vari Farm",
    "Vaanexterior":                  "Nel'Vari Village",
    # Withergate
    "WithergateRooftopFarm":         "Withergate Rooftop Farm",
    "WithergateCarnival6":           "City of Withergate",
    "WithergateOutskirts":           "City of Withergate",
    "WithergateForest1":             "Withergate Forest",
    "WithergateGloriteCaveEntrance": "Withergate Forest",
    "Sewer":                         "Withergate Sewer",
    # Special
    "AltarFishingReward":            "Midnight Isle",
}

# ---------------------------------------------------------------------------
# Season mapping
# ---------------------------------------------------------------------------

_SEASON_NAMES = {0: "Spring", 1: "Summer", 2: "Fall", 3: "Winter"}

# ---------------------------------------------------------------------------
# Probability helpers
# ---------------------------------------------------------------------------

def _lerp(a: float, b: float, t: float) -> float:
    return (1 - t) * a + t * b


def _adjusted_odds(rarity: str, level: int) -> float:
    t = level / 120.0
    if rarity == "Rare":
        return _lerp(0.8, 3.35, t)
    if rarity == "Epic":
        return _lerp(0.675, 4.25, t)
    if rarity == "Legendary":
        return _lerp(0.55, 5.0, t)
    return 1.0


def _compute_percentages(
    drops: list,
    items_by_name: dict,
    level: int,
    familiar_waters_value: float = 0.0,
    advanced_fish_mapping_value: float = 0.0,
) -> dict[str, float]:
    """Compute spawn percentages for a given pool of drops at a given level."""
    num = 0.0
    num2 = 0.0
    if familiar_waters_value:
        num += 0.05 * familiar_waters_value
    if advanced_fish_mapping_value:
        num2 += 0.1 * advanced_fish_mapping_value

    rows: list[tuple[str, float]] = []

    for drop in drops:
        fish_name = (drop.get("name") or "").strip()
        chance = float(drop.get("drop_chance") or 0)

        if not fish_name or chance <= 0:
            continue

        item = items_by_name.get(fish_name)
        if not item:
            continue

        rarity_value = int(getattr(item, "rarity", 0))
        rarity_str = constants.RARITY_TYPE_MAPPING.get(rarity_value, "Common")

        rarity_adjustment = 1.0
        if rarity_str == "Epic":
            rarity_adjustment += num
        elif rarity_str == "Legendary":
            rarity_adjustment += num + num2

        adjusted = _adjusted_odds(rarity_str, level)
        effective_weight = chance * rarity_adjustment * adjusted
        rows.append((fish_name, effective_weight))

    total = sum(w for _, w in rows)
    if total <= 0:
        return {}
    return {name: (w / total) * 100.0 for name, w in rows}


def _get_fish_season(fish_name: str, items_by_name: dict) -> str:
    """Return 'Any', 'Spring', 'Summer', 'Fall', or 'Winter' for a fish."""
    item = items_by_name.get(fish_name)
    if not item:
        return "Any"
    has_set = int(getattr(item, "has_set_season", 0) or 0)
    if not has_set:
        return "Any"
    season_idx = getattr(item, "set_season", None)
    try:
        return _SEASON_NAMES.get(int(season_idx), "Any")
    except (TypeError, ValueError):
        return "Any"


def _compute_location_rows(
    scene_data: dict,
    items_by_name: dict,
    location_name: str,
) -> list[dict]:
    """Return all spawn rows for one scene/location, respecting seasonal pools."""
    all_drops = scene_data.get("fish_drops", [])
    has_seasonal = scene_data.get("has_seasonal_fish", False)

    rows: list[dict] = []

    if not has_seasonal:
        # Single pool — all fish are year-round
        min_p = _compute_percentages(all_drops, items_by_name, level=1)
        max_p = _compute_percentages(
            all_drops, items_by_name, level=70,
            familiar_waters_value=15, advanced_fish_mapping_value=30,
        )
        for fish_name in min_p:
            rows.append({
                "fish": fish_name, "location": location_name, "season": "Any",
                "min": round(min_p[fish_name], 2),
                "max": round(max_p.get(fish_name, 0.0), 2),
            })
    else:
        # Bucket drops by season
        year_round: list[dict] = []
        by_season: dict[int, list] = {0: [], 1: [], 2: [], 3: []}

        for drop in all_drops:
            fish_name = (drop.get("name") or "").strip()
            season = _get_fish_season(fish_name, items_by_name)
            if season == "Any":
                year_round.append(drop)
            else:
                idx = next(k for k, v in _SEASON_NAMES.items() if v == season)
                by_season[idx].append(drop)

        # Year-round fish — percentages calculated within year-round pool only
        if year_round:
            min_p = _compute_percentages(year_round, items_by_name, level=1)
            max_p = _compute_percentages(
                year_round, items_by_name, level=70,
                familiar_waters_value=15, advanced_fish_mapping_value=30,
            )
            for fish_name in min_p:
                rows.append({
                    "fish": fish_name, "location": location_name, "season": "Any",
                    "min": round(min_p[fish_name], 2),
                    "max": round(max_p.get(fish_name, 0.0), 2),
                })

        # Per-season rates for all fish — combined pool (year-round + that season).
        # Year-round fish get one entry per active season (rate diluted by seasonal fish).
        # Seasonal fish get their own season entry.
        # When both "Any" and a seasonal entry exist, the seasonal rate takes precedence.
        for season_idx, season_name in _SEASON_NAMES.items():
            season_drops = by_season.get(season_idx, [])
            if not season_drops:
                continue
            combined = year_round + season_drops
            min_p = _compute_percentages(combined, items_by_name, level=1)
            max_p = _compute_percentages(
                combined, items_by_name, level=70,
                familiar_waters_value=15, advanced_fish_mapping_value=30,
            )
            # Year-round fish: add their diluted per-season rate
            for drop in year_round:
                fish_name = (drop.get("name") or "").strip()
                if fish_name in min_p:
                    rows.append({
                        "fish": fish_name, "location": location_name, "season": season_name,
                        "min": round(min_p[fish_name], 2),
                        "max": round(max_p.get(fish_name, 0.0), 2),
                    })
            # Seasonal fish: their only entry
            for drop in season_drops:
                fish_name = (drop.get("name") or "").strip()
                rows.append({
                    "fish": fish_name, "location": location_name, "season": season_name,
                    "min": round(min_p.get(fish_name, 0.0), 2),
                    "max": round(max_p.get(fish_name, 0.0), 2),
                })

    return rows

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_OUTPUT_FILE))

    fish_spawner_data = json_utils.load_json(_FISH_DATA)

    items = _load_cache()
    items_by_name = {item.name: item for item in items.values()}

    fish_to_rows: dict[str, list[dict]] = {}

    for scene_name, location_name in _SCENE_LOCATION_MAPPING.items():
        scene_data = fish_spawner_data.get(scene_name)
        if not scene_data:
            continue

        for row in _compute_location_rows(scene_data, items_by_name, location_name):
            entry = {
                "location": row["location"],
                "season":   row["season"],
                "min":      row["min"],
                "max":      row["max"],
            }
            existing = fish_to_rows.setdefault(row["fish"], [])
            if entry not in existing:
                existing.append(entry)

    output_lines: list[str] = []
    for fish_name in sorted(fish_to_rows.keys(), key=lambda x: x.lower()):
        output_lines.append("{{Fish locations\n")
        output_lines.append(f"|name = {fish_name}\n")
        # Sort: within each location, put "Any" last so seasonal entries get
        # the low index numbers and the template parser finds them first.
        rows = sorted(
            fish_to_rows[fish_name],
            key=lambda r: (r["location"], r["season"] == "Any", r["season"]),
        )

        # Locations that have at least one seasonal entry — their "Any" row
        # will be commented out (still visible in wikitext, hidden from UI).
        locations_with_seasons = {
            r["location"] for r in rows if r["season"] != "Any"
        }

        active_rows  = [r for r in rows if not (r["season"] == "Any" and r["location"] in locations_with_seasons)]
        comment_rows = [r for r in rows if      r["season"] == "Any" and r["location"] in locations_with_seasons]

        for idx, row in enumerate(active_rows, start=1):
            output_lines.append(f"|{idx}_location = {row['location']}\n")
            output_lines.append(f"   |{idx}_season = {row['season']}\n")
            output_lines.append(f"   |{idx}_min = {row['min']}\n")
            output_lines.append(f"   |{idx}_max = {row['max']}\n")

        for row in comment_rows:
            idx = len(active_rows) + comment_rows.index(row) + 1
            output_lines.append(f"<!-- |{idx}_location = {row['location']}\n")
            output_lines.append(f"   |{idx}_season = {row['season']}\n")
            output_lines.append(f"   |{idx}_min = {row['min']}\n")
            output_lines.append(f"   |{idx}_max = {row['max']} -->\n")

        output_lines.append("}}\n\n")

    file_utils.write_lines(_OUTPUT_FILE, output_lines)
    print(f"✅ Fish spawn chances written to {_OUTPUT_FILE}")


if __name__ == "__main__":
    run()
