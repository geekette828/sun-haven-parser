"""
Quest page formatter — Layer 2 of the pipeline.

Pure formatting function that assembles a complete quest wiki page.
No file I/O — returns a string.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from formatters.quest.quest_infobox import (
    create_quest_infobox,
    load_item_lookup,
    resolve_quest_type,
)
from formatters.quest.quest_summary import create_quest_summary
from formatters.quest.quest_sections import (
    create_quest_overview_box,
    create_quest_overview_steps_box,
    create_quest_step_list,
    create_quest_bb_description,
    create_quest_description,
    create_quest_complete_text,
    create_quest_dialogue,
    create_quest_walkthrough,
    create_hidden_block,
)
from formatters.quest.quest_context import extract_quest_context


def create_quest_page(quest: dict, npc: str = "", bulletin: str = "", end_text: str = "") -> str:
    """
    Assemble a complete quest wiki page and return it as a string.
    """
    item_lookup = load_item_lookup()
    next_lookup: dict = {}
    quest_type = resolve_quest_type(quest).lower()

    ctx = extract_quest_context(quest, npc=npc, end_text=end_text)
    infobox = create_quest_infobox(quest, item_lookup, next_lookup)
    summary = create_quest_summary(
        quest,
        npc=ctx["npc"],
        bulletin=ctx["description"],
        end_text=end_text,
    )

    sections: list[str] = []

    if "romance" in quest_type:
        sections.append(create_hidden_block(quest))

    elif quest_type in ["bulletin", "bulletin board"]:
        sections.extend([
            create_quest_overview_box(quest),
            create_quest_bb_description(quest),
            create_quest_complete_text(quest),
            create_hidden_block(quest),
        ])

    elif quest_type == "character":
        sections.extend([
            create_quest_overview_box(quest),
            create_quest_description(quest),
            create_quest_dialogue(quest),
            create_hidden_block(quest),
        ])

    elif "main" in quest_type:
        sections.extend([
            create_quest_overview_steps_box(quest),
            create_quest_step_list(quest),
            create_quest_walkthrough(quest),
            create_hidden_block(quest),
        ])

    else:
        sections.append(create_hidden_block(quest))

    full_page = "\n".join([infobox, summary]) + "\n\n" + "\n".join(sections).strip()
    return full_page
