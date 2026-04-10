"""
Compares the old camelCase items_data.json (pre-refactor) against the
new snake_case items_data.json (post-refactor) to confirm data values
are equivalent.

Ignores:
  - Key name changes (camelCase → snake_case)
  - New fields added by the builder (classification, etc.)
  - Fields that only existed in the old format

Run:
    python analysis/compare_builder_output.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config.constants as constants

OLD_JSON = os.path.join(constants.PREVIOUS_OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
NEW_JSON = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")

# ---------------------------------------------------------------------------
# Key mapping: old camelCase → new snake_case
# Only fields that existed in the old format are checked.
# ---------------------------------------------------------------------------

KEY_MAP = {
    "assetName":        "asset_name",
    "Name":             "name",
    "GUID":             "guid",
    "ID":               "item_id",
    "iconGUID":         "icon_guid",
    "description":      "description",
    "useDescription":   "use_description",
    "helpDescription":  "help_description",
    "stackSize":        "stack_size",
    "canSell":          "can_sell",
    "sellPrice":        "sell_price",
    "orbsSellPrice":    "orbs_sell_price",
    "ticketSellPrice":  "ticket_sell_price",
    "rarity":           "rarity",
    "hearts":           "hearts",
    "decorationType":   "decoration_type",
    "isDLCItem":        "is_dlc",
    "isForageable":     "is_forageable",
    "isGem":            "is_gem",
    "isAnimalProduct":  "is_animal_product",
    "isMeal":           "is_meal",
    "isFruit":          "is_fruit",
    "isArtisanryItem":  "is_artisanry",
    "isPotion":         "is_potion",
    "hasSetSeason":     "has_set_season",
    "setSeason":        "set_season",
    "exp":              "exp",
    "health":           "health",
    "mana":             "mana",
    "armorSet":         "armor_set",
    "requiredLevel":    "required_level",
    "seasons":          "seasons",
    "pickaxeable":      "pickaxeable",
    "axeable":          "axeable",
    "placeableOnTables":"placeable_on_tables",
    "placeableOnWalls": "placeable_on_walls",
    "placeableAsRug":   "placeable_as_rug",
    "placeableInWater": "placeable_in_water",
    "canRotate":        "can_rotate",
}

# Nested list field mappings: (old_key, new_key, inner_key_map)
NESTED_MAP = [
    ("stats",      "stats",      {"statType": "stat_type", "value": "value"}),
    ("maxStats",   "max_stats",  {"statType": "stat_type", "value": "value"}),
    ("foodStat",   "food_stat",  {"increase": "increase",  "stat":  "stat"}),
    ("statBuff",   "stat_buff",  {"statType": "stat_type", "value": "value", "duration": "duration"}),
    ("cropStages", "crop_stages",{"daysToGrow": "days_to_grow", "guid": "guid"}),
]

# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _norm(value):
    """Normalise a value for comparison — bools from 0/1 ints, None as None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        # Old format stored booleans as 0/1 ints; new format uses True/False.
        # Only convert if the new side is also bool — handled at comparison site.
        return value
    return value


def _bools_match(old_val, new_val) -> bool:
    """Compare a value that may be 0/1 in old format and True/False in new."""
    if isinstance(new_val, bool):
        return bool(old_val) == new_val
    return old_val == new_val


def _nested_match(old_list, new_list, inner_key_map) -> list[str]:
    """Compare two lists of dicts using an inner key map. Returns mismatch messages."""
    issues = []
    old_list = old_list or []
    new_list = new_list or []
    if len(old_list) != len(new_list):
        issues.append(f"  length mismatch: old={len(old_list)} new={len(new_list)}")
        return issues
    for i, (old_entry, new_entry) in enumerate(zip(old_list, new_list)):
        for old_k, new_k in inner_key_map.items():
            ov = old_entry.get(old_k)
            nv = new_entry.get(new_k)
            if not _bools_match(ov, nv) and ov != nv:
                issues.append(f"  [{i}] {old_k}: old={ov!r} new={nv!r}")
    return issues


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------

def run():
    print(f"Old: {OLD_JSON}")
    print(f"New: {NEW_JSON}\n")

    with open(OLD_JSON, encoding="utf-8") as f:
        old_data = json.load(f)
    with open(NEW_JSON, encoding="utf-8") as f:
        new_data = json.load(f)

    old_keys = {k.lower(): k for k in old_data}
    new_keys = {k.lower(): k for k in new_data}

    only_in_old = set(old_keys) - set(new_keys)
    only_in_new = set(new_keys) - set(old_keys)

    if only_in_old:
        print(f"⚠️  Items only in OLD ({len(only_in_old)}): {sorted(only_in_old)[:10]}{'...' if len(only_in_old) > 10 else ''}")
    if only_in_new:
        print(f"⚠️  Items only in NEW ({len(only_in_new)}): {sorted(only_in_new)[:10]}{'...' if len(only_in_new) > 10 else ''}")

    mismatches = []
    matched = 0

    for lower_name in sorted(old_keys):
        if lower_name not in new_keys:
            continue

        old_item = old_data[old_keys[lower_name]]
        new_item = new_data[new_keys[lower_name]]
        item_issues = []

        # Flat field comparison
        for old_k, new_k in KEY_MAP.items():
            ov = old_item.get(old_k)
            nv = new_item.get(new_k)
            if not _bools_match(ov, nv) and ov != nv:
                item_issues.append(f"  {old_k} → {new_k}: old={ov!r} new={nv!r}")

        # Nested list comparison
        for old_k, new_k, inner_map in NESTED_MAP:
            issues = _nested_match(old_item.get(old_k), new_item.get(new_k), inner_map)
            for issue in issues:
                item_issues.append(f"  {old_k}: {issue}")

        if item_issues:
            mismatches.append((old_keys[lower_name], item_issues))
        else:
            matched += 1

    print(f"✅ Matching items: {matched}")
    if mismatches:
        print(f"❌ Items with data mismatches: {len(mismatches)}\n")
        for name, issues in mismatches[:20]:
            print(f"  {name}:")
            for issue in issues:
                print(f"    {issue}")
        if len(mismatches) > 20:
            print(f"  ... and {len(mismatches) - 20} more")
    else:
        print("✅ All shared fields match between old and new formats.")


if __name__ == "__main__":
    run()
