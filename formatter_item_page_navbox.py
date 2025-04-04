import os
from utils import json_utils, file_utils
import config.constants as constants
from formatter_itemInfobox_classifications import classify_item

def create_item_navbox(item):
    """
    Create and return the appropriate navbox template based on the item classification.
    
    Navbox rules:
    - If itemType is Animal, use: {{Animal navbox|subtype}}
    - If itemType is Fish, use: {{Fish navbox}}
    - If itemType is Furniture, use: {{Furniture navbox|subtype}}
    - If subtype is Clothing, use: {{Clothing navbox|category}}
    - If subtype is Armor, Accessory, Weapon, or Tool, use: {{Equipment navbox|subtype}}
    - Otherwise, add [[Category:Navbox needed]]
    """
    itemType, subtype, category = classify_item(item)
    
    if itemType == "Animal":
        return f"{{{{Animal navbox|{subtype}}}}}"
    elif itemType == "Fish":
        return "{{Fish navbox}}"
    elif itemType == "Furniture":
        return f"{{{{Furniture navbox|{subtype}}}}}"
    elif subtype.lower() == "clothing":
        return f"{{{{Clothing navbox|{category}}}}}"
    elif subtype.lower() in ("armor", "accessory", "weapon", "tool"):
        return f"{{{{Equipment navbox|{subtype}}}}}"
    else:
        return "[[Category:Navbox needed]]"
