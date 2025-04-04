import os
import json
import logging
import config.constants as constants  
from formatter_itemInfobox_classifications import classify_item
from formatter_itemInfobox_item_Data import format_item_data

def setup_logger(debug_log_path):
    logger = logging.getLogger("formatter_itemInfobox")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(debug_log_path, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

def get_sell_info(item):
    # Priority: sellPrice (coins) > orbsSellPrice (orbs) > ticketSellPrice (tickets)
    if item.get("sellPrice", 0):
        return item["sellPrice"], "coins"
    elif item.get("orbsSellPrice", 0):
        return item["orbsSellPrice"], "orbs"
    elif item.get("ticketSellPrice", 0):
        return item["ticketSellPrice"], "tickets"
    else:
        return 0, ""

def create_basic_infobox(item):
    sell, selltype = get_sell_info(item)
    stack = item.get("stackSize", "")
    rarity = item.get("rarity", "")
    hearts = item.get("hearts", "")
    dlc_val = item.get("isDLCItem", 0)
    dlc_str = "True" if dlc_val == 1 else "False"
    
    # Get classification fields from the classification module.
    itemType, subtype, category = classify_item(item)
    
    basic_infobox = (
        "{{Item infobox\n"
        f"|sell = {sell}\n"
        f"|selltype = {selltype}\n"
        f"|stack = {stack}\n"
        f"|rarity = {rarity}\n"
        f"|hearts = {hearts}\n"
        "<!-- Item Classification -->\n"
        f"|itemType = {itemType}\n"
        f"|subtype = {subtype}\n"
        f"|category = {category}\n"
        f"|dlc = {dlc_str}\n"
    )
    return basic_infobox

def create_full_infobox(item):
    basic = create_basic_infobox(item)
    classification = classify_item(item)
    extra_data = format_item_data(classification, item)
    
    # If extra data exists, insert it before the closing braces.
    if extra_data.strip():
        full_infobox = basic + extra_data + "\n}}"
    else:
        full_infobox = basic + "}}"
    return full_infobox

def main():
    json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
    output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "itemInfobox.txt")
    debug_log_path = os.path.join(constants.OUTPUT_DIRECTORY, "Debug", "formatter_itemInfobox_debug.txt")
    
    logger = setup_logger(debug_log_path)
    logger.info("Starting full infobox formatting.")
    
    # Hard-coded test items for development; update as needed.
    test_items = [
        "iris shirt", 
        "iris skirt", 
        "iris wig", 
        "iris' bed", 
        "iris' bench", 
        "iris' chair", 
        "iris' dresser", 
        "iris' lamp", 
        "iris' painting", 
        "iris' plushie", 
        "iris' rug", 
        "iris' table", 
        "iris' topiary", 
        "iris' wardrobe", 
        "mage master coat", 
        "mage master pants", 
        "mage master wig", 
        "mage student pants", 
        "mage student shirt", 
        "mage student wig"
    ]
    logger.info(f"Test items: {test_items}")
    
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            items_data = json.load(f)
        logger.info("Successfully loaded JSON data.")
    except Exception as e:
        logger.exception("Failed to load JSON data.")
        return
    
    # Build a new dictionary with lower-case keys.
    items_data_lower = { key.lower(): value for key, value in items_data.items() }
    
    output_lines = []
    for item_name in test_items:
        key = item_name.lower()
        if key in items_data_lower:
            item = items_data_lower[key]
            full_infobox = create_full_infobox(item)
            output_lines.append(f"Item: {item_name}\n{full_infobox}")
            logger.info(f"Processed full infobox for: {item_name}")
        else:
            logger.warning(f"Item '{item_name}' not found in JSON data.")
    
    try:
        with open(output_file_path, "w", encoding="utf-8") as outf:
            outf.write("\n\n".join(output_lines))
        logger.info("Successfully wrote output file.")
    except Exception as e:
        logger.exception("Failed to write output file.")

if __name__ == "__main__":
    main()
