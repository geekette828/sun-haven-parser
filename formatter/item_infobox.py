import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
import logging
from utils import json_utils, file_utils, text_utils
from mappings.item_classification import classify_item
from mappings.item_infobox_mapping import format_infobox

def setup_logger(debug_log_path):
    logger = logging.getLogger("create_item_infobox")
    logger.setLevel(logging.DEBUG)
    file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))
    fh = logging.FileHandler(debug_log_path, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

def process_items(test_items=None):
    json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
    output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "item_infobox.txt")
    debug_log_path = os.path.join(".hidden", "debug_output", "create_item_infobox_debug.txt")

    file_utils.ensure_dir_exists(os.path.dirname(output_file_path))
    file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

    logger = setup_logger(debug_log_path)
    logger.info("Starting item infobox generation.")

    if test_items is None:
        test_items = [
            "Iron Ring",
            "Candy Corn Fruit Pop",
            "Watery Protector's Potion",
            "Carrot Juice",
            "Apple Juice",
            "Candied Yams"
        ]
    logger.info(f"Test items: {test_items}")

    try:
        items_data = json_utils.load_json(json_file_path)
        logger.info("Successfully loaded JSON data.")
    except Exception as e:
        logger.exception("Failed to load JSON data.")
        return

    items_data_lower = { key.lower(): value for key, value in items_data.items() }

    output_lines = []
    for item_name in test_items:
        key = item_name.lower()
        if key in items_data_lower:
            item = items_data_lower[key]
            # Sanitize any color/sprite tags
            for field in ["description", "useDescription"]:
                if field in item:
                    item[field] = text_utils.sanitize_text(item[field])

            classification = classify_item(item)
            infobox_text = format_infobox(item, classification, item_name)
            if infobox_text:
                output_lines.append(f"Item: {item_name}\n{infobox_text}")
                logger.info(f"Generated infobox for: {item_name}")
            else:
                logger.info(f"Skipped infobox for: {item_name} (non-display type)")
        else:
            logger.warning(f"Item '{item_name}' not found in JSON data.")

    try:
        file_utils.write_lines(output_file_path, ["\n\n".join(output_lines)])
        logger.info("Successfully wrote output file.")
    except Exception as e:
        logger.exception("Failed to write output file.")

def main():
    process_items()

if __name__ == "__main__":
    main()

print("Item infobox creation complete")
