import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import textwrap
from utils import text_utils
from mappings.quest_mapping import extract_quest_context

def create_quest_overview_box(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    return textwrap.dedent(f"""\
        ==Overview==
        {{{{Quest overview
        |requires = {ctx['requires']}
        |rewards  = {ctx['rewards']}
        |bonus    = {ctx['bonus']} }}}}
    """)

def create_quest_overview_steps_box(quest: dict) -> str:
    return textwrap.dedent(f"""\
        ==Overview==
        {{Quest overview/steps
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
        |3_bonus    = }}
    """)

def create_quest_step_list(quest: dict) -> str:
    return textwrap.dedent(f"""\
        ===Steps===
        # Accept quest
        # 
    """)

def create_quest_bb_description(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    return textwrap.dedent(f"""\
        ==Bulletin Board Description==
        {ctx['description']}
    """)

def create_quest_description(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    return textwrap.dedent(f"""\
        ==Description==
        The in-game description of this quest:
        {{{{OneLiner|{ctx['objective']}}}}}
    """)

def create_quest_complete_text(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    return textwrap.dedent(f"""\
        ==Quest Complete Text== 
        Upon turning in this quest, {ctx['npc']} will say:
        {{{{Chat|{ctx['npc']}|{ctx['end_text']} }}}}
    """)

def create_quest_dialogue(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    return textwrap.dedent(f"""\
        ==Dialogue==
        ===Pre-Quest===
        {{{{Conversation Dialogue|{ctx['npc']}|{ctx['name']}}}}}

        ===Post-Quest===
        {{{{Chat|{ctx['npc']}|{ctx['end_text']} }}}}
    """)

def create_quest_walkthrough(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    return textwrap.dedent(f"""\
        ==Walkthrough==
        ===Step 1 Name===
        {{{{Main quest section|questStep=|requires={ctx['requires']}|rewards={ctx['rewards']}|bonus={ctx['bonus']} }}}}

        ===Step 2 Name===
        {{{{Main quest section|questStep=|requires=|rewards=|bonus= }}}}

        ===Step 3 Name===
    """)

def create_hidden_block(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    return textwrap.dedent(f"""\
        <!--
        ==Media==
        <gallery widths="200" bordercolor="transparent" spacing="small" captionalign="center">
        File:filename.png|File Description
        </gallery>

        ==Trivia==
        *

        ==History==
        *{{{{History|x.x.x|description for {ctx['name']}}}}}-->
    """)
