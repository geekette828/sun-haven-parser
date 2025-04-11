def classify_item(item):
    """
    Given an item dictionary, returns a tuple (itemType, subtype, category)
    based on the following rules.

    Animal classification (highest priority):
      - If useDescription is exactly:
          "\"(Grab a leash to have them follow you!)\\n(Left click at house or farm to place)\""
          then itemType = "Animal", subtype = "Pet", category = "".
      - If useDescription is exactly "(Left click at farm to place)" and description is not empty,
          then itemType = "Animal", subtype = "Barn Animal", category = "".
      - If useDescription is exactly "(Left click at farm to place)" and description is empty,
          then itemType = "Animal", subtype = "Wild Animal", category = "".

    Weapon classification:
      - If the item name contains "sword" and useDescription is exactly "(Left click to swing)",
          then itemType = "Equipment", subtype = "Weapon", category = "Sword".
      - If the item name contains "crossbow" and useDescription is exactly "(Left click to fire)",
          then itemType = "Equipment", subtype = "Weapon", category = "Crossbow".
      - If the item name contains "staff" or "staves" and the description includes
          "when selected on your toolbelt, this staff grants" (case-insensitive),
          then itemType = "Equipment", subtype = "Weapon", category = "Staff".

    Tool classification:
      - If the item name contains "axe" and useDescription is exactly "(Left click on trees to use)",
          then itemType = "Equipment", subtype = "Tool", category = "Axe".
      - If the item name contains "pickaxe" and useDescription is exactly "(Left click on a rock or decoration to use)",
          then itemType = "Equipment", subtype = "Tool", category = "Pickaxe".
      - If useDescription is exactly "(Press left click and hold to cast your line)",
          then itemType = "Equipment", subtype = "Tool", category = "Rod".
      - If useDescription is exactly "\"(Left click to hoe)\\n(Right click to unhoe)\"",
          then itemType = "Equipment", subtype = "Tool", category = "Hoe".
      - If useDescription is exactly "\"(Left click on tilled dirt to water)\\n(Left click on water to refill)\"",
          then itemType = "Equipment", subtype = "Tool", category = "Watering Can".
      - If the item name contains "fishing net",
          then itemType = "Equipment", subtype = "Tool", category = "Net".
      - If the item name contains "scythe" and useDescription is exactly "(Left click to swing)",
          then itemType = "Equipment", subtype = "Tool", category = "Scythe".
    
    Forageable classification:
      - If isForageable is 1:
            * If foodStat is empty → itemType = "Forageables", subtype = "Resources", category = "".
            * If foodStat is non-empty → itemType = "Forageables", subtype = "Food", category = "".
    
    Fish classification:
      - If hasSetSeason is not None and foodStat is non-empty,
          then itemType = "Fish", subtype = "", category = "".
    
    Consumable Food classification:
      - If isPotion is 0, isForageable is 0, and foodStat is non-empty,
          then itemType = "Consumable", subtype = "Food", category = "".
    
    Furniture classification:
      - If useDescription is exactly "(Left click to place)":
          then itemType = "Furniture" and subtype is determined by key phrases in the name.
          (For example, if name contains "end table" or "nightstand", subtype = "Nightstand"; if "bed", then "Bed"; etc.)
          Category remains blank.
    
    Equipment fallback classification:
      For items that do not match any of the above:
      - If stats is non-empty (apply accessory then Armor rules):
          * If the name contains "ring", then return "Equipment", "Accessory", "Ring".
          * Else if the name contains "amulet", then return "Equipment", "Accessory", "Amulet".
          * Else if the name contains "keepsake", then return "Equipment", "Accessory", "Keepsake".
          * Else if name contains "helmet", then return "Equipment", "Armor", "Helmet".
          * Else if name contains any of "robe", "chest", "chestplate", "chest plate", then return "Equipment", "Armor", "Chest".
          * Else if name contains any of "gloves", "gauntlets", then return "Equipment", "Armor", "Gloves".
          * Else if name contains any of "leg", "legs", "shoes", "pants", then return "Equipment", "Armor", "Legs".
          * Else if name contains any of "cape", "wings", "back", then return "Equipment", "Armor", "Cape".
      - If stats is empty, apply Clothing rules:
          * If name contains any of "hat", "crown", "headband", "headphones", "hood", "goggles", "tiara", "helmet", then return "Equipment", "Clothing", "Hat".
          * Else if name contains "wig", then return "Equipment", "Clothing", "Wig".
          * Else if name contains "dress" or "robe", then return "Equipment", "Clothing", "Dress".
          * Else if name contains any of "chest", "chestplate", "chest plate", "shirt", "tank top", "hoodie", "jacket", "crop top", "sweater", "torso", "costume", "outfit", "vest", "coat", "tee", "t-shirt", then return "Equipment", "Clothing", "Shirt".
          * Else if name contains any of "gloves", "gauntlets", then return "Equipment", "Clothing", "Gloves".
          * Else if name contains "cape", then return "Equipment", "Clothing", "Cape".
          * Else if name contains any of "pants", "slacks", "shoes", "boots", "greaves", then return "Equipment", "Clothing", "Pants".
          * Else if name contains "shorts", then return "Equipment", "Clothing", "Shorts".
          * Else if name contains any of "skirt", "skirts", then return "Equipment", "Clothing", "Skirt".
    
    If no rule applies, returns empty strings.
    """
    use_desc = item.get("useDescription", "")
    desc = item.get("description", "")
    stats = item.get("stats", [])
    name = item.get("Name", "").lower()
    foodStat = item.get("foodStat", [])
    isForageable = item.get("isForageable", 0)
    isPotion = item.get("isPotion", 0)
    hasSetSeason = item.get("hasSetSeason")

    # 1. Animal classification.
    if use_desc == "\"(Grab a leash to have them follow you!)\\n(Left click at house or farm to place)\"":
        return "Animal", "Pet", ""
    elif use_desc == "(Left click at farm to place)":
        if desc and desc.strip():
            return "Animal", "Barn Animal", ""
        else:
            return "Animal", "Wild Animal", ""
    
    # 2. Weapon classification.
    if "sword" in name and use_desc == "(Left click to swing)":
        return "Equipment", "Weapon", "Sword"
    if "crossbow" in name and use_desc == "(Left click to fire)":
        return "Equipment", "Weapon", "Crossbow"
    if ("staff" in name or "staves" in name) and desc and "when selected on your toolbelt, this staff grants" in desc.lower():
        return "Equipment", "Weapon", "Staff"
    
    # 3. Tool classification.
    if "axe" in name and use_desc == "(Left click on trees to use)":
        return "Equipment", "Tool", "Axe"
    if "pickaxe" in name and use_desc == "(Left click on a rock or decoration to use)":
        return "Equipment", "Tool", "Pickaxe"
    if use_desc == "(Press left click and hold to cast your line)":
        return "Equipment", "Tool", "Rod"
    if use_desc == "\"(Left click to hoe)\\n(Right click to unhoe)\"":
        return "Equipment", "Tool", "Hoe"
    if use_desc == "\"(Left click on tilled dirt to water)\\n(Left click on water to refill)\"":
        return "Equipment", "Tool", "Watering Can"
    if "fishing net" in name:
        return "Equipment", "Tool", "Net"
    if "scythe" in name and use_desc == "(Left click to swing)":
        return "Equipment", "Tool", "Scythe"
    
    # 4. Forageable classification.
    if isForageable == 1:
        if not foodStat:
            return "Forageables", "Resources", ""
        else:
            return "Forageables", "Food", ""
    
    # 5. Fish classification.
    if hasSetSeason is not None and foodStat:
        return "Fish", "", ""
    
    # 6. Consumable Food classification.
    if isPotion == 0 and isForageable == 0 and foodStat:
        return "Consumable", "Food", ""
    
    # 7. Record classification.
    if use_desc == "(Use on record player to play)":
        return "Record", "", ""
    
    # 8. Mount classification.
    if use_desc == "(Left click to summon/unsummon mount)":
        return "Mount", "", ""

    # 9. Flooring
    if use_desc == "(Left click to place path on farm)":
        return "Furniture", "Tile", ""

    # 10. Wallpaper
    if use_desc == "(Use on a wall to place)":
        return "Furniture", "Wallpaper", ""
    
    # 11. Other Furniture classification.
    if use_desc == "(Left click to place)":
        name = name.lower() 
        if "end table" in name or "nightstand" in name or "night stand" in name:
            return "Furniture", "Nightstand", ""
        if "bed" in name:
            return "Furniture", "Bed", ""
        if "bridge" in name:
            return "Furniture", "Bridge", ""
        if "bookcase" in name:
            return "Furniture", "Bookcase", ""
        if "couch" in name:
            return "Furniture", "Couch", ""
        if any(keyword in name for keyword in ["chair", "floor cushion", "stool"]):
            return "Furniture", "Chair", ""
        if "chest" in name:
            return "Furniture", "Chest", ""
        if "fireplace" in name:
            return "Furniture", "Fireplace", ""
        if "painting" in name:
            return "Furniture", "Painting", ""
        if any(keyword in name for keyword in ["statue", "sculpture", "model", "column"]):
            return "Furniture", "Statue", ""
        if any(keyword in name for keyword in ["plant", "tree", "vase", "cactus", "flower", "seaweed", "bush", "leaf", "ivy"]):
            return "Furniture", "Plant", ""
        if any(keyword in name for keyword in ["light", "lamp", "lantern", "candle", "candelabra"]):
            return "Furniture", "Lighting", ""
        if any(keyword in name for keyword in ["plushie", "plush"]):
            return "Furniture", "Plushie", ""
        if any(keyword in name for keyword in ["rug", "mat", "doormat"]):
            return "Furniture", "Rug", ""
        if "table" in name:
            return "Furniture", "Table", ""
        if any(keyword in name for keyword in ["wardrobe", "dresser"]):
            return "Furniture", "Wardrobe", ""
        if any(keyword in name for keyword in ["window", "windows"]):
            return "Furniture", "Window", ""
        return "Furniture", "Misc", ""
    
    # 10. Equipment fallback classification.
    # First, if stats is non-empty, check for Accessory rules.
    if stats:
        if "ring" in name:
            return "Equipment", "Accessory", "Ring"
        if "amulet" in name:
            return "Equipment", "Accessory", "Amulet"
        if "keepsake" in name:
            return "Equipment", "Accessory", "Keepsake"
        # Then proceed with Armor rules.
        if "helmet" in name:
            return "Equipment", "Armor", "Helmet"
        if any(keyword in name for keyword in ["robe", "chest", "chestplate", "chest plate"]):
            return "Equipment", "Armor", "Chest"
        if any(keyword in name for keyword in ["gloves", "gauntlets"]):
            return "Equipment", "Armor", "Gloves"
        if any(keyword in name for keyword in ["leg", "legs", "shoes", "pants"]):
            return "Equipment", "Armor", "Legs"
        if any(keyword in name for keyword in ["cape", "wings", "back"]):
            return "Equipment", "Armor", "Cape"
    else:
        # If stats is empty, apply Clothing rules.
        if any(keyword in name for keyword in ["hat", "crown", "headband", "headphones", "hood", "goggles", "tiara", "helmet", "head scarf", "beanie", "halo", "helm"]):
            return "Equipment", "Clothing", "Hat"
        if "wig" in name:
            return "Equipment", "Clothing", "Wig"
        if "dress" in name or "robe" in name:
            return "Equipment", "Clothing", "Dress"
        if any(keyword in name for keyword in ["chest", "kimono", "chestplate", "chest plate", "shirt", "tank top", "hoodie", "jacket", "crop top", "sweater", "torso", "costume", "outfit", "vest", "coat", "tee", "t-shirt", "blouse", "suit", "cover up"]):
            return "Equipment", "Clothing", "Shirt"
        if any(keyword in name for keyword in ["gloves", "gauntlets"]):
            return "Equipment", "Clothing", "Gloves"
        if any(keyword in name for keyword in ["cape", "wings", "tail"]):
            return "Equipment", "Clothing", "Cape"
        if any(keyword in name for keyword in ["pants", "slacks", "shoes", "boots", "greaves"]):
            return "Equipment", "Clothing", "Pants"
        if "shorts" in name:
            return "Equipment", "Clothing", "Shorts"
        if any(keyword in name for keyword in ["skirt", "skirts"]):
            return "Equipment", "Clothing", "Skirt"
    
    return "", "", ""
