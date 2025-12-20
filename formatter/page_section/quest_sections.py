import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import config.constants as constants
import textwrap
from mappings.quest_mapping import extract_quest_context


def _get_item_lookup(item_lookup):
    """Use passed lookup when available; otherwise load once."""
    if item_lookup is not None:
        return item_lookup
    from formatter.page_section.quest_infobox import load_item_lookup
    return load_item_lookup()


def _format_req_reward_bonus(quest: dict, item_lookup) -> tuple[str, str, str]:
    """
    Format requires/rewards/bonus from the quest dict using the SAME data keys
    the infobox uses (not extract_quest_context).
    """
    from formatter.page_section.quest_infobox import format_items

    requires = format_items(quest.get("itemRequirements", []), item_lookup)
    rewards = format_items(quest.get("guaranteeRewards2", []), item_lookup)
    bonus = format_items(quest.get("choiceRewards2", []), item_lookup)
    return requires, rewards, bonus


def create_quest_overview_box(quest: dict, item_lookup=None) -> str:
    ctx = extract_quest_context(quest)
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
    """
    A steps-style overview box for main quests.
    This uses overall quest requires/rewards/bonus for step 1 (until you map per-step rewards).
    """
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
    """
    Leaves your existing quest-mapping logic alone.
    This depends on extract_quest_context producing ctx['step_list'] (or similar).
    If your mapping uses a different key, update it here.
    """
    ctx = extract_quest_context(quest)

    # Try a couple common keys so this doesn't silently break when mapping changes.
    step_list = (
        ctx.get("step_list")
        or ctx.get("steps_list")
        or ctx.get("steps")
        or ""
    )

    if isinstance(step_list, list):
        # If mapping returns list[str], render as bullets
        step_list = "\n".join([f"* {s}" for s in step_list if s])

    if step_list and not str(step_list).strip().startswith("*"):
        # If mapping returns a blob, don’t double-bullet it.
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
    name = ctx.get("name", ctx.get("questName", ctx.get("quest_name", "")))
    end_text = ctx.get("end_text", "")

    return textwrap.dedent(f"""\
        ==Dialogue==
        ===Pre-Quest===
        {{{{Conversation Dialogue|{npc}|{name}}}}}

        ===Post-Quest===
        {{{{Chat|{npc}|{end_text}}}}}
    """)


def create_quest_walkthrough(quest: dict, item_lookup=None) -> str:
    """
    Main quest walkthrough skeleton that includes the overall requires/rewards/bonus in Step 1.
    """
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

def build_history_section(display_name):
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