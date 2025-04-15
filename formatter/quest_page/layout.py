import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import textwrap
from formatter.quest_page.infobox import resolve_quest_type
from utils import text_utils

def create_quest_layout(quest, npc="", bulletin="", end_text=""):
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
            <!--
            ==Media==
            <gallery widths="200" bordercolor="transparent" spacing="small" captionalign="center">
            File:filename.png|File Description
            </gallery>

            ==Trivia==

            ==History==
            *{{{{History|x.x.x|description here.}}}}-->
        """)

    elif quest_type in ["bulletin", "bulletin board"]:
        region_map = {
            "nel'vari": (
                "[[Nel'Vari]]",
                f"The quest '''{name}''' is a [[Quests|quest]] that has the chance to be available at the [[Nel'Vari Bulletin Board|Nel'Vari bulletin board]] anytime after a player has unlocked the Nel'Vari region. {objective}."
            ),
            "withergate": (
                "[[Withergate]]",
                f"The quest '''{name}''' is a [[Quests|quest]] that has the chance to be available at the [[Withergate Bulletin Board|Withergate bulletin board]] anytime after a player has unlocked the Withergate region. {objective}."
            ),
            "brinestone deeps": (
                "[[Brinestone Deeps]]",
                f"The quest '''{name}''' is a [[Quests|quest]] that has the chance to be available at the [[Brinestone_Deeps_Bulletin_Board|Brinestone Deeps bulletin board]] anytime after a player has unlocked the Brinestone Deeps region."
            )
        }

        location, intro = region_map.get(region.lower(), (
            "[[Sun Haven]]",
            f"The quest '''{name}''' is a [[Quests|quest]] that has the chance to be available at the [[Sun Haven Bulletin Board|Sun Haven bulletin board]]. The objective of this quest is to {objective}"
        ))

        requires = quest.get("itemRequirementsFormatted", "")
        rewards = quest.get("guaranteeRewardsFormatted", "")
        bonus = quest.get("choiceRewardsFormatted", "")

        return textwrap.dedent(f"""\
            {intro}

            The {region} bulletin board is located [...] Every day the bulletin board will have random tasks that the player can accept and complete in exchange for currency and experience. When a new quest is available, the bulletin board will have a red exclamation point floating above it. 

            {{{{Quest overview
            |requires = {requires}
            |rewards  = {rewards}
            |bonus    = {bonus} }}}}

            ===Steps===
            # Accept quest on bulletin board.
            # 

            ==Bulletin Board Description==
            {bulletin}

            ==Quest Complete Text== 
            Upon turning in this quest, the NPC will say:
            {chat}
            <!--
            ==Media==
            <gallery widths="200" bordercolor="transparent" spacing="small" captionalign="center">
            File:filename.png|File Description
            </gallery>

            ==Trivia==

            ==History==
            *{{{{History|x.x|description here.}}}}-->
        """)

    elif quest_type == "character":
        requires = quest.get("itemRequirementsFormatted", "")
        rewards = quest.get("guaranteeRewardsFormatted", "")
        bonus = quest.get("choiceRewardsFormatted", "")

        return textwrap.dedent(f"""\
            '''{name}''' is a [[Quests#Character Quests|character quest]] that has a chance to be available after the player has married [[{npc}]]. {npc} is requesting the player brings them {requires}. Buy it and deliver it to them.

            Each [[:Category:Romance candidates|romanceable NPC]] has a chance to give the player a certain character quest for one of their favorite items. These quests are only available once the NPC is married to the player. When these quests are available, the character will have a [[File:Quest.png|15px]] quest icon above their heads, first thing in the morning. Unlike many of the other character quests which have an unlimited time to complete, the time limit for all of the post-marriage quests is 2 days.

            ==Overview==
            {{{{Quest overview
            |requires = {requires}
            |rewards  = {rewards}
            |bonus    = {bonus} }}}}

            == Steps ==
            # Talk to {npc}.

            == Description ==
            The in-game description of this quest:
            {{{{OneLiner|{description}}}}}

            == Dialogue ==
            <!--===Pre-Quest===
            {{{{Conversation Dialogue|{npc}|{name}}}}}
            -->
            ===Post-Quest===
            {chat}
            <!--
            ==Media==
            <gallery widths="200" bordercolor="transparent" spacing="small" captionalign="center">
            File:FileName.png|Description
            </gallery>

            ==Trivia==

            == History ==
            * {{{{History|X.X|Quest added to the game.}}}}-->
        """)

    elif "main" in quest_type:
        return textwrap.dedent(f"""\
            <!-- Broad overview of this quest chain -->

            Main quests are a series of [[quests]] the player must accomplish in order to complete the core narrative of the game. These are quests that tell the adventure of the player and their journey, as they travel through the world of Sun Haven. These quests often have many steps to them, with each step having its own requirement to proceed to the next.

            ==Overview==
            {{{{Quest overview/steps
            |1_step     = Step 1
            |1_requires = 
            |1_rewards  = 
            |1_bonus    = 
            |2_step     = Step 2
            |2_requires = 
            |2_rewards  = 
            |2_bonus    = 
            |3_step     = Step 3
            |3_requires = 
            |3_rewards  = 
            |3_bonus    =  }}}}

            ===Steps===
            # 

            ==Walkthrough==
            ===Step 1 Name===
            {{{{Main quest section|questStep=|requires={objective}|rewards=|bonus= }}}}

            ===Step 2 Name===

            ===Step 3 Name===

            <!--
            ==Media==
            <gallery widths="200" bordercolor="transparent" spacing="small" captionalign="center">
            File:filename.png|File Description
            </gallery>

            ==Trivia==

            ==History==
            *{{{{History|x.x|Change goes here.}}}}-->
        """)

    else:
        return textwrap.dedent(f"""\
            '''{name}''' is a [[Quests|quest]] in the game. [[Category:Missing quest category]].

            <!--
            ==Media==
            <gallery widths="200" bordercolor="transparent" spacing="small" captionalign="center">
            File:filename.png|File Description
            </gallery>

            ==Trivia==

            ==History==
            *{{{{History|x.x|Change goes here.}}}}-->
            """)




