"""
Quest infobox formatter — Layer 2 of the pipeline.

Pure formatting functions for quest infobox wikitext.
Depends on the item builder cache (items_data.json) via _load_cache().

No file I/O — all functions return strings.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import config.constants as constants
from builders.item_builder import _load_cache
from utils import json_utils, text_utils

# ---------------------------------------------------------------------------
# Item lookup
# ---------------------------------------------------------------------------

def load_item_lookup() -> dict:
    """
    Build an item_id (str) → display_name lookup from the item builder cache.
    Hardcoded special IDs are always included.
    """
    hardcoded = {
        "60000": "Coins",
        "60001": "Orbs",
        "60002": "Tickets",
        "60004": "Farming EXP",
        "60005": "Exploration EXP",
        "60006": "Mining EXP",
        "60007": "Bonus Mana",
        "60008": "Combat EXP",
        "60009": "Fishing EXP",
        "18013": "Community Token",
    }

    path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
    if not os.path.exists(path):
        return hardcoded

    try:
        items = _load_cache()
        for item in items.values():
            hardcoded[str(item.item_id)] = item.name
    except Exception:
        pass

    return hardcoded

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_items(items_list: list, item_lookup: dict) -> str:
    if not items_list:
        return ""
    formatted = []
    for item in items_list:
        item_id = str(item.get("id", ""))
        amount = item.get("amount", 1)
        item_name = item_lookup.get(item_id, f"Unknown Item ({item_id})")
        formatted.append(f"{item_name}*{amount}")
    return "; ".join(formatted)


def resolve_quest_type(quest: dict) -> str:
    title = quest.get("quest_name", "")
    type_number = quest.get("quest_type")

    if "First Date With" in title or "Second Date With" in title:
        return "Romance"
    elif "Attend the" in title:
        return "Festival"
    elif isinstance(type_number, int):
        return constants.QUEST_TYPES.get(type_number, str(type_number))
    return str(type_number or "")


def create_quest_infobox(quest: dict, item_lookup: dict, next_lookup: dict) -> str:
    quest_name = quest.get("quest_name", "Unknown Quest")
    time_limit = quest.get("days_to_do", -1)
    time_str = "Unlimited" if time_limit == -1 else f"{time_limit} days"
    objective = text_utils.clean_game_dialogue(quest.get("quest_description", ""))
    npc = quest.get("npc_to_turn_in_to", "")

    next_quest = quest.get("next_quest", {})
    if isinstance(next_quest, dict):
        next_name = next_lookup.get(next_quest.get("guid", ""), next_quest.get("guid", "None"))
    else:
        next_name = next_quest or ""

    requires = format_items(quest.get("item_requirements", []), item_lookup)
    rewards  = format_items(quest.get("guarantee_rewards", []), item_lookup)
    bonus    = format_items(quest.get("choice_rewards", []), item_lookup)

    quest_type = resolve_quest_type(quest)

    return (
        f"{{{{Quest infobox\n"
        f"|title = {quest_name}\n"
        f"|objective = {objective}\n"
        f"|type = {quest_type}\n"
        f"|time = {time_str}\n"
        f"|npc = {npc}\n"
        f"|location = \n"
        f"|prereq = \n"
        f"<!-- Quest Requirements and Rewards -->\n"
        f"|requires = {requires}\n"
        f"|rewards = {rewards}\n"
        f"|bonus = {bonus}\n"
        f"<!-- Quest Chronology -->\n"
        f"|prev = \n"
        f"|next = {next_name} }}}}\n"
    )


def build_guid_lookup(quest_data: dict) -> dict:
    lookup = {}
    for quests in quest_data.values():
        for q in quests:
            if "guid" in q:
                lookup[q["guid"]] = q.get("quest_name", q["guid"])
    return lookup


def find_quests_by_names(quest_data: dict, test_names: list) -> list:
    normalized = {name.strip().lower() for name in test_names}
    matched = []
    seen = set()

    for quest_group in quest_data.values():
        for quest in quest_group:
            name = quest.get("quest_name", "").strip().lower()
            if name in normalized:
                sig = (
                    name,
                    quest.get("quest_description", "").strip(),
                    quest.get("npc_to_turn_in_to", "").strip(),
                )
                if sig not in seen:
                    matched.append(quest)
                    seen.add(sig)
    return matched
