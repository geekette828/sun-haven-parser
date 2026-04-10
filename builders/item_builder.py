"""
Item builder — Layer 1 of the pipeline.

Responsibilities:
  - Parse raw MonoBehaviour (.asset) and GameObject (.prefab) files
  - Produce ItemData objects (fully typed, classified)
  - Write a JSON cache for warm reloads and manual reference
  - Load from JSON cache when source files have not changed

Public API:
  build_all_items()  →  dict[str, ItemData]   (keyed by lowercase display name)
  load_item(name)    →  ItemData | None
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
import sys
from math import floor
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from builders.item_data import (
    CropStage,
    FoodStatEntry,
    ItemClassification,
    ItemData,
    StatBuffEntry,
    StatEntry,
)
from config import skip_items
from mappings.item_classification import classify_item as _classify_raw
from utils import file_utils, json_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_MONOBEHAVIOUR_DIR = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
_GAMEDATA_DIR = os.path.join(constants.INPUT_DIRECTORY, "GameObject")
_DISPLAY_NAMES_FILE = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")

_CACHE_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
_DEBUG_LOG = os.path.join(constants.DEBUG_DIRECTORY, "json", "item_builder_debug.txt")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("item_builder")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    file_utils.ensure_dir_exists(os.path.dirname(_DEBUG_LOG))
    handler = logging.FileHandler(_DEBUG_LOG, mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
    return logger

_log = _setup_logger()

# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _is_cache_valid() -> bool:
    """Return True if the JSON cache is newer than the source MonoBehaviour directory."""
    if not os.path.exists(_CACHE_FILE):
        return False
    if not os.path.isdir(_MONOBEHAVIOUR_DIR):
        return False
    cache_mtime = os.path.getmtime(_CACHE_FILE)
    source_mtime = max(
        os.path.getmtime(os.path.join(_MONOBEHAVIOUR_DIR, f))
        for f in os.listdir(_MONOBEHAVIOUR_DIR)
        if f.endswith(".asset")
    )
    return cache_mtime >= source_mtime


def _save_cache(items: dict[str, ItemData]) -> None:
    """Serialize all ItemData objects to JSON and write the cache file."""
    file_utils.ensure_dir_exists(os.path.dirname(_CACHE_FILE))
    serializable = {name: dataclasses.asdict(item) for name, item in items.items()}
    json_utils.write_json(serializable, _CACHE_FILE, indent=4)
    _log.info("Cache written: %d items → %s", len(items), _CACHE_FILE)


def _load_cache() -> dict[str, ItemData]:
    """Deserialize the JSON cache back into ItemData objects."""
    raw = json_utils.load_json(_CACHE_FILE)
    if not raw:
        return {}
    result = {}
    for name, d in raw.items():
        try:
            result[name] = _item_data_from_dict(d)
        except Exception as exc:
            _log.warning("Failed to deserialize cached item '%s': %s", name, exc)
    _log.info("Loaded %d items from cache.", len(result))
    return result

# ---------------------------------------------------------------------------
# Deserialization (JSON dict → ItemData)
# ---------------------------------------------------------------------------

def _item_data_from_dict(d: dict) -> ItemData:
    """Reconstruct an ItemData from a plain dict (as stored in the JSON cache)."""

    def _stat_entry(x: dict) -> StatEntry:
        return StatEntry(stat_type=x["stat_type"], value=x["value"])

    def _food_stat_entry(x: dict) -> FoodStatEntry:
        return FoodStatEntry(increase=x["increase"], stat=x["stat"])

    def _stat_buff_entry(x: dict) -> StatBuffEntry:
        return StatBuffEntry(
            stat_type=x["stat_type"], value=x["value"], duration=x["duration"]
        )

    def _crop_stage(x: dict) -> CropStage:
        return CropStage(days_to_grow=x["days_to_grow"], guid=x.get("guid"))

    def _classification(x: Optional[dict]) -> Optional[ItemClassification]:
        if not x:
            return None
        return ItemClassification(
            item_type=x["item_type"],
            subtype=x["subtype"],
            category=x["category"],
        )

    return ItemData(
        asset_name=d["asset_name"],
        name=d["name"],
        guid=d["guid"],
        item_id=d["item_id"],
        icon_guid=d.get("icon_guid"),
        description=d.get("description", ""),
        use_description=d.get("use_description", ""),
        help_description=d.get("help_description", ""),
        stack_size=d.get("stack_size"),
        can_sell=d.get("can_sell", False),
        sell_price=d.get("sell_price", 0),
        orbs_sell_price=d.get("orbs_sell_price", 0),
        ticket_sell_price=d.get("ticket_sell_price", 0),
        rarity=d.get("rarity"),
        hearts=d.get("hearts"),
        health=d.get("health"),
        mana=d.get("mana"),
        exp=d.get("exp"),
        required_level=d.get("required_level"),
        armor_set=d.get("armor_set"),
        decoration_type=d.get("decoration_type"),
        is_dlc=d.get("is_dlc", False),
        is_forageable=d.get("is_forageable", False),
        is_gem=d.get("is_gem", False),
        is_animal_product=d.get("is_animal_product", False),
        is_meal=d.get("is_meal", False),
        is_fruit=d.get("is_fruit", False),
        is_artisanry=d.get("is_artisanry", False),
        is_potion=d.get("is_potion", False),
        has_set_season=d.get("has_set_season"),
        set_season=d.get("set_season"),
        seasons=d.get("seasons"),
        stats=[_stat_entry(x) for x in d.get("stats", [])],
        max_stats=[_stat_entry(x) for x in d.get("max_stats", [])],
        food_stat=[_food_stat_entry(x) for x in d.get("food_stat", [])],
        stat_buff=[_stat_buff_entry(x) for x in d.get("stat_buff", [])],
        crop_stages=[_crop_stage(x) for x in d.get("crop_stages", [])],
        placeable_on_tables=d.get("placeable_on_tables", False),
        placeable_on_walls=d.get("placeable_on_walls", False),
        placeable_as_rug=d.get("placeable_as_rug", False),
        placeable_in_water=d.get("placeable_in_water", False),
        pickaxeable=d.get("pickaxeable", False),
        axeable=d.get("axeable", False),
        can_rotate=d.get("can_rotate", False),
        classification=_classification(d.get("classification")),
    )

# ---------------------------------------------------------------------------
# Raw file parsers (private)
# ---------------------------------------------------------------------------

def _parse_number(val: str) -> int | float:
    return float(val) if "." in val else int(val)


def _extract_guid(meta_file: str) -> Optional[str]:
    try:
        content = "\n".join(file_utils.read_file_lines(meta_file))
    except Exception as exc:
        _log.warning("Error reading %s: %s", meta_file, exc)
        return None
    match = re.search(r"guid:\s*([a-f0-9]+)", content)
    return match.group(1) if match else None


def _extract_icon_guid(asset_file: str) -> Optional[str]:
    try:
        lines = file_utils.read_file_lines(asset_file)
    except Exception as exc:
        _log.warning("Error reading %s: %s", asset_file, exc)
        return None
    for line in lines:
        match = re.match(r"icon:\s*\{fileID:\s*\d+,\s*guid:\s*([\da-f]+),", line.strip())
        if match:
            return match.group(1)
    return None


def _extract_item_info(asset_file: str) -> tuple[Optional[int], Optional[str]]:
    basename = os.path.basename(asset_file)
    match = re.match(r"(\d+)\s+-\s+(.+)\.asset", basename)
    if match:
        return int(match.group(1)), match.group(2)
    return None, None


def _extract_key_display_name(asset_file: str) -> Optional[str]:
    try:
        for line in file_utils.read_file_lines(asset_file):
            if "keyDisplayName:" in line:
                return line.split("keyDisplayName:")[1].strip()
    except Exception as exc:
        _log.warning("Failed to extract keyDisplayName from %s: %s", asset_file, exc)
    return None


def _should_exclude_item(item_name: str) -> bool:
    name = item_name.lower()
    if name in (p.lower() for p in skip_items.SKIP_ITEMS):
        return True
    for pattern in skip_items.SKIP_PATTERNS:
        cleaned = pattern.strip("*").lower()
        if cleaned in name:
            return True
    return False


def _get_display_names(prefab_file: str) -> dict[str, str]:
    display_names: dict[str, str] = {}
    try:
        lines = file_utils.read_file_lines(prefab_file)
        current_term = None
        capturing_language = False
        for line in lines:
            line = line.strip()
            if line.startswith("- Term:"):
                current_term = line.split(":", 1)[1].strip()
                capturing_language = False
            elif line.startswith("Languages:") and current_term:
                capturing_language = True
            elif capturing_language and line.startswith("- "):
                display_names[current_term] = line[2:].strip()
                capturing_language = False
                current_term = None
    except Exception as exc:
        _log.warning("Error reading display names: %s", exc)
    return display_names


def _extract_stat_buff(lines: list[str]) -> list[StatBuffEntry]:
    capturing = False
    capturing_stats = False
    duration: Optional[float] = None
    current_stat: Optional[StatBuffEntry] = None
    entries: list[StatBuffEntry] = []

    for line in lines:
        line = line.strip()
        if line.startswith("statBuff:"):
            capturing = True
            continue
        if capturing:
            if line.startswith("stats:"):
                capturing_stats = True
                continue
            if match := re.match(r"duration:\s*([\d.]+)", line):
                duration = _parse_number(match.group(1))
                for e in entries:
                    if e.duration == 0:
                        entries[entries.index(e)] = StatBuffEntry(e.stat_type, e.value, int(duration))
            if capturing_stats:
                if match := re.match(r"-\s*statType:\s*(\d+)", line):
                    current_stat = StatBuffEntry(
                        stat_type=int(match.group(1)),
                        value=0.0,
                        duration=int(duration) if duration is not None else 0,
                    )
                    entries.append(current_stat)
                elif match := re.match(r"value:\s*([\d.]+)", line):
                    if entries:
                        last = entries[-1]
                        entries[-1] = StatBuffEntry(last.stat_type, _parse_number(match.group(1)), last.duration)
                elif re.match(r"^\S", line):
                    capturing_stats = False
                    capturing = False
            elif re.match(r"^\S", line):
                capturing = False

    return entries


def _extract_attributes(asset_file: str) -> dict:
    """Parse a raw .asset file and return a flat dict of all extracted fields."""
    attrs: dict = {
        "id": None,
        "description": None,
        "use_description": None,
        "help_description": None,
        "stack_size": None,
        "can_sell": False,
        "sell_price": None,
        "orbs_sell_price": None,
        "ticket_sell_price": None,
        "rarity": None,
        "hearts": None,
        "decoration_type": None,
        "is_dlc": False,
        "is_forageable": False,
        "is_gem": False,
        "is_animal_product": False,
        "is_meal": False,
        "is_fruit": False,
        "is_artisanry": False,
        "is_potion": False,
        "has_set_season": None,
        "set_season": None,
        "exp": None,
        "health": None,
        "mana": None,
        "armor_set": None,
        "required_level": None,
        "stats": [],
        "max_stats": [],
        "food_stat": [],
        "stat_buff": [],
        "crop_stages": [],
        "seasons": None,
        "icon_guid": None,
    }

    boolean_fields = {
        "isDLCItem": "is_dlc",
        "isForageable": "is_forageable",
        "isGem": "is_gem",
        "isAnimalProduct": "is_animal_product",
        "isMeal": "is_meal",
        "isFruit": "is_fruit",
        "isArtisanryItem": "is_artisanry",
        "isPotion": "is_potion",
        "canSell": "can_sell",
    }

    numeric_fields = {
        "health": "health",
        "mana": "mana",
        "requiredLevel": "required_level",
        "stackSize": "stack_size",
        "sellPrice": "sell_price",
        "orbsSellPrice": "orbs_sell_price",
        "ticketSellPrice": "ticket_sell_price",
        "rarity": "rarity",
        "hearts": "hearts",
        "decorationType": "decoration_type",
        "hasSetSeason": "has_set_season",
        "setSeason": "set_season",
        "armorSet": "armor_set",
        "exp": "exp",
    }

    # Pre-compile combined patterns for performance
    _NUMERIC_PATTERN = re.compile(
        r"^(health|mana|requiredLevel|stackSize|sellPrice|orbsSellPrice|ticketSellPrice"
        r"|rarity|hearts|decorationType|hasSetSeason|setSeason|armorSet|exp):\s*([\d.]+)"
    )
    _BOOL_PATTERN = re.compile(
        r"^(isDLCItem|isForageable|isGem|isAnimalProduct|isMeal|isFruit|isArtisanryItem|isPotion|canSell):\s*(\d+)"
    )

    try:
        lines = file_utils.read_file_lines(asset_file)
        capturing_description = False
        capturing_stats = False
        capturing_max_stats = False
        capturing_food_stat = False
        capturing_seasons = False
        capturing_crop_stages = False
        description_lines: list[str] = []
        seasons_list: list[str] = []
        crop_stages: list[dict] = []

        for line in lines:
            line = line.strip()

            # Numeric fields — single combined regex
            if match := _NUMERIC_PATTERN.match(line):
                raw_key, value = match.group(1), match.group(2)
                snake_key = numeric_fields[raw_key]
                attrs[snake_key] = _parse_number(value)
                continue

            # Boolean fields + canSell — single combined regex
            if match := _BOOL_PATTERN.match(line):
                raw_key, value = match.group(1), match.group(2)
                snake_key = boolean_fields.get(raw_key, "can_sell")
                attrs[snake_key] = int(value) == 1
                continue

            # useDescription / helpDescription
            if match := re.match(r"useDescription:\s*(.+)", line):
                attrs["use_description"] = match.group(1).strip()
            if match := re.match(r"helpDescription:\s*(.+)", line):
                attrs["help_description"] = match.group(1).strip()

            # description (may be multi-line)
            if line.startswith("description:"):
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    attrs["description"] = parts[1].strip()
                else:
                    capturing_description = True
                continue
            if capturing_description:
                if line.startswith("-") or ":" in line:
                    capturing_description = False
                else:
                    description_lines.append(line)
                    continue

            # stats
            if line.startswith("stats:") and not capturing_stats:
                capturing_stats = True
                continue
            if capturing_stats:
                if match := re.match(r"-\s*statType:\s*(\d+)", line):
                    attrs["stats"].append({"stat_type": int(match.group(1)), "value": None})
                elif match := re.match(r"value:\s*([\d.]+)", line):
                    if attrs["stats"]:
                        attrs["stats"][-1]["value"] = _parse_number(match.group(1))
                elif re.match(r"^\S", line):
                    capturing_stats = False

            # maxStats
            if line.startswith("maxStats:"):
                capturing_max_stats = True
                continue
            if capturing_max_stats:
                if match := re.match(r"-\s*statType:\s*(\d+)", line):
                    attrs["max_stats"].append({"stat_type": int(match.group(1)), "value": None})
                elif match := re.match(r"value:\s*([\d.]+)", line):
                    if attrs["max_stats"]:
                        attrs["max_stats"][-1]["value"] = _parse_number(match.group(1))
                elif re.match(r"^\S", line):
                    capturing_max_stats = False

            # foodStat
            if line.startswith("foodStat:"):
                capturing_food_stat = True
                continue
            if capturing_food_stat:
                if match := re.match(r"increase:\s*([\d.]+)", line):
                    attrs["food_stat"].append({"increase": _parse_number(match.group(1)), "stat": None})
                elif match := re.match(r"stat:\s*(\d+)", line):
                    if attrs["food_stat"]:
                        attrs["food_stat"][-1]["stat"] = int(match.group(1))
                elif re.match(r"^\S", line):
                    capturing_food_stat = False

            # cropStages
            if re.match(r"^\s*cropStages:\s*$", line):
                capturing_crop_stages = True
                crop_stages = []
                continue
            if capturing_crop_stages:
                if match := re.match(r"^\s*-\s*daysToGrow:\s*([\d.]+)", line):
                    crop_stages.append({"days_to_grow": _parse_number(match.group(1)), "guid": None})
                elif match := re.match(r"sprite:.*guid:\s*([\da-f]+)", line):
                    if crop_stages:
                        crop_stages[-1]["guid"] = match.group(1)
                elif re.match(r"^\S", line):
                    capturing_crop_stages = False

            # seasons
            if re.match(r"^\s*seasons:\s*$", line):
                capturing_seasons = True
                seasons_list = []
                continue
            if capturing_seasons:
                if match := re.match(r"^\s*-\s*(\d+)", line):
                    seasons_list.append(match.group(1))
                elif re.match(r"^\s*\S", line):
                    capturing_seasons = False

        if description_lines:
            attrs["description"] = " ".join(description_lines).strip()
        if seasons_list:
            attrs["seasons"] = "; ".join(seasons_list)
        if crop_stages:
            attrs["crop_stages"] = crop_stages

    except Exception as exc:
        _log.error("Error parsing %s: %s", asset_file, exc)

    return attrs


def _extract_prefab_attributes(prefab_file: str) -> dict:
    """Parse a .prefab file for placement and rotation flags."""
    data = {}
    rotate_count = 0
    rotate_keys = ["southDecoration", "eastDecoration", "northDecoration", "westDecoration"]

    try:
        for line in file_utils.read_file_lines(prefab_file):
            line = line.strip()
            if match := re.match(
                r"(pickaxeable|axeable|placeableOnTables|placeableOnWalls|placeableAsRug|placeableInWater):\s*(\d)",
                line,
            ):
                key, val = match.groups()
                snake = re.sub(r"([A-Z])", r"_\1", key).lower().lstrip("_")
                data[snake] = int(val) == 1
            if any(k in line for k in rotate_keys):
                rotate_count += 1
    except Exception as exc:
        _log.warning("Failed to read prefab %s: %s", prefab_file, exc)

    if rotate_count >= 2:
        data["can_rotate"] = True

    return data


# ---------------------------------------------------------------------------
# Classification bridge
# ---------------------------------------------------------------------------

def _classify(item_data: ItemData) -> ItemClassification:
    """
    Run the existing classify_item() logic against a temporary compatibility
    dict built from ItemData fields. Returns an ItemClassification.

    Note: classify_item() will be updated to accept ItemData directly in a
    future refactor once all callers are migrated.
    """
    compat = {
        "Name": item_data.name,
        "name": item_data.name,
        "description": item_data.description,
        "useDescription": item_data.use_description,
        "stats": [{"statType": s.stat_type, "value": s.value} for s in item_data.stats],
        "foodStat": [{"increase": f.increase, "stat": f.stat} for f in item_data.food_stat],
        "isForageable": int(item_data.is_forageable),
        "isPotion": int(item_data.is_potion),
        "isMeal": int(item_data.is_meal),
        "hasSetSeason": item_data.has_set_season,
    }
    item_type, subtype, category = _classify_raw(compat)
    return ItemClassification(item_type=item_type, subtype=subtype, category=category)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_all_items(force_rebuild: bool = False) -> dict[str, ItemData]:
    """
    Return all items as a dict keyed by lowercase display name.

    Loads from the JSON cache if it is up-to-date, otherwise re-parses
    the raw game files and writes a fresh cache.

    Args:
        force_rebuild: Skip the cache check and always re-parse raw files.
    """
    if not force_rebuild and _is_cache_valid():
        _log.info("Cache is valid — loading from %s", _CACHE_FILE)
        cached = _load_cache()
        if cached:
            return cached
        _log.warning("Cache load returned empty — falling back to full build.")

    _log.info("Building items from raw files in %s", _MONOBEHAVIOUR_DIR)
    print("Building item data from raw files...")

    prefab_files = [f for f in os.listdir(_GAMEDATA_DIR) if f.endswith(".prefab")]
    prefab_lookup = {
        os.path.splitext(f)[0]: os.path.join(_GAMEDATA_DIR, f) for f in prefab_files
    }
    display_names = _get_display_names(_DISPLAY_NAMES_FILE)

    asset_files = [f for f in os.listdir(_MONOBEHAVIOUR_DIR) if f.endswith(".asset")]
    total = len(asset_files)
    step = max(1, total // 5)
    all_items: dict[str, ItemData] = {}

    for idx, filename in enumerate(asset_files):
        if idx % step == 0:
            print(f"  🔄 {floor((idx / total) * 100)}% complete...")

        asset_path = os.path.join(_MONOBEHAVIOUR_DIR, filename)
        item_id, asset_name = _extract_item_info(asset_path)
        if not item_id or not asset_name:
            continue
        if _should_exclude_item(asset_name):
            continue

        key_display = _extract_key_display_name(asset_path)
        display_name = display_names.get(key_display, asset_name)

        attrs = _extract_attributes(asset_path)

        # Merge prefab attributes
        prefab_path = prefab_lookup.get(asset_name)
        if prefab_path:
            attrs.update(_extract_prefab_attributes(prefab_path))
        else:
            _log.debug("No prefab match for %s", asset_name)

        icon_guid = _extract_icon_guid(asset_path)
        stat_buff_entries = _extract_stat_buff(file_utils.read_file_lines(asset_path))

        # Filter stat_buff types out of raw stats to avoid duplication
        stat_buff_types = {e.stat_type for e in stat_buff_entries}
        filtered_stats = [
            s for s in attrs.get("stats", []) if s["stat_type"] not in stat_buff_types
        ]

        item = ItemData(
            asset_name=asset_name,
            name=display_name,
            guid=_extract_guid(asset_path + ".meta") or "",
            item_id=item_id,
            icon_guid=icon_guid,
            description=attrs.get("description") or "",
            use_description=attrs.get("use_description") or "",
            help_description=attrs.get("help_description") or "",
            stack_size=attrs.get("stack_size"),
            can_sell=attrs.get("can_sell", False),
            sell_price=attrs.get("sell_price") or 0,
            orbs_sell_price=attrs.get("orbs_sell_price") or 0,
            ticket_sell_price=attrs.get("ticket_sell_price") or 0,
            rarity=attrs.get("rarity"),
            hearts=attrs.get("hearts"),
            health=attrs.get("health"),
            mana=attrs.get("mana"),
            exp=attrs.get("exp"),
            required_level=attrs.get("required_level"),
            armor_set=attrs.get("armor_set"),
            decoration_type=attrs.get("decoration_type"),
            is_dlc=attrs.get("is_dlc", False),
            is_forageable=attrs.get("is_forageable", False),
            is_gem=attrs.get("is_gem", False),
            is_animal_product=attrs.get("is_animal_product", False),
            is_meal=attrs.get("is_meal", False),
            is_fruit=attrs.get("is_fruit", False),
            is_artisanry=attrs.get("is_artisanry", False),
            is_potion=attrs.get("is_potion", False),
            has_set_season=attrs.get("has_set_season"),
            set_season=attrs.get("set_season"),
            seasons=attrs.get("seasons"),
            stats=[StatEntry(s["stat_type"], s["value"] or 0.0) for s in filtered_stats],
            max_stats=[StatEntry(s["stat_type"], s["value"] or 0.0) for s in attrs.get("max_stats", [])],
            food_stat=[FoodStatEntry(f["increase"], f["stat"] or 0) for f in attrs.get("food_stat", [])],
            stat_buff=stat_buff_entries,
            crop_stages=[CropStage(c["days_to_grow"], c.get("guid")) for c in attrs.get("crop_stages", [])],
            placeable_on_tables=attrs.get("placeable_on_tables", False),
            placeable_on_walls=attrs.get("placeable_on_walls", False),
            placeable_as_rug=attrs.get("placeable_as_rug", False),
            placeable_in_water=attrs.get("placeable_in_water", False),
            pickaxeable=attrs.get("pickaxeable", False),
            axeable=attrs.get("axeable", False),
            can_rotate=attrs.get("can_rotate", False),
        )

        item.classification = _classify(item)
        key = display_name.lower()
        if key in all_items:
            existing = all_items[key]
            _log.warning(
                "Display name collision: '%s' (asset: %s, id: %s) already exists as (asset: %s, id: %s) — keeping first.",
                display_name, asset_name, item_id, existing.asset_name, existing.item_id,
            )
            print(f"  ⚠️  Collision: '{display_name}' ({asset_name}) duplicates ({existing.asset_name}) — keeping first.")
        else:
            all_items[key] = item

    _save_cache(all_items)
    print(f"✅ Built {len(all_items)} items.")
    _log.info("Build complete: %d items.", len(all_items))
    return all_items


def load_item(name: str, items: Optional[dict[str, ItemData]] = None) -> Optional[ItemData]:
    """
    Look up a single item by display name (case-insensitive).

    If a pre-loaded items dict is supplied it will be used directly,
    otherwise build_all_items() is called to load/build the full set.
    """
    if items is None:
        items = build_all_items()
    return items.get(name.strip().lower())


if __name__ == "__main__":
    # Run directly to rebuild the JSON cache from raw game files.
    # Example: python builders/item_builder.py
    # Add --force to bypass the cache check and always re-parse.
    import argparse
    parser = argparse.ArgumentParser(description="Rebuild the items JSON cache.")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if cache is valid.")
    args = parser.parse_args()
    build_all_items(force_rebuild=args.force)
    print(f"JSON cache written to: {_CACHE_FILE}")
