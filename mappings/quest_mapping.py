from formatter.quest_infobox import resolve_quest_type
from utils import text_utils

def extract_quest_context(quest: dict, npc: str = "", end_text: str = "") -> dict:
    return {
        "quest_type": resolve_quest_type(quest).lower(),
        "region": quest.get("region", "").strip(),
        "name": quest.get("questName", "Unnamed Quest"),
        "objective": text_utils.clean_text(quest.get("questDescription", "")),
        "description": text_utils.clean_text(quest.get("bulletinBoardDescription", "")),
        "npc": quest.get("npcToTurnInTo", ""),
        "end_text": text_utils.format_for_chat(quest.get("endTex", "")),
        "requires": quest.get("itemRequirementsFormatted", ""),
        "rewards": quest.get("guaranteeRewardsFormatted", ""),
        "bonus": quest.get("choiceRewardsFormatted", ""),
    }
