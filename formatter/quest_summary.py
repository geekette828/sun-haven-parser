import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import textwrap
from formatter.quest_infobox import resolve_quest_type
from utils import text_utils

def create_quest_summary(quest, npc="", bulletin="", end_text=""):
    quest_type = resolve_quest_type(quest).lower()
    region = quest.get("region", "").strip()
    name = quest.get("questName", "Unnamed Quest")
    objective = text_utils.clean_text(quest.get("questDescription", ""))
    description = text_utils.clean_text(quest.get("bulletinBoardDescription", ""))
    chat = f"{{{{Chat|{npc}|{end_text}}}}}"

    if "romance" in quest_type:
        return textwrap.dedent(f"""\

        '''{name}''' is a unique date quest that becomes available after the player completes {npc}'s <specific conversation cycle>. Once the player has asked {npc} on a date, this special event can be triggered at <location> between <time> and <1 hour later>. The player must speak to {npc} within that one-hour window to begin the date. If the player misses the opportunity, the event is permanently unavailable and cannot be triggered again.

        Although this event is technically classified as a quest, it does not offer any experience or item rewards. Instead, it serves as a one-time, story-rich interaction that deepens the relationship between the player and {npc}. The full dialogue and scene details for this event can be found on the [[{npc}/Events\\events]] page.
        """)

    elif quest_type in ["bulletin", "bulletin board"]:
        region_map = {
            "nel'vari": "[[Nel'Vari Bulletin Board|Nel'Vari bulletin board]]",
            "withergate": "[[Withergate Bulletin Board|Withergate bulletin board]]",
            "brinestone deeps": "[[Brinestone_Deeps_Bulletin_Board|Brinestone Deeps bulletin board]]",
        }
        board_location = region_map.get(region.lower(), "[[Sun Haven Bulletin Board|Sun Haven bulletin board]]")

        return f"'''{name}''' is a [[Quests|quest]] that has the chance to be available at the {board_location}. The objective of this quest is to {objective}."

    elif quest_type == "character":
        return f"'''{name}''' is a [[Quests#Character Quests|character quest]] that can become available after the player marries [[{npc}]]."

    elif "main" in quest_type:
        return f"'''{name}''' is part of the [[Main Quests]] storyline."

    return f"'''{name}''' is a [[Quests|quest]] in the game. [[Category:Missing quest category]]."
