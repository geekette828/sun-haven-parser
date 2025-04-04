import os
import config.constants as constants
from utils import json_utils, file_utils

def transform_items_data(items_data):
    """Transform items_data.json into a dictionary with IDs and GUIDs as keys."""
    transformed = {}
    for item_name, item_info in items_data.items():
        base_name = item_name.split(" (")[0]  # Remove color/variant details
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
    raw_items_data = json_utils.load_json(items_data_path)
    items_data = transform_items_data(raw_items_data)

    formatted_output = format_shop_data(shop_data, items_data)

    file_utils.write_lines(output_file_path, [formatted_output])

    print("Shops file generated successfully.")

if __name__ == "__main__":
    main()
