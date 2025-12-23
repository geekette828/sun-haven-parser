import os
import sys
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import json_utils, file_utils


def find_table_assets(root_directory):
    """Recursively find *.asset files matching the furniture table patterns."""
    patterns = (
        "wallpapertable.asset",
        "largeitemstable.asset",
        "floordingtable.asset",
        "flooringtable.asset",
        "smallitemstable.asset",
    )

    matches = []
    if not root_directory or not os.path.isdir(root_directory):
        return matches

    for root, _, files in os.walk(root_directory):
        for filename in files:
            lower = filename.lower()
            if lower.endswith(patterns):
                matches.append(os.path.join(root, filename))

    return sorted(matches)

def _parse_guid_from_braces(value):
    """Extract GUID from a Unity YAML reference like {fileID: ..., guid: XXXXX, type: ...}."""
    if not value:
        return None
    m = re.search(r"guid:\s*([0-9a-fA-F]{8,})", value)
    return m.group(1) if m else None

def parse_shop_table_asset(asset_path):
    """Parse a *Table.asset (Unity YAML) and return a shop-like dict.

    We only extract what all_shops needs:
    - shop_name (from m_Name, falling back to filename)
    - starting_items / random_items (lists of dicts containing id/price/orbs/tickets/itemToUseAsCurrency)
    """
    shop = {
        "shop_name": os.path.splitext(os.path.basename(asset_path))[0],
        "starting_items": [],
        "random_items": [],
    }

    current_section = None  # startingItems, startingItems2, randomItems, randomItems2, etc.
    current_item = None

    def commit_item():
        nonlocal current_item
        if not current_item:
            return

        # default missing numeric fields to 0 so determine_price_and_currency behaves consistently
        current_item.setdefault("price", 0)
        current_item.setdefault("orbs", 0)
        current_item.setdefault("tickets", 0)

        is_random = bool(current_section and "random" in current_section.lower())
        if is_random:
            shop["random_items"].append(current_item)
        else:
            shop["starting_items"].append(current_item)

        current_item = None

    with open(asset_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")

            # Shop/table name
            m_name = re.match(r"^\s*m_Name:\s*(.+)\s*$", line)
            if m_name:
                shop["shop_name"] = m_name.group(1).strip()
                continue

            # Section headers
            m_section = re.match(r"^\s*(startingItems\d*|randomItems\d*):\s*(\[\])?\s*$", line)
            if m_section:
                commit_item()
                current_section = m_section.group(1)
                continue

            # New item start
            m_id = re.match(r"^\s*-\s*id:\s*(\d+)\s*$", line)
            if m_id:
                commit_item()
                current_item = {"id": int(m_id.group(1))}
                continue

            if not current_item:
                continue

            # Fields within an item
            m_field = re.match(r"^\s*(price|orbs|tickets):\s*(-?\d+)\s*$", line)
            if m_field:
                key = m_field.group(1)
                current_item[key] = int(m_field.group(2))
                continue

            m_currency = re.match(r"^\s*itemToUseAsCurrency:\s*(\{.*\}|\S+)\s*$", line)
            if m_currency:
                guid = _parse_guid_from_braces(m_currency.group(1))
                if guid:
                    current_item["itemToUseAsCurrency"] = guid
                else:
                    # {fileID: 0} or empty => treat as None
                    current_item["itemToUseAsCurrency"] = None
                continue

    commit_item()
    return shop


def transform_items_data(items_data):
    """Transform items_data.json into a dictionary with IDs and GUIDs as keys."""
    transformed = {}
    for item_name, item_info in items_data.items():
        base_name = item_info.get("Name", item_name.split(" (")[0])  # Remove color/variant details
        if "ID" in item_info:
            transformed[str(item_info["ID"])] = base_name
        if "GUID" in item_info:
            guid = item_info["GUID"]
            transformed[guid] = base_name
            transformed[guid.lower()] = base_name  # extra safety
    return transformed

def determine_price_and_currency(item, items_data):
    """Determine the price and currency, including custom currency via GUID."""
    currency_guid = item.get("itemToUseAsCurrency")

    # If itemToUseAsCurrency is not null, use the GUID to get currency name
    if currency_guid:
        currency_name = items_data.get(currency_guid, items_data.get(currency_guid.lower(), "UnknownCurrency"))
        return item.get("price", 0), currency_name

    # Otherwise, fall back to orbs/tickets/coins
    if item.get("price", 0) > 0:
        return item["price"], "Coins"
    elif item.get("orbs", 0) > 0:
        return item["orbs"], "Orbs"
    elif item.get("tickets", 0) > 0:
        return item["tickets"], "Tickets"

    return None, None

def get_item_name_by_id(item_id, items_data):
    """Retrieve item name from transformed items_data based on ID."""
    return items_data.get(str(item_id), f"Item {item_id}")

def format_shop_data(shop_data, items_data):
    """Format shop data into the required format."""
    formatted_output = []

    for shop in shop_data:
        shop_name = shop.get("shop_name", "Unknown Shop")
        formatted_output.append(f"### {shop_name} ###")
        formatted_output.append("{{Shop/header}}")

        seen_items = set()

        for item in shop.get("starting_items", []):
            item_id = item.get("id")
            if item_id is None:
                continue

            item_name = get_item_name_by_id(item_id, items_data)
            if item_name in seen_items:
                continue
            seen_items.add(item_name)

            price, currency = determine_price_and_currency(item, items_data)
            if price and currency:
                formatted_output.append(f"{{{{Shop|{item_name}|{price}|{currency}}}}}")

        for item in shop.get("random_items", []):
            item_id = item.get("id")
            if item_id is None:
                continue

            item_name = get_item_name_by_id(item_id, items_data)
            if item_name in seen_items:
                continue
            seen_items.add(item_name)

            price, currency = determine_price_and_currency(item, items_data)
            if price and currency:
                formatted_output.append(f"{{{{Shop|{item_name}|{price}|{currency}|random=1}}}}")

        formatted_output.append("{{Shop/footer}}\n")

    return "\n".join(formatted_output)

def main():
    """Main function to process the JSON files and create the formatted output."""
    input_directory = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
    output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted")
    file_utils.ensure_dir_exists(output_directory)

    shop_data_path = os.path.join(input_directory, "shop_data.json")
    items_data_path = os.path.join(input_directory, "items_data.json")
    output_file_path = os.path.join(output_directory, "shops.txt")

    shop_data = json_utils.load_json(shop_data_path)

    # Also build the extra furniture/flooring/wallpaper tables that are stored as *.asset files.
    # These are not always present in shop_data.json.
    asset_root_directory = getattr(constants, "INPUT_DIRECTORY", None)
    table_asset_paths = find_table_assets(asset_root_directory)
    extra_shops = []
    for asset_path in table_asset_paths:
        try:
            extra_shops.append(parse_shop_table_asset(asset_path))
        except Exception as e:
            print(f"🛠️  Failed to parse table asset: {asset_path} ({e})")

    if extra_shops:
        # shop_data.json can be either a list or a dict wrapper; normalize first
        if isinstance(shop_data, dict) and isinstance(shop_data.get("shops"), list):
            shop_data = shop_data["shops"]
        if shop_data is None:
            shop_data = []
        if not isinstance(shop_data, list):
            print("🛠️  Unexpected shop_data.json format; skipping merge of extra table assets.")
        else:
            existing_names = {str(s.get("shop_name", "")).strip().lower() for s in shop_data if isinstance(s, dict)}
            for s in extra_shops:
                name_key = str(s.get("shop_name", "")).strip().lower()
                if name_key and name_key not in existing_names:
                    shop_data.append(s)
                    existing_names.add(name_key)
    raw_items_data = json_utils.load_json(items_data_path)
    items_data = transform_items_data(raw_items_data)

    formatted_output = format_shop_data(shop_data, items_data)

    file_utils.write_lines(output_file_path, [formatted_output])

    print("Shops file generated successfully.")

    # after computing paths in main()
    print("🔍 reading:", os.path.abspath(shop_data_path))
    print("📝 writing:", os.path.abspath(output_file_path))

    # shop_data already loaded (and may include merged table assets)
    if isinstance(shop_data, dict) and isinstance(shop_data.get("shops"), list):
        shop_data = shop_data["shops"]

    print(f"📦 shops discovered: {len(shop_data)}")
    print("   sample:", [s.get("shop_name") for s in shop_data[:10]])
    print("   generals:", [s.get("shop_name") for s in shop_data if 'general' in str(s.get('shop_name','')).lower()][:10])


if __name__ == "__main__":
    main()
