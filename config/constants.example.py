ROOT_DIRECTORY = r"YOUR PATH/TO/Sun Haven Parser"
INPUT_DIRECTORY = r"YOUR PATH/TO/Sun Haven Parser/_input/x.x"
IMAGE_INPUT_DIRECTORY = r"YOUR PATH/TO/IMAGES/"
OUTPUT_DIRECTORY = r"YOUR PATH/TO/Sun Haven Parser/_output/x.x"

PWB_SETTINGS = {
    "throttle": 5,
    "max_retries": 5,
    "retry_wait": 10,
    "user_agent": "SH Wiki User (https://sunhaven.wiki.gg/wiki/User:YOURUSERNAMEHERE)",
}

ADDITIONAL_PATHS = {
    "PWB": r"YOUR PATH/TO/PWB"
}

STAT_TYPE_MAPPING = {
    0: "Health",
    1: "Mana",
    2: "Strength",
    3: "Agility",
    4: "Health Regen",
    5: "Mana Regen",
    6: "Movement Speed",
    7: "Jump",
    8: "Spell Damage",
    9: "Melee Lifesteal",
    10: "Ranged LifeSteal",
    11: "Movement Speed On Hit",
    12: "Movement Speed On Kill",
    13: "Health On Kill",
    27: "Bonus Combat EXP",
    28: "Bonus Woodcutting EXP",
    29: "Bonus Fishing EXP",
    30: "Bonus Mining EXP",
    31: "Bonus Crafting EXP",
    32: "Bonus Farming EXP",
    33: "StunChance",
    34: "Accuracy",
    35: "FarmingSkill",
    36: "Gold Per Craft",
    37: "MiningSkill",
    38: "Gold Per Craft",
    39: "Woodcutting Damage",
    57: "Power",
    58: "Woodcutting Damage",
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