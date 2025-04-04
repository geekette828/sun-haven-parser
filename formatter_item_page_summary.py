import re
from formatter_itemInfobox_classifications import classify_item
import config.constants as constants

# Dictionary mapping (Item Type, Subtype, Category) to summary text.
# Replace '''ITEM NAME''' with the actual item name.
# Replace  ''RARITY'' (for pets or fish) with the item's rarity.
# Replace SEASONAL LINE, EXPERIENCE, SELL, and SELLTYPE for fish summaries.
SUMMARIES = {
    # EQUIPMENT > CLOTHING
    ("Equipment", "Clothing", "Skirt"): "'''ITEM NAME''' is a [[clothing]] item for the player's leg slot. Clothing items do not have stats that buff the player, and it is recommended they are only put into the cosmetic slots. Cosmetic items are meant to allow the player to customize the look of their character however they want, without hindering their stats.",
    ("Equipment", "Clothing", "Pants"): "'''ITEM NAME''' is a [[clothing]] item for the player's leg slot. Clothing items do not have stats that buff the player, and it is recommended they are only put into the cosmetic slots. Cosmetic items are meant to allow the player to customize the look of their character however they want, without hindering their stats.",
    ("Equipment", "Clothing", "Shorts"): "'''ITEM NAME''' is a [[clothing]] item for the player's leg slot. Clothing items do not have stats that buff the player, and it is recommended they are only put into the cosmetic slots. Cosmetic items are meant to allow the player to customize the look of their character however they want, without hindering their stats.",
    ("Equipment", "Clothing", "Dress"): "'''ITEM NAME''' is a [[clothing]] item for the player's chest slot. Clothing items do not have stats that buff the player, and it is recommended they are only put into the cosmetic slots. Cosmetic items are meant to allow the player to customize the look of their character however they want, without hindering their stats.",
    ("Equipment", "Clothing", "Shirt"): "'''ITEM NAME''' is a [[clothing]] item for the player's chest slot. Clothing items do not have stats that buff the player, and it is recommended they are only put into the cosmetic slots. Cosmetic items are meant to allow the player to customize the look of their character however they want, without hindering their stats.",
    ("Equipment", "Clothing", "Gloves"): "'''ITEM NAME''' is a [[clothing]] item for the player's hand slot. Clothing items do not have stats that buff the player, and it is recommended they are only put into the cosmetic slots. Cosmetic items are meant to allow the player to customize the look of their character however they want, without hindering their stats.",
    ("Equipment", "Clothing", "Wig"): "'''ITEM NAME''' is a [[clothing]] item for the player's head slot. Clothing items do not have stats that buff the player, and it is recommended they are only put into the cosmetic slots. Cosmetic items are meant to allow the player to customize the look of their character however they want, without hindering their stats.",
    ("Equipment", "Clothing", "Hat"): "'''ITEM NAME''' is a [[clothing]] item for the player's head slot. Clothing items do not have stats that buff the player, and it is recommended they are only put into the cosmetic slots. Cosmetic items are meant to allow the player to customize the look of their character however they want, without hindering their stats.",
    ("Equipment", "Clothing", "Cape"): "'''ITEM NAME''' is a [[clothing]] item for the player's back slot. Clothing items do not have stats that buff the player, and it is recommended they are only put into the cosmetic slots. Cosmetic items are meant to allow the player to customize the look of their character however they want, without hindering their stats.",
    
    # EQUIPMENT > ARMOR
    ("Equipment", "Armor", "Helmet"): "The '''ITEM NAME''' is an armor item for the player head slot. Armor items have various stats that buff the user. If the player enjoys the look of a particular armor item, but has a better item with different stats, the player can put armor items into the cosmetic slot. The player does not gain any stat benefits from armor items in the cosmetic slot, the cosmetic slot only displays the skin of that item on the player's character.",
    ("Equipment", "Armor", "Chest"): "The '''ITEM NAME''' is an armor item for the player chest slot. Armor items have various stats that buff the user. If the player enjoys the look of a particular armor item, but has a better item with different stats, the player can put armor items into the cosmetic slot. The player does not gain any stat benefits from armor items in the cosmetic slot, the cosmetic slot only displays the skin of that item on the player's character.",
    ("Equipment", "Armor", "Gloves"): "The '''ITEM NAME''' is an armor item for the player hand slot. Armor items have various stats that buff the user. If the player enjoys the look of a particular armor item, but has a better item with different stats, the player can put armor items into the cosmetic slot. The player does not gain any stat benefits from armor items in the cosmetic slot, the cosmetic slot only displays the skin of that item on the player's character.",
    ("Equipment", "Armor", "Legs"): "The '''ITEM NAME''' is an armor item for the player legs slot. Armor items have various stats that buff the user. If the player enjoys the look of a particular armor item, but has a better item with different stats, the player can put armor items into the cosmetic slot. The player does not gain any stat benefits from armor items in the cosmetic slot, the cosmetic slot only displays the skin of that item on the player's character.",
    ("Equipment", "Armor", "Cape"): "The '''ITEM NAME''' is an armor item for the player back slot. Armor items have various stats that buff the user. If the player enjoys the look of a particular armor item, but has a better item with different stats, the player can put armor items into the cosmetic slot. The player does not gain any stat benefits from armor items in the cosmetic slot, the cosmetic slot only displays the skin of that item on the player's character.",
    
    # EQUIPMENT > ACCESSORY
    ("Equipment", "Accessory", "Ring"): "'''ITEM NAME''' is an [[Accessories|accessory]] item for the player's ring slot. The player is allowed to wear two rings at a time.",
    ("Equipment", "Accessory", "Amulet"): "'''ITEM NAME''' is an [[Accessories|accessory]] item for the player's amulet slot. Accessories do not belong to any set, thus this item does not receive any set bonuses from the ''[[Uniformity|uniformity skill]]''.",
    ("Equipment", "Accessory", "Keepsake"): "'''ITEM NAME''' is an [[Accessories|accessory]] item for the player's keepsake slot. Accessories do not belong to any set, thus it does not receive any set bonuses from the ''[[Uniformity|uniformity skill]]''.",
    
    # EQUIPMENT > TOOL
    ("Equipment", "Tool", "Axe"): "'''ITEM NAME''' is a tool used to chop down trees and stumps. There is technically no minimum level of axe strength the player must have in order to chop [[hardwood]] trees and stumps on their Sun Haven Farm, nor a minimum level for the [[Elven Hardwood]] trees; however, the trees and stumps regenerate health. A single player must have a strong enough axe that can outpace the trees' regeneration, or have more than one player chopping away at the same tree.",
    ("Equipment", "Tool", "Pickaxe"): "'''ITEM NAME''' is a tool used to mine rocks and ore nodes. There is technically no minimum level of pickaxe strength the player must have in order to mine [[heavystone]] and [[Elven Heavystone|elven heavystone]]; however, the rocks regenerate health. A single player must have a strong enough pickaxe that can outpace the rocks' regeneration, or have more than one player mining away at the same rock.",
    ("Equipment", "Tool", "Rod"): "'''ITEM NAME''' is a tool used to catch fish in the waters around Sun Haven and other regions. Fishing poles hold some unique stats compared to the other tools in the game, and some give additional bonuses on top of the stat changes.",
    ("Equipment", "Tool", "Hoe"): "'''ITEM NAME''' is a tool used to til the earth, so the player can plant seeds. Each tier upgrade to the hoe increases the speed at which the player can till the ground.",
    ("Equipment", "Tool", "Watering Can"): "'''ITEM NAME''' is a tool used to water [[crops]]. Each tier upgrade to the watering can, increases the water capacity and the use speed from the previous tier.", 
    ("Equipment", "Tool", "Net"): "'''ITEM NAME''' is a tool used to passively catch fish on the player's [[Sun Haven Farm]], and cannot be placed on the [[Nel'Vari Farm]] nor the [[Withergate Rooftop Farm|Withergate Farm]]. Nets can be placed in either of the ponds, the river, or the ocean and will automatically catch fish for the player. The [[fish]] caught will slightly differ if the net is placed in the lakes and rivers of the player's farm or if the net is placed in the sea. Nets can be collected from roughly once a day.\n\nNets require fishing permits that are sold at [[Peter's Fishing Store]], each permit will increase the number of nets the player is able to deploy on their farm. Only one permit per tier is allowed in each world, regardless of how many players are in that world. ", 
    ("Equipment", "Tool", "Scythe"): "",
    
    # FURNITURE
    ("Furniture", "Bed", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. This item cannot be rotated and must always be facing front. The majority of furniture items serve no purpose aside from allowing the player to customize the aesthetic of their farm and housing; however, [[Furniture/Beds|beds]] are used to progress the player to the next day. If the player does not fall asleep in a bed before the clock strikes midnight, the player will faint from exhaustion. Fainting costs the player money and forces the next day upon them.\n\nThe bed cannot be used to skip the entire day, however, as the earliest the player can go to bed is 06:00 PM. Attempting to interact with the bed at any earlier time displays the message \"It is too early to sleep!\"\n\n[[Furniture]] items can be placed within the boundaries of the player character's farm; whether indoors, outdoors, or both. The player can pick up furniture items by hitting them with a [[pickaxe]].",
    ("Furniture", "Nightstand", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. [[Furniture/Surfaces#End Tables|End tables]] (also called nightstands) are a type of furniture item that allow smaller items to be placed on top of them for decoration. They are generally smaller than tables and are often found next to couches or beds.\n\n[[Furniture]] items can be placed within the boundaries of the player character's farm; whether indoors, outdoors, or both. Items that require a wall can only be placed indoors. The player can pick up furniture items by hitting them with a [[pickaxe]].",
    ("Furniture", "Bridge", ""): "'''ITEM NAME''' is a unique piece of furniture that can be built to update the look of the existing bridge on the player's [[Sun Haven Farm]]. Unlike [[wallpaper]], which can be used repeatedly, [[Furniture/Bridges|bridges]] are one-time use. If the player replaces their bridge and later wants a previous or new design, they will need to build a new bridge.",
    ("Furniture", "Bookcase", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. [[Furniture/Decoration#Bookcases|Bookcases]] are decorative shelves for display only—the player cannot store books on them.\n\n[[Furniture]] items can be placed within the boundaries of the player character's farm; whether indoors, outdoors, or both. Items that require a wall can only be placed indoors. The player can pick up furniture items by hitting them with a [[pickaxe]].",
    ("Furniture", "Couch", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. [[Furniture/Seating#Couches|Couches]] are decorative and cannot be sat on.\n\n[[Furniture]] items can be placed within the boundaries of the player character's farm; whether indoors, outdoors, or both. Items that require a wall can only be placed indoors. The player can pick up furniture items by hitting them with a [[pickaxe]].",
    ("Furniture", "Chair", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. Chairs are decorative and the player cannot sit on any chair, couch, or stool.\n\n[[Furniture]] items can be placed within the boundaries of the player character's farm; whether indoors, outdoors, or both. The player can pick up furniture items by hitting them with a [[pickaxe]].",
    ("Furniture", "Chest", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. This item cannot be rotated and must always face front. The basic chest provides 6x5 slots (30 items total) regardless of item type, and the player can change its color or name in the open chest UI. [[Furniture/Storage#Chests|Chests]] are similar to [[Furniture/Storage#Refrigerators|refrigerators]] and [[Furniture/Storage#Wardrobes|wardrobes]], as they store various items.\n\n[[Furniture]] items can be placed within the boundaries of the player character's farm; whether indoors, outdoors, or both. Items that require a wall can only be placed indoors. The player can pick up furniture items by hitting them with a [[pickaxe]].",
    ("Furniture", "Fireplace", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor of the player's house or farm. It cannot be rotated and must always face front. [[Furniture/Lighting#Fireplaces|Fireplaces]] are decorative items that provide a little light.\n\n[[Furniture]] items can be placed within the boundaries of the player character's farm; whether indoors, outdoors, or both. Items requiring a wall can only be placed indoors. The player can pick up furniture items by hitting them with a [[pickaxe]].",
    ("Furniture", "Lighting", ""): "'''ITEM NAME''' is a piece of furniture. Items that provide [[Furniture/Lighting|light]] will automatically turn on when it gets dark and emit a glow around them.\n\n[[Furniture]] items can be placed within the boundaries of the player character's farm; whether indoors, outdoors, or both. Items requiring a wall can only be placed indoors. The player can pick up furniture items by hitting them with a [[pickaxe]].",
    ("Furniture", "Plushie", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor of the player's house or farm, or on top of surfaces like shelves and tables. It cannot be rotated and must always face front. [[Furniture/Plushies|Plushies]] are toys covered in plush fabric and filled with soft material. Like other plushies in Sun Haven, this item is purely cosmetic and cannot be interacted with.\n\n[[Furniture]] items can be placed within the boundaries of the player character's farm; whether indoors, outdoors, or both. Items requiring a wall can only be placed indoors. The player can pick up furniture items by hitting them with a [[pickaxe]].",
    ("Furniture", "Table", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. [[Furniture/Surfaces#Tables|Tables]] are decorative surfaces on which smaller items can be placed.\n\n[[Furniture]] items can be placed within the boundaries of the player character's farm; whether indoors, outdoors, or both. Items requiring a wall can only be placed indoors. The player can pick up furniture items by hitting them with a [[pickaxe]].",
    ("Furniture", "Wardrobe", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. It cannot be rotated and must always face forward. [[Furniture/Storage#Wardrobes|Wardrobes]] function similarly to chests.\n\nAll [[furniture]] items can be placed within the boundaries of the player character's farm. Items placed on the floor or surfaces can be both indoors and outdoors, but items on a wall must be placed inside a building. The player can pick up furniture items by hitting them with a [[pickaxe]].",
    ("Furniture", "", ""): "'''ITEM NAME''' is a piece of furniture.\n\nAll [[furniture]] items can be placed within the boundaries of the player character's farm. Items placed on the floor or surfaces can be indoors or outdoors, but items placed on a wall must be inside a building. The player can pick up furniture items by hitting them with a [[pickaxe]].",

    # ANIMAL > PET
    ("Animal", "Pet", ""): "'''ITEM NAME''' is a ''RARITY'' quality creature that provides companionship for the player on their farm and during travels. Companion pets can be placed on the player's farm or the player can use a [[Pet Leash|pet leash]] to have the companion pet follow the player throughout the world. Pets take no damage while following the player around, nor do they attack.\n\nThere are two skills the player can choose to benefit from owning various companion pets. If the player chooses to put the pet on their farm and invests in the ''[[Zookeeper]]'' skill, pets on the farm will grant a bonus in gold each day. If the player invests in the ''[[Promenade]]'' skill, when a companion pet is leashed by the player's side, the player will get a bonus to movement speed and receive exploration experience every in-game hour.",
    
    # FISH
    ("Fish", "", ""): "'''ITEM NAME''' is an ''RARITY'' type of fish which can be caught SEASONAL LINE. {{Bonding experience|EXPERIENCE}}\n\n{{Fishing skill price calculations|SELL|SELLTYPE}}",
}

def normalize_classification(itemType, subtype, category):
    """
    Normalize the classification values to title-case.
    Since only the first field is required, subtype and category remain empty if not provided.
    """
    itemType = itemType.strip().title() if itemType else ""
    subtype = subtype.strip().title() if subtype else ""
    category = category.strip().title() if category else ""
    return (itemType, subtype, category)

def get_sell_info(item):
    """
    (Not used if we parse values from the infobox.)
    Determine the sell price and type for an item.
    Priority: sellPrice (coins) > orbsSellPrice (orbs) > ticketSellPrice (tickets)
    """
    if item.get("sellPrice", 0):
        return item["sellPrice"], "coins"
    elif item.get("orbsSellPrice", 0):
        return item["orbsSellPrice"], "orbs"
    elif item.get("ticketSellPrice", 0):
        return item["ticketSellPrice"], "tickets"
    else:
        return "SELL", "SELLTYPE"

def parse_infobox(infobox):
    """
    Parse the infobox output to extract computed values.
    Returns a dictionary with keys in lower case.
    """
    pattern = re.compile(r'\|\s*(\w+)\s*=\s*(.+)')
    computed = {}
    for line in infobox.splitlines():
        match = pattern.match(line)
        if match:
            key, value = match.groups()
            computed[key.strip().lower()] = value.strip()
    return computed

def create_item_summary(item, computed, display_name=None):
    """
    Generate and return a summary string for the given item using the summary template
    and the computed values parsed from the infobox.
    
    Optionally, a display_name can be provided if the item object does not include the name.
    The display name will be converted to title case.
    """
    from formatter_itemInfobox_classifications import classify_item
    itemType, subtype, category = classify_item(item)
    key = normalize_classification(itemType, subtype, category)
    summary_template = SUMMARIES.get(key, "Summary is needed for this item. [[Category:Missing summary]]")
    
    # Use display_name override if provided, otherwise use the "name" field.
    if display_name is None:
        display_name = item.get("name", "ITEM NAME")
    # Convert the display name to title case.
    display_name = display_name.title()
    
    # Replace ITEM NAME placeholder (the template has it surrounded by triple quotes)
    summary = summary_template.replace("ITEM NAME", display_name)
    
    # Replace rarity using the computed value if available.
    raw_rarity = computed.get("rarity", str(item.get("rarity", "rarity")))
    if raw_rarity.isdigit():
        rarity = constants.RARITY_TYPE_MAPPING.get(int(raw_rarity), raw_rarity)
    else:
        rarity = raw_rarity
    rarity = rarity.lower()
    summary = summary.replace("RARITY", rarity)
    
    # For fish items, use the computed infobox values.
    if key == ("Fish", "", ""):
        seasonal_mapping = {
            "Spring": "in the spring season",
            "Summer": "in the summer season",
            "Fall": "in the fall season",
            "Winter": "in the winter season",
            "Any": "in all seasons"
        }
        season = computed.get("season", "Any")
        seasonal_line = seasonal_mapping.get(season, "in all seasons")
        summary = summary.replace("SEASONAL LINE", seasonal_line)
        
        exp_value = computed.get("exp", "EXPERIENCE")
        summary = summary.replace("EXPERIENCE", str(exp_value))
        
        # Replace SELLTYPE before SELL.
        selltype = computed.get("selltype", "SELLTYPE")
        summary = summary.replace("SELLTYPE", selltype.lower())
        sell = computed.get("sell", "SELL")
        summary = summary.replace("SELL", sell)
    
    return summary