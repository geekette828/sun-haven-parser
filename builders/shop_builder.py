"""
Shop builder — Layer 1 of the pipeline.

Parses raw MonoBehaviour (.asset) files for merchant and general store
inventories, writing shop_data.json.

Usage:
    python builders/shop_builder.py
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

_MONOBEHAVIOUR_DIR = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
_CACHE_FILE        = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "shop_data.json")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Asset filenames that don't match the standard "merchant" / "generalstore"
# patterns but should still be included.
_EDGE_CASE_SHOP_NAMES = [
    "MythsAndMusesMerchat",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_guid(meta_path: str) -> str | None:
    if not os.path.exists(meta_path):
        return None
    with open(meta_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = re.match(r"guid:\s*(\S+)", line)
            if match:
                return match.group(1)
    return None


def _parse_shop_asset(asset_path: str) -> dict:
    base  = os.path.basename(asset_path).replace(".asset", "")
    clean = re.sub(r"(?:Merchant)?Table$", "", base, flags=re.IGNORECASE)

    shop_data: dict = {
        "file_name":     os.path.basename(asset_path),
        "shop_name":     clean.strip("_"),
        "guid":          _extract_guid(asset_path + ".meta"),
        "starting_items": [],
        "random_items":   [],
    }

    with open(asset_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    current_section: str | None = None
    item: dict = {}

    for line in lines:
        line = line.strip()

        if line.startswith("startingItems2:"):
            current_section = "starting"
            continue
        elif line.startswith("randomShopItems2:"):
            current_section = "random"
            continue
        elif re.match(r"-\s*id:", line):
            if "id" in item:
                if current_section == "starting":
                    shop_data["starting_items"].append(item)
                elif current_section == "random":
                    shop_data["random_items"].append(item)
            item = {}

        match = re.match(
            r"(?:-\s*)?(id|price|orbs|tickets|isLimited|qty|resetDay|chance|saleItem):\s*(.*)",
            line,
        )
        if match:
            key, value = match.groups()
            item[key] = int(value) if value.isdigit() else value
        elif "itemToUseAsCurrency:" in line:
            guid_match = re.search(r"guid:\s*([a-f0-9]+)", line)
            item["item_to_use_as_currency"] = guid_match.group(1) if guid_match else None

    # Flush last item
    if "id" in item:
        if current_section == "starting":
            shop_data["starting_items"].append(item)
        elif current_section == "random":
            shop_data["random_items"].append(item)

    return shop_data

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_CACHE_FILE))

    shop_list: list[dict] = []

    for file_name in os.listdir(_MONOBEHAVIOUR_DIR):
        if not file_name.endswith(".asset"):
            continue

        lower = file_name.lower()
        is_merchant    = "merchant" in lower and not file_name[0].isdigit()
        is_generalstore = "generalstore" in lower
        is_edge_case   = any(file_name.startswith(name) for name in _EDGE_CASE_SHOP_NAMES)

        if not (is_merchant or is_generalstore or is_edge_case):
            continue

        asset_path = os.path.join(_MONOBEHAVIOUR_DIR, file_name)
        shop_data  = _parse_shop_asset(asset_path)
        shop_list.append(shop_data)

    if shop_list:
        json_utils.write_json(shop_list, _CACHE_FILE, indent=4)
        print(f"✅ {len(shop_list)} shops written to {_CACHE_FILE}")
    else:
        print("⚠️  No valid shop data found. JSON file was not created.")


if __name__ == "__main__":
    run()
