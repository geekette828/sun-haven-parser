"""
All shops exporter — Layer 3 of the pipeline.

Reads shop_data.json (from shop_builder) plus any furniture/flooring/wallpaper
*Table.asset files, then writes shops.txt with {{Shop}} wikitext.

Item names are resolved from the item builder cache via _load_cache().

Usage:
    python exporters/all_shops.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from builders.item_builder import _load_cache
from utils import json_utils, file_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SHOP_DATA   = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "shop_data.json")
_OUTPUT_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "shops.txt")

# ---------------------------------------------------------------------------
# Table asset helpers (furniture / flooring / wallpaper)
# ---------------------------------------------------------------------------

_TABLE_PATTERNS = (
    "wallpapertable.asset",
    "largeitemstable.asset",
    "floordingtable.asset",
    "flooringtable.asset",
    "smallitemstable.asset",
)


def _find_table_assets(root_dir: str) -> list[str]:
    matches = []
    if not root_dir or not os.path.isdir(root_dir):
        return matches
    for root, _, files in os.walk(root_dir):
        for filename in files:
            if filename.lower().endswith(_TABLE_PATTERNS):
                matches.append(os.path.join(root, filename))
    return sorted(matches)


def _parse_guid_from_braces(value: str) -> str | None:
    if not value:
        return None
    m = re.search(r"guid:\s*([0-9a-fA-F]{8,})", value)
    return m.group(1) if m else None


def _parse_shop_table_asset(asset_path: str) -> dict:
    shop: dict = {
        "shop_name":     os.path.splitext(os.path.basename(asset_path))[0],
        "starting_items": [],
        "random_items":   [],
    }
    current_section = None
    current_item: dict | None = None

    def _commit_item() -> None:
        nonlocal current_item
        if not current_item:
            return
        current_item.setdefault("price", 0)
        current_item.setdefault("orbs", 0)
        current_item.setdefault("tickets", 0)
        is_random = bool(current_section and "random" in current_section.lower())
        bucket = "random_items" if is_random else "starting_items"
        shop[bucket].append(current_item)
        current_item = None

    with open(asset_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")

            m_name = re.match(r"^\s*m_Name:\s*(.+)\s*$", line)
            if m_name:
                shop["shop_name"] = m_name.group(1).strip()
                continue

            m_section = re.match(r"^\s*(startingItems\d*|randomItems\d*):\s*(\[\])?\s*$", line)
            if m_section:
                _commit_item()
                current_section = m_section.group(1)
                continue

            m_id = re.match(r"^\s*-\s*id:\s*(\d+)\s*$", line)
            if m_id:
                _commit_item()
                current_item = {"id": int(m_id.group(1))}
                continue

            if not current_item:
                continue

            m_field = re.match(r"^\s*(price|orbs|tickets):\s*(-?\d+)\s*$", line)
            if m_field:
                current_item[m_field.group(1)] = int(m_field.group(2))
                continue

            m_currency = re.match(r"^\s*itemToUseAsCurrency:\s*(\{.*\}|\S+)\s*$", line)
            if m_currency:
                guid = _parse_guid_from_braces(m_currency.group(1))
                current_item["item_to_use_as_currency"] = guid
                continue

    _commit_item()
    return shop

# ---------------------------------------------------------------------------
# Item name / currency helpers
# ---------------------------------------------------------------------------

def _build_id_and_guid_map(items: dict) -> dict:
    """Build a combined id_str → name and guid → name map from item cache."""
    result: dict[str, str] = {}
    for item in items.values():
        result[str(item.item_id)] = item.name
        if hasattr(item, "guid") and item.guid:
            result[item.guid] = item.name
            result[item.guid.lower()] = item.name
    return result


def _determine_price_and_currency(item: dict, name_map: dict) -> tuple:
    currency_guid = item.get("item_to_use_as_currency") or item.get("itemToUseAsCurrency")
    if currency_guid:
        currency_name = name_map.get(currency_guid, name_map.get(currency_guid.lower(), "UnknownCurrency"))
        return item.get("price", 0), currency_name

    if item.get("price", 0) > 0:
        return item["price"], "Coins"
    elif item.get("orbs", 0) > 0:
        return item["orbs"], "Orbs"
    elif item.get("tickets", 0) > 0:
        return item["tickets"], "Tickets"

    return None, None


def _get_item_name(item_id, name_map: dict) -> str:
    return name_map.get(str(item_id), f"Item {item_id}")

# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------

def _format_shop_data(shop_data: list, name_map: dict) -> str:
    output: list[str] = []

    for shop in shop_data:
        shop_name = shop.get("shop_name", "Unknown Shop")
        output.append(f"### {shop_name} ###")
        output.append("{{Shop/header}}")

        seen_items: set[str] = set()

        for item in shop.get("starting_items", []):
            item_id = item.get("id")
            if item_id is None:
                continue
            item_name = _get_item_name(item_id, name_map)
            if item_name in seen_items:
                continue
            seen_items.add(item_name)
            price, currency = _determine_price_and_currency(item, name_map)
            if price and currency:
                output.append(f"{{{{Shop|{item_name}|{price}|{currency}}}}}")

        for item in shop.get("random_items", []):
            item_id = item.get("id")
            if item_id is None:
                continue
            item_name = _get_item_name(item_id, name_map)
            if item_name in seen_items:
                continue
            seen_items.add(item_name)
            price, currency = _determine_price_and_currency(item, name_map)
            if price and currency:
                output.append(f"{{{{Shop|{item_name}|{price}|{currency}|random=1}}}}")

        output.append("{{Shop/footer}}\n")

    return "\n".join(output)

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_OUTPUT_FILE))

    shop_data: list = json_utils.load_json(_SHOP_DATA)

    # Normalize if wrapped in a dict
    if isinstance(shop_data, dict) and isinstance(shop_data.get("shops"), list):
        shop_data = shop_data["shops"]
    if shop_data is None:
        shop_data = []

    # Merge extra table assets
    table_paths = _find_table_assets(getattr(constants, "INPUT_DIRECTORY", None))
    extra_shops: list = []
    for asset_path in table_paths:
        try:
            extra_shops.append(_parse_shop_table_asset(asset_path))
        except Exception as exc:
            print(f"⚠️  Failed to parse table asset: {asset_path} ({exc})")

    if extra_shops and isinstance(shop_data, list):
        existing_names = {str(s.get("shop_name", "")).strip().lower() for s in shop_data}
        for s in extra_shops:
            name_key = str(s.get("shop_name", "")).strip().lower()
            if name_key and name_key not in existing_names:
                shop_data.append(s)
                existing_names.add(name_key)

    # Build name map from item cache
    items    = _load_cache()
    name_map = _build_id_and_guid_map(items)

    formatted = _format_shop_data(shop_data, name_map)
    file_utils.write_lines(_OUTPUT_FILE, [formatted])

    print(f"✅ {len(shop_data)} shops written to {_OUTPUT_FILE}")


if __name__ == "__main__":
    run()
