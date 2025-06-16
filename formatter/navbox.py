import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import json_utils, file_utils
from mappings.item_classification import classify_item

def create_item_navbox(item):
    """
    Create and return the appropriate navbox template based on the item classification.
    
    Navbox rules:
    - If itemType is Animal, use: {{Animal navbox|subtype}}
    - If itemType is Fish, use: {{Fish navbox}}
    - If itemType is Furniture, use: {{Furniture navbox|subtype}}
    - If subtype is Clothing, use: {{Clothing navbox|category}}
    - If subtype is Armor, Accessory, Weapon, or Tool, use: {{Equipment navbox|subtype}}
    - If subtype is House Customization use: {{Building customization navbox|house}}
    - Otherwise, add [[Category:Navbox needed]]
    """
    itemType, subtype, category = classify_item(item)
    
    if itemType == "Animal":
        return f"{{{{Animal navbox|{subtype}}}}}"
    elif itemType == "Fish":
        return "{{Fish navbox}}"
    elif itemType == "Furniture":
        return f"{{{{Furniture navbox|{subtype}}}}}"
    elif subtype.lower() == "mount":
        return f"{{{{Animal navbox|mounts}}}}"
    elif subtype.lower() == "clothing":
        return f"{{{{Clothing navbox|{category}}}}}"
    elif subtype.lower() in ("armor", "accessory", "weapon", "tool"):
        return f"{{{{Equipment navbox|{subtype}}}}}"
    elif subtype.lower() == "house customization":
        return f"{{{{Building customization navbox|house}}}}"
    else:
        return "[[Category:Navbox needed]]"
