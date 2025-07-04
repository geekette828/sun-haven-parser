import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
import re
from mappings.item_classification import classify_item

# Dictionary mapping (Item Type, Subtype, Category) to summary text.
# Replace '''ITEM NAME''' with the actual item name.
# Replace  ''RARITY'' (for pets or fish) with the item's rarity.
# Replace SEASONAL LINE, EXPERIENCE, SELL, and SELLTYPE for fish summaries.
SUMMARIES = {
    # BUILDING > HOUSE CUSTOMIZATION
    ("Building", "House Customization", "Door"): """The '''ITEM NAME''' is one of several [[House Customization/TYPE_PLURAL|TYPE_PLURAL]] the player can select to personalize the exterior of their home. These customizations affect the look and feel of the house and will automatically adapt to match each new tier when the house is upgraded. While the layout and structure of the house may change across tiers, the selected style will remain consistent throughout all upgrades.\n\nThe player can [[House Customization|customize]] the exterior of their Sun Haven [[Home Sweet Home|house]] by individually changing the roof, walls, door, windows, and patio. There are many styles available, and the player is not locked into a specific theme.\n\nOther items in the '''STYLE''' set include STYLE_MATCHES.""",
    ("Building", "House Customization", "Roof"): """The '''ITEM NAME''' is one of several [[House Customization/TYPE_PLURAL|TYPE_PLURAL]] the player can select to personalize the exterior of their home. These customizations affect the look and feel of the house and will automatically adapt to match each new tier when the house is upgraded. While the layout and structure of the house may change across tiers, the selected style will remain consistent throughout all upgrades.\n\nThe player can [[House Customization|customize]] the exterior of their Sun Haven [[Home Sweet Home|house]] by individually changing the roof, walls, door, windows, and patio. There are many styles available, and the player is not locked into a specific theme.\n\nOther items in the '''STYLE''' set include STYLE_MATCHES.""",
    ("Building", "House Customization", "Walls"): """The '''ITEM NAME''' is one of several [[House Customization/TYPE_PLURAL|TYPE_PLURAL]] the player can select to personalize the exterior of their home. These customizations affect the look and feel of the house and will automatically adapt to match each new tier when the house is upgraded. While the layout and structure of the house may change across tiers, the selected style will remain consistent throughout all upgrades.\n\nThe player can [[House Customization|customize]] the exterior of their Sun Haven [[Home Sweet Home|house]] by individually changing the roof, walls, door, windows, and patio. There are many styles available, and the player is not locked into a specific theme.\n\nOther items in the '''STYLE''' set include STYLE_MATCHES.""",
    ("Building", "House Customization", "Windows"): """The '''ITEM NAME''' is one of several [[House Customization/TYPE_PLURAL|TYPE_PLURAL]] the player can select to personalize the exterior of their home. These customizations affect the look and feel of the house and will automatically adapt to match each new tier when the house is upgraded. While the layout and structure of the house may change across tiers, the selected style will remain consistent throughout all upgrades.\n\nThe player can [[House Customization|customize]] the exterior of their Sun Haven [[Home Sweet Home|house]] by individually changing the roof, walls, door, windows, and patio. There are many styles available, and the player is not locked into a specific theme.\n\nOther items in the '''STYLE''' set include STYLE_MATCHES.""",
    ("Building", "House Customization", "Patio"): """The '''ITEM NAME''' is one of several [[House Customization/Patios|patios]] the player can choose to modify the base foundation of their house. Unlike other types of exterior customizations, the patio does not change appearance when the house is upgraded. It serves as a permanent stylistic choice that remains fixed regardless of the home's tier.\n\nThe player can [[House Customization|customize]] the exterior of their Sun Haven [[Home Sweet Home|house]] by individually changing the roof, walls, door, windows, and patio. There are many styles available, and the player is not locked into a specific theme.\n\nOther items in the '''STYLE''' set include STYLE_MATCHES.""",

    # EQUIPMENT > CLOTHING
    ("Equipment", "Clothing", "Skirt"): "'''ITEM NAME''' is a [[clothing]] item worn in the player's leg slot. Clothing items are purely cosmetic and do not provide any stats, unlike [[armor]], which grants bonuses when equipped. They are intended to be worn in the cosmetic slot, allowing the player to express their style and customize their appearance freely without impacting performance.",
    ("Equipment", "Clothing", "Pants"): "'''ITEM NAME''' is a [[clothing]] item worn in the player's leg slot. Clothing items are purely cosmetic and do not provide any stats, unlike [[armor]], which grants bonuses when equipped. They are intended to be worn in the cosmetic slot, allowing the player to express their style and customize their appearance freely without impacting performance.",
    ("Equipment", "Clothing", "Shorts"): "'''ITEM NAME''' is a [[clothing]] item worn in the player's leg slot. Clothing items are purely cosmetic and do not provide any stats, unlike [[armor]], which grants bonuses when equipped. They are intended to be worn in the cosmetic slot, allowing the player to express their style and customize their appearance freely without impacting performance.",
    ("Equipment", "Clothing", "Dress"): "'''ITEM NAME''' is a [[clothing]] item worn in the player's chest slot. Clothing items are purely cosmetic and do not provide any stats, unlike [[armor]], which grants bonuses when equipped. They are intended to be worn in the cosmetic slot, allowing the player to express their style and customize their appearance freely without impacting performance.",
    ("Equipment", "Clothing", "Shirt"): "'''ITEM NAME''' is a [[clothing]] item worn in the player's chest slot. Clothing items are purely cosmetic and do not provide any stats, unlike [[armor]], which grants bonuses when equipped. They are intended to be worn in the cosmetic slot, allowing the player to express their style and customize their appearance freely without impacting performance.",
    ("Equipment", "Clothing", "Gloves"): "'''ITEM NAME''' is a [[clothing]] item worn in the player's hand slot. Clothing items are purely cosmetic and do not provide any stats, unlike [[armor]], which grants bonuses when equipped. They are intended to be worn in the cosmetic slot, allowing the player to express their style and customize their appearance freely without impacting performance.",
    ("Equipment", "Clothing", "Wig"): "'''ITEM NAME''' is a [[clothing]] item worn on the player's head. Clothing items are purely cosmetic and do not provide any stats, unlike [[armor]], which grants bonuses when equipped. They are intended to be worn in the cosmetic slot, allowing the player to express their style and customize their appearance freely without impacting performance.",
    ("Equipment", "Clothing", "Hat"): "'''ITEM NAME''' is a [[clothing]] item worn in the player's head slot. Clothing items are purely cosmetic and do not provide any stats, unlike [[armor]], which grants bonuses when equipped. They are intended to be worn in the cosmetic slot, allowing the player to express their style and customize their appearance freely without impacting performance.",
    ("Equipment", "Clothing", "Cape"): "'''ITEM NAME''' is a [[clothing]] item worn in the player's back slot. Clothing items are purely cosmetic and do not provide any stats, unlike [[armor]], which grants bonuses when equipped. They are intended to be worn in the cosmetic slot, allowing the player to express their style and customize their appearance freely without impacting performance.",
    
    # EQUIPMENT > ARMOR
    ("Equipment", "Armor", "Helmet"): "The '''ITEM NAME''' is an armor item worn in the player's head slot. Unlike [[clothing]], armor provides stat bonuses when equipped. If the player prefers the appearance of a particular armor piece but has stronger gear, it can be placed in a cosmetic slot; however, doing so will not grant any of its stat bonuses. Some armor pieces belong to [[armor sets|sets]], which can activate the ''[[uniformity]]'' bonus when all set pieces are equipped in their main equipment slots. This bonus can increase the player's damage dealt by up to 10%.",
    ("Equipment", "Armor", "Chest"): "The '''ITEM NAME''' is an armor item worn in the player's chest slot. Unlike [[clothing]], armor provides stat bonuses when equipped. If the player prefers the appearance of a particular armor piece but has stronger gear, it can be placed in a cosmetic slot; however, doing so will not grant any of its stat bonuses. Some armor pieces belong to [[armor sets|sets]], which can activate the ''[[uniformity]]'' bonus when all set pieces are equipped in their main equipment slots. This bonus can increase the player's damage dealt by up to 10%.",
    ("Equipment", "Armor", "Gloves"): "The '''ITEM NAME''' is an armor item worn in the player's hand slot. Unlike [[clothing]], armor provides stat bonuses when equipped. If the player prefers the appearance of a particular armor piece but has stronger gear, it can be placed in a cosmetic slot; however, doing so will not grant any of its stat bonuses. Some armor pieces belong to [[armor sets|sets]], which can activate the ''[[uniformity]]'' bonus when all set pieces are equipped in their main equipment slots. This bonus can increase the player's damage dealt by up to 10%.",
    ("Equipment", "Armor", "Legs"): "The '''ITEM NAME''' is an armor item worn in the player's leg slot. Unlike [[clothing]], armor provides stat bonuses when equipped. If the player prefers the appearance of a particular armor piece but has stronger gear, it can be placed in a cosmetic slot; however, doing so will not grant any of its stat bonuses. Some armor pieces belong to [[armor sets|sets]], which can activate the ''[[uniformity]]'' bonus when all set pieces are equipped in their main equipment slots. This bonus can increase the player's damage dealt by up to 10%.",
    ("Equipment", "Armor", "Cape"): "The '''ITEM NAME''' is an armor item worn in the player's back slot. Unlike [[clothing]], armor provides stat bonuses when equipped. If the player prefers the appearance of a particular armor piece but has stronger gear, it can be placed in a cosmetic slot; however, doing so will not grant any of its stat bonuses. Some armor pieces belong to [[armor sets|sets]], which can activate the ''[[uniformity]]'' bonus when all set pieces are equipped in their main equipment slots. This bonus can increase the player's damage dealt by up to 10%.",

    # EQUIPMENT > ACCESSORY
    ("Equipment", "Accessory", "Ring"): "'''ITEM NAME''' is an [[Accessories|accessory]] item for the player's ring slot. The player is allowed to wear two rings at a time.",
    ("Equipment", "Accessory", "Amulet"): "'''ITEM NAME''' is an [[Accessories|accessory]] item for the player's amulet slot. Accessories do not belong to any set, thus this item does not receive any set bonuses from the ''[[Uniformity|uniformity skill]]''.",
    ("Equipment", "Accessory", "Keepsake"): "'''ITEM NAME''' is an [[Accessories|accessory]] item for the player's keepsake slot. Accessories do not belong to any set, thus it does not receive any set bonuses from the ''[[Uniformity|uniformity skill]]''.",
    
    # EQUIPMENT > TOOL
    ("Equipment", "Tool", "Axe"): "'''ITEM NAME''' is a tool used for chopping trees and stumps. While there is no specific axe level required, tougher trees such as [[hardwood]] and [[Elven Hardwood]] regenerate health over time. Players must either have a strong enough axe or collaborate with others to cut them down effectively.",
    ("Equipment", "Tool", "Pickaxe"): "'''ITEM NAME''' is a mining tool used to break rocks and ore. No specific strength is required to mine [[heavystone]] or [[Elven Heavystone]], but these materials regenerate health. Efficient mining requires a powerful pickaxe or cooperative play.",
    ("Equipment", "Tool", "Rod"): "'''ITEM NAME''' is a fishing rod used to catch fish across various regions. Fishing rods can include unique stat bonuses, offering benefits that may improve catch rates or provide other passive effects.",
    ("Equipment", "Tool", "Hoe"): "'''ITEM NAME''' is used to till soil, preparing land for seed planting. Each upgraded tier of the hoe increases the speed and efficiency of tilling.",
    ("Equipment", "Tool", "Watering Can"): "'''ITEM NAME''' is used to water [[crops]]. As the player upgrades their watering can, its water capacity and speed improve, allowing for faster and more efficient crop maintenance.",
    ("Equipment", "Tool", "Net"): "'''ITEM NAME''' is a passive fishing tool used on the [[Sun Haven Farm]]. Nets can be placed in ponds, rivers, or oceans and automatically collect fish once daily. Their effectiveness depends on placement, and the fish vary by location. Players must purchase fishing permits from [[Peter's Fishing Store]] to increase their net capacity, with each world only allowing one permit per tier.",
    ("Equipment", "Tool", "Scythe"): "'''ITEM NAME''' is a tool typically used to harvest crops or clear debris. It helps maintain farmland by quickly removing weeds and other obstacles.",

    # EQUIPMENT > WEAPON
    ("Equipment", "Weapon", "Sword"): "The '''ITEM NAME''' is a balanced and versatile weapon favored by warriors for its speed and control.",
    ("Equipment", "Weapon", "Crossbow"): "The '''ITEM NAME''' is a mechanical ranged weapon that fires bolts with deadly precision and force. Equipped with an automatic loading system, it unleashes rapid consecutive shots making it ideal for sustained ranged combat, especially when mobility matters.",
    ("Equipment", "Weapon", "Staff"): "The '''ITEM NAME''' is a conduit of magical power, the staff channels arcane energy into potent ranged attacks and spell effects.",
    ("Equipment", "Weapon", "Great Sword"): "The '''ITEM NAME''' is a massive two-handed weapon known for its overwhelming power and wide sweeping attacks. While slow to swing, the great sword delivers devastating blows but requires careful timing and positioning due to its slower attack speed and longer recovery frames. Ideal for players who favor strength and precision over speed and agility.",
    ("Equipment", "Weapon", "Hammer"): "The '''ITEM NAME''' is acolossal blunt weapon designed to crush armor and shatter defenses. The two-handed hammer delivers slow but immensely powerful strikes, capable of staggering even the toughest foes. Its weight and momentum make each swing feel impactful, often knocking enemies off balance or breaking through shields. While it lacks finesse and speed, it makes up for it with sheer force and battlefield presence.",

    # FURNITURE
    ("Furniture", "Bed", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. This item cannot be rotated and must always be facing front. The majority of furniture items serve no purpose aside from allowing the player to customize the aesthetic of their farm and housing; however, [[Furniture/Beds|beds]] are used to progress the player to the next day. If the player does not fall asleep in a bed before the clock strikes midnight, the player will faint from exhaustion. Fainting costs the player money and forces the next day upon them.\n\nThe bed cannot be used to skip the entire day, however, as the earliest the player can go to bed is 06:00 PM. Attempting to interact with the bed at any earlier time displays the message \"It is too early to sleep!\"\n\n[[Furniture]] items can be placed within the boundaries of the player character's farm; whether indoors, outdoors, or both. The player can pick up furniture items by hitting them with a [[pickaxe]].",
    ("Furniture", "Nightstand", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. [[Furniture/Surfaces#End Tables|End tables]] (also called nightstands) are a type of furniture item that allow smaller items to be placed on top of them for decoration. They are generally smaller than tables and are often found next to couches or beds. Most furniture serves no functional purpose and is intended purely for aesthetics, allowing the player to personalize their home and farm. Furniture can be placed either outdoors on the farm or inside any of the player's buildings. Some furniture must be placed directly on the floor, while smaller items can also be placed on surfaces like tables or countertops. Wall-mounted furniture must be placed indoors. To pick up furniture, the player can strike the item with a [[pickaxe]].",
    ("Furniture", "Bridge", ""): "'''ITEM NAME''' is a one-time-use furniture item used to alter the appearance of the bridge on the [[Sun Haven Farm]]. Once placed, it replaces the current bridge design and cannot be reused like wallpaper.",
    ("Furniture", "Bookcase", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. [[Furniture/Decoration#Bookcases|Bookcases]] are decorative shelves for display only—the player cannot store books on them. Most furniture serves no functional purpose and is intended purely for aesthetics, allowing the player to personalize their home and farm. Furniture can be placed either outdoors on the farm or inside any of the player's buildings. Some furniture must be placed directly on the floor, while smaller items can also be placed on surfaces like tables or countertops. Wall-mounted furniture must be placed indoors. To pick up furniture, the player can strike the item with a [[pickaxe]].",
    ("Furniture", "Couch", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. [[Furniture/Seating#Couches|Couches]] are decorative and cannot be sat on. Most furniture serves no functional purpose and is intended purely for aesthetics, allowing the player to personalize their home and farm. Furniture can be placed either outdoors on the farm or inside any of the player's buildings. Some furniture must be placed directly on the floor, while smaller items can also be placed on surfaces like tables or countertops. Wall-mounted furniture must be placed indoors. To pick up furniture, the player can strike the item with a [[pickaxe]].",
    ("Furniture", "Chair", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the player's house or on their farm. Chairs are decorative and the player cannot sit on any chair, couch, or stool. Most furniture serves no functional purpose and is intended purely for aesthetics, allowing the player to personalize their home and farm. Furniture can be placed either outdoors on the farm or inside any of the player's buildings. Some furniture must be placed directly on the floor, while smaller items can also be placed on surfaces like tables or countertops. Wall-mounted furniture must be placed indoors. To pick up furniture, the player can strike the item with a [[pickaxe]].",
    ("Furniture", "Chest", ""): "'''ITEM NAME''' is a storage item with 30 inventory slots. It cannot be rotated and must face forward. Players can name and recolor the chest, and it functions similarly to [[Furniture/Storage#Refrigerators|refrigerators]] and [[Furniture/Storage#Wardrobes|wardrobes]].",
    ("Furniture", "Fireplace", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor of the player's house or farm. It cannot be rotated and must always face front. [[Furniture/Lighting#Fireplaces|Fireplaces]] are decorative items that provide a little light. Most furniture serves no functional purpose and is intended purely for aesthetics, allowing the player to personalize their home and farm. Furniture can be placed either outdoors on the farm or inside any of the player's buildings. Some furniture must be placed directly on the floor, while smaller items can also be placed on surfaces like tables or countertops. Wall-mounted furniture must be placed indoors. To pick up furniture, the player can strike the item with a [[pickaxe]].",
    ("Furniture", "Lighting", ""): "'''ITEM NAME''' is a decorative lighting item. When placed, it automatically turns on at night and emits light in its surroundings.",
    ("Furniture", "Plushie", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor of the player's house or farm, or on top of surfaces like shelves and tables. It cannot be rotated and must always face front. [[Furniture/Plushies|Plushies]] are toys covered in plush fabric and filled with soft material. Like other plushies in Sun Haven, this item is purely cosmetic and cannot be interacted with. Most furniture serves no functional purpose and is intended purely for aesthetics, allowing the player to personalize their home and farm. Furniture can be placed either outdoors on the farm or inside any of the player's buildings. Wall-mounted furniture must be placed indoors. To pick up furniture, the player can strike the item with a [[pickaxe]].",
    ("Furniture", "Rug", ""): "'''ITEM NAME''' is a decorative [[Furniture/Rugs|rug]] that can be placed on the floor in the player's house or on their farm. Like most furniture, rugs serve no functional purpose and are purely aesthetic, allowing the player to personalize their space. Furniture can be placed either outdoors on the farm or inside any of the player's buildings. Some pieces must be placed directly on the floor, while others can also sit atop tables or countertops. Wall-mounted items must be placed indoors. To pick up furniture, the player can strike the item with a [[pickaxe]].",
    ("Furniture", "Table", ""): "'''ITEM NAME''' is a surface furniture piece. [[Furniture/Surfaces#Tables|Tables]] allow smaller decorative items to be placed on top, making them ideal for interior design.",
    ("Furniture", "Tile", ""): "[[Tile Maker#Item Showcase|Tiles]] prevent trees from spawning on them and come in batches of 10. Investing in the [[Architect]] skill improves [[Movement Speed]] while walking on these tiles.",
    ("Furniture", "Wallpaper", ""): "'''ITEM NAME''' is a wallpaper item used to decorate interior walls. Wallpaper can be reused multiple times and must be equipped to change wall appearances. It only functions indoors.",
    ("Furniture", "Flooring", ""): "'''ITEM NAME''' is a flooring item used to decorate interior floors. Flooring can be reused multiple times and must be equipped to change floor appearances. It only functions indoors.",
    ("Furniture", "Wardrobe", ""): "'''ITEM NAME''' is a storage item placed on the floor. [[Furniture/Storage#Wardrobes|Wardrobes]] work similarly to chests and provide additional organization options.",
    ("Furniture", "Window", ""): "'''ITEM NAME''' is a window that changes appearance based on the time of day. It must be placed indoors and always faces forward. Players' homes come with two default windows that can be relocated with a [[pickaxe]].",
    ("Furniture", "Selling Portal", ""): "'''ITEM NAME''' is a piece of furniture that can be placed on the floor in the players house or on their farm. This item cannot be rotated and must always be facing front. [[Selling Portals|Selling portals]] are furniture items that allow the player to ship various things for currency. Each selling portal has a max number of items that can be shipped per day, if the player places additional selling portals on their farm(s), they are able to ship more items from the different portals. The player will receive their money during the transition of to the next day.\"\n\n[[Furniture]] items can be placed within the boundaries of the player characters farm; whether indoors, outdoors, or both. Items that require a wall, can only be placed indoors. The player can pick up furniture items by hitting them with a [[pickaxe]]. ",
    ("Furniture", "", ""): "'''ITEM NAME''' is a piece of furniture.\n\nAll [[furniture]] items can be placed within the boundaries of the player character's farm. Items placed on the floor or surfaces can be indoors or outdoors, but items placed on a wall must be inside a building. The player can pick up furniture items by hitting them with a [[pickaxe]].",

    # ANIMAL > PET
    ("Animal", "Pet", ""): "'''ITEM NAME''' is a ''RARITY'' companion creature. Pets can be placed on the player's farm or follow the player via a [[Pet Leash|pet leash]]. They are non-combat companions and cannot take damage.\n\nWith the ''[[Zookeeper]]'' skill, pets on the farm generate gold daily. With ''[[Promenade]]'', leashed pets grant movement speed boosts and exploration experience every in-game hour.",

    # FISH
    ("Fish", "", ""): "'''ITEM NAME''' is an ''RARITY'' type of fish which can be caught SEASONAL LINE. {{Bonding experience|EXPERIENCE}}\n\n{{Fishing skill price calculations|SELL|SELLTYPE}}",

    # MOUNT
    ("Item", "Mount", ""): "'''ITEM NAME''' is an item that when used calls a mount for the player to ride upon. There are various [[skills]] the player can earn to increase the speed of the mount, and actions available while on the mount. All mounts benefit from these skills, which means all mounts will move at the same speed, and the skin of the mount is purely cosmetic.",

    # RECORD
    ("Record", "", ""): "The '''ITEM NAME''' is a purchasable [[records|record]] that can be played on a [[Record Player|record player]]. To activate the music, the player must interact with the record player while holding a record in their hand. The music will then begin to play throughout the area. When the track ends, it will start over in a loop. The record will '''not''' be consumed if the player changes the music and can be used again an infinite number of times.\n\n'''Music Sample'''\n[[file:ITEM NAME.ogg]]",
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
    pattern = re.compile(r'^\s*\|\s*([^=]+?)\s*=\s*(.*)')
    computed = {}
    for line in infobox.splitlines():
        match = pattern.match(line)
        if match:
            key, value = match.groups()
            # Strip both spaces and any trailing '}' from the value
            value = value.strip().rstrip("}").strip()
            computed[key.strip().lower()] = value
    return computed

def custom_title(text):
    """
    Title-case a string without capitalizing letters after an apostrophe.
    For example, "xyla's plushie" becomes "Xyla's Plushie".
    """
    words = text.split()
    new_words = []
    for word in words:
        if "'" in word:
            parts = word.split("'", 1)
            # Capitalize the first part and leave the rest as is.
            new_word = parts[0].capitalize() + "'" + parts[1]
        else:
            new_word = word.capitalize()
        new_words.append(new_word)
    return " ".join(new_words)

def create_item_summary(item, computed, display_name=None):
    """
    Generate and return a summary string for the given item using the summary template
    and the computed values parsed from the infobox.
    """
    itemType, subtype, category = classify_item(item)
    key = normalize_classification(itemType, subtype, category)
    summary_template = SUMMARIES.get(key, "No summary available for this item. [[Category:Missing summary]]")

    if display_name is None:
        display_name = item.get("name", "ITEM NAME")
    display_name = custom_title(display_name)
    summary = summary_template

    raw_rarity = computed.get("rarity", str(item.get("rarity", "rarity")))
    if raw_rarity.isdigit():
        rarity = constants.RARITY_TYPE_MAPPING.get(int(raw_rarity), raw_rarity)
    else:
        rarity = raw_rarity
    rarity = rarity.lower()
    summary = summary.replace("RARITY", rarity)

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
        currency = computed.get("currency", "CURRENCY")
        summary = summary.replace("CURRENCY", currency.lower())
        sell = computed.get("sell", "SELL")
        summary = summary.replace("SELL", sell)

    if itemType == "Building" and subtype == "House Customization":
        style_targets = ["Door", "Roof", "Walls", "Windows", "Patio"]
        name_words = display_name.split()
        for idx, word in enumerate(name_words):
            if word.capitalize() in style_targets:
                style = " ".join(name_words[:idx])
                item_type = word.capitalize()
                break
        else:
            style = name_words[0]
            item_type = "Unknown"

        style_matches = [f"[[{style} {target}]]" for target in style_targets if target != item_type]
        summary = summary.replace("STYLE", style).replace("STYLE_MATCHES", ", ".join(style_matches))

    if computed.get("dlc", "false").lower() == "true":
        extra_text = (
            f"{display_name} belongs to a [[Downloadable Content|DLC]] game pack. Once acquired, "
            "the set will be delivered to the player's mailbox. These items are delivered to every "
            "character on the player's steam account."
        )
        summary = summary.rstrip() + "\n\n" + extra_text.strip()

    summary = summary.replace("ITEM NAME", display_name)
    return summary