ROOT_DIRECTORY = r"YOUR PATH/TO/Sun Haven Parser"
INPUT_DIRECTORY = r"YOUR PATH/TO/Sun Haven Parser/_input/x.x"
IMAGE_INPUT_DIRECTORY = r"YOUR PATH/TO/IMAGES/"
OUTPUT_DIRECTORY = r"YOUR PATH/TO/Sun Haven Parser/_output/x.x"
DEBUG_DIRECTORY = r"YOUR PATH/TO/Sun Haven Parser/.hidden/debug_output"

PWB_SETTINGS = {
    "BATCH_SIZE": 50,
    "SLEEP_INTERVAL": 8,
    "NULL_EDIT_SLEEP_INTERVAL": 10,
    "MAX_RETRIES": 5,
    "THROTTLE": 5,
    "USER_AGENT": "SH Wiki User (https://sunhaven.wiki.gg/wiki/User:YOURUSERNAMEHERE)",
}

ADDITIONAL_PATHS = {
    "PWB": r"YOUR PATH/TO/PWB"
}

STAT_TYPE_MAPPING = {
    0: "Health",
    1: "Mana",
    2: "Attack Damage",
    3: "Attack Speed",
    4: "Health Regen",
    5: "Mana Regen",
    6: "Movespeed",
    7: "Jump Height",
    8: "Spell Damage",
    9: "Melee Lifesteal",
    10: "Ranged LifeSteal",
    11: "Movespeed On Hit",
    12: "Movespeed On Kill",
    13: "Health On Kill",
    14: "Crit",
    15: "Damage Reduction",
    16: "Gold Gain",
    17: "Knockback",
    18: "Stun Duration",
    19: "Size",
    20: "Fishing Skill",
    21: "Mining Skill",
    22: "Exploration Skill",
    23: "Defense",
    24: "Flat Damage",
    25: "RomanceBonus",
    26: "Money Per Day",
    27: "Bonus Combat EXP",
    28: "Bonus Woodcutting EXP",
    29: "Bonus Fishing EXP",
    30: "Bonus Mining EXP",
    31: "Bonus Crafting EXP",
    32: "Bonus Farming EXP",
    33: "Stun Chance",
    34: "Accuracy",
    35: "Farming Skill",
    36: "Gold Per Craft",
    37: "Mining Crit",
    38: "Woodcutting Crit",
    39: "Smithing Skill",
    40: "Bonus Experience",
    41: "Spell Power",
    42: "Sword Power",
    43: "Crossbow Power",
    44: "Crit Damage",
    45: "Dodge",
    46: "Free Air Skip Chance",
    47: "Fishing Minigame Speed",
    48: "Fish Bobber Attraction",
    49: "Enemy Gold Drop",
    50: "Extra Forageable Chance",
    51: "Bonus Tree Damage",
    52: "Mining Damage",
    53: "Fall Damage Reduction",
    54: "Movement Speed After Rock",
    55: "Fruit Mana Restore",
    56: "Spell Attack Speed",
    57: "Power",
    58: "Woodcutting Damage",
    59: "Community Token Per Day",
    60: "Tickets Per Day",
    61: "Triple Gold Chance",
    62: "Pickup Range",
    63: "Extra Crop Chance",
    64: "Fishing Win Area",
    65: "Fishing Sweet Spot Area",
    66: "Mana Per Craft",
    67: "Black Gem Drop Chance",
    68: "Crafting Speed",
    999: "none",
}

FOOD_STAT_INCREASES = {
    0: "Very Small",
    1: "Small",
    2: "Moderate",
    3: "Large",
    4: "Huge"
}

SEASONS = {
    0: "Spring",
    1: "Summer",
    2: "Fall",
    3: "Winter",
}

QUEST_TYPES = {
    0: "Bulletin Board",
    1: "Character Quest",
    2: "Sun Haven Main Quest",
    3: "Withergate Main Quest",
    4: "Nel'Vari Main Quest",
    8: "Brinestone Deep Main Quest",
}

RARITY_TYPE_MAPPING = {
    0: "Common",
    1: "Uncommon",
    2: "Rare",
    3: "Epic",
    4: "Legendary",
}