"""
Quest context extractor.

Converts a raw quest dict into a normalised context dict used when
building quest infoboxes and page sections.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from formatters.quest.quest_infobox import resolve_quest_type
from utils import text_utils


def extract_quest_context(quest: dict, npc: str = "", end_text: str = "") -> dict:
    """Return a normalised context dict derived from a raw quest record."""
    return {
        "quest_type": resolve_quest_type(quest).lower(),
        "region": quest.get("region", "").strip(),
        "name": quest.get("questName", "Unnamed Quest"),
        "objective": text_utils.clean_game_dialogue(quest.get("questDescription", "")),
        "description": text_utils.clean_game_dialogue(quest.get("bulletinBoardDescription", "")),
        "npc": quest.get("npcToTurnInTo", ""),
        "end_text": text_utils.format_for_chat(quest.get("endTex", "")),
        "requires": quest.get("itemRequirementsFormatted", ""),
        "rewards": quest.get("guaranteeRewardsFormatted", ""),
        "bonus": quest.get("choiceRewardsFormatted", ""),
    }
