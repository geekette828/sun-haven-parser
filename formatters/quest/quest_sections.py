"""
Quest section formatters — Layer 2 of the pipeline.

Pure formatting functions for quest page sections.
No file I/O — all functions return strings.
"""

from __future__ import annotations

import os
import sys
import textwrap

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import config.constants as constants
from formatters.quest.quest_infobox import load_item_lookup, format_items
from formatters.quest.quest_context import extract_quest_context

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_item_lookup(item_lookup):
    if item_lookup is not None:
        return item_lookup
    return load_item_lookup()


def _format_req_reward_bonus(quest: dict, item_lookup: dict) -> tuple[str, str, str]:
    requires = format_items(quest.get("item_requirements", []), item_lookup)
    rewards  = format_items(quest.get("guarantee_rewards", []), item_lookup)
    bonus    = format_items(quest.get("choice_rewards", []), item_lookup)
    return requires, rewards, bonus

# ---------------------------------------------------------------------------
# Section formatters
# ---------------------------------------------------------------------------

def create_quest_overview_box(quest: dict, item_lookup=None) -> str:
    item_lookup = _get_item_lookup(item_lookup)
    requires, rewards, bonus = _format_req_reward_bonus(quest, item_lookup)

    return textwrap.dedent(f"""\
        ==Overview==
        {{{{Quest overview
        |requires = {requires}
        |rewards = {rewards}
        |bonus = {bonus}
        }}}}
    """)


def create_quest_overview_steps_box(quest: dict, item_lookup=None) -> str:
    item_lookup = _get_item_lookup(item_lookup)
    requires, rewards, bonus = _format_req_reward_bonus(quest, item_lookup)

    return textwrap.dedent(f"""\
        ==Overview==
        {{{{Quest overview/steps
        |1_step = Step 1
        |1_requires = {requires}
        |1_rewards = {rewards}
        |1_bonus = {bonus}
        |2_step = Step 2
        |2_requires =
        |2_rewards =
        |2_bonus =
        |3_step = Step 3
        |3_requires =
        |3_rewards =
        |3_bonus =
        }}}}
    """)


def create_quest_step_list(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    step_list = (
        ctx.get("step_list")
        or ctx.get("steps_list")
        or ctx.get("steps")
        or ""
    )
    if isinstance(step_list, list):
        step_list = "\n".join(f"* {s}" for s in step_list if s)
    if step_list and not str(step_list).strip().startswith("*"):
        step_list = str(step_list).strip()

    return textwrap.dedent(f"""\
        ==Quest Steps==
        {step_list}
    """)


def create_quest_bb_description(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    return textwrap.dedent(f"""\
        ==Bulletin Board Description==
        {{{{BB quest description|tgc|{ctx['description']}}}}}
    """)


def create_quest_description(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    return textwrap.dedent(f"""\
        ==Description==
        The in-game description of this quest:
        {{{{OneLiner|{ctx.get('objective', '')}}}}}
    """)


def create_quest_complete_text(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    npc = ctx.get("npc", "")
    end_text = ctx.get("end_text", "")
    return textwrap.dedent(f"""\
        ==Post-Quest Dialogue==
        Upon turning in this quest, {npc} will say:
        {{{{Chat|{npc}|{end_text}}}}}
    """)


def create_quest_dialogue(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    npc = ctx.get("npc", "")
    name = ctx.get("name", ctx.get("quest_name", ""))
    end_text = ctx.get("end_text", "")

    return textwrap.dedent(f"""\
        ==Dialogue==
        ===Pre-Quest===
        {{{{Conversation Dialogue|{npc}|{name}}}}}

        ===Post-Quest===
        {{{{Chat|{npc}|{end_text}}}}}
    """)


def create_quest_walkthrough(quest: dict, item_lookup=None) -> str:
    item_lookup = _get_item_lookup(item_lookup)
    requires, rewards, bonus = _format_req_reward_bonus(quest, item_lookup)

    return textwrap.dedent(f"""\
        ==Walkthrough==
        ===Step 1===
        {{{{Main quest section|questStep=|requires={requires}|rewards={rewards}|bonus={bonus}}}}}

        ===Step 2===
        {{{{Main quest section|questStep=|requires=|rewards=|bonus=}}}}

        ===Step 3===
        {{{{Main quest section|questStep=|requires=|rewards=|bonus=}}}}
    """)


def build_history_section(display_name: str) -> str:
    patch = constants.PATCH_VERSION.replace("PBE ", "").strip()
    return (
        f"==History==\n"
        f"*{{{{History|{patch}|[[{display_name}]] added to the game.}}}}\n"
    )


def create_hidden_block(quest: dict) -> str:
    ctx = extract_quest_context(quest)
    name = ctx.get("name", "")
    patch = constants.PATCH_VERSION.replace("PBE ", "").strip()
    return textwrap.dedent(f"""\
        <!--==Media==
        <gallery widths="200" bordercolor="transparent" spacing="small" captionalign="center">
        File:filename.png|File Description
        </gallery>

        ==Trivia==
        *
        -->
        ==History==
        *{{{{History|{patch}|[[{name}]] quest added to the game.}}}}


        {{{{Quest navbox}}}}
    """)
