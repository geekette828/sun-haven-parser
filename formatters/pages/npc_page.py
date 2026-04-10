"""
NPC page formatter — Layer 2 of the pipeline.

Pure formatting functions for NPC wiki pages.
No file I/O — all functions return strings.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import config.constants as constants

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TEXTURE_BLURB = (
    "This [[characters|character]] is a texture NPC — a type of non-playable character designed to add depth "
    "and life to the world rather than serve as a major figure in the story. Texture NPCs usually have minimal "
    "dialogue, often just a single line that offers a glimpse into their personality, environment, or the current "
    "season. They might appear or disappear depending on the time of year or specific in-game events, helping the "
    "world feel more dynamic and lived-in."
)

_CHARACTER_BLURB = "This [[characters|character]] is an interactable NPC."

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_title_case(name: str) -> str:
    return " ".join(word.capitalize() for word in name.split())


def extract_chat_templates(one_liner_text: str) -> list[str]:
    """Keep only {{chat|...}} lines; strip section headers."""
    chat_lines = []
    for line in one_liner_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("===") and stripped.endswith("==="):
            continue
        if "{{chat|" in stripped:
            chat_lines.append(stripped)
    return chat_lines


def _determine_npc_type(cycles_text: str, one_liners: list[str]) -> str:
    if cycles_text.strip():
        return "Character"
    return "Texture"

# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def build_infobox(npc_type: str) -> str:
    return (
        "{{NPC infobox\n"
        f"|type = {npc_type}\n"
        "|race = \n"
        "|species = \n"
        "|birthday = \n"
        "|gender = \n"
        "|occupation = \n"
        "|region = \n"
        "|residence = \n"
        "|relationships = \n"
        "<!-- Animations -->\n"
        "|blinking = \n"
        "|breathing = \n"
        "|walking =  \n"
        "}}\n"
    )


def build_summary(npc_name: str) -> str:
    return f"'''{npc_name}''' is a character the player can encounter<!--When/Where-->.\n"


def build_type_blurb(npc_type: str) -> str:
    if npc_type == "Texture":
        return _TEXTURE_BLURB + "\n"
    return _CHARACTER_BLURB + "\n"


def build_schedule(npc_name: str, schedule_text: str) -> str:
    intro = (
        f"{npc_name} currently has only one schedule that they follow, "
        "regardless if it is sunny or rainy.\n"
    )
    if schedule_text:
        return "==Schedule==\n" + intro + schedule_text.strip() + "\n"

    return (
        "==Schedule==\n"
        + intro
        + f"{{{{Schedule |character = {npc_name}\n"
        + "|1_name    = General\n"
        + "|1_1_time  = 6:00\n"
        + "|1_1_info  = \n"
        + "}}\n"
    )


def build_quests() -> str:
    return "==Quests==\n{{Quest involves NPC}}\n"


def build_dialogue(one_liners: list[str], cycles_text: str) -> str:
    parts = [
        "==Dialogue==\n",
        "===General Dialogue===\n",
        "General non-conversational dialogue between this character and the player.\n",
    ]
    if one_liners:
        parts.append("\n".join(one_liners).strip() + "\n")
    if cycles_text.strip():
        parts.extend([
            "\n===Conversations===\n",
            cycles_text.strip() + "\n",
        ])
    return "".join(parts)


def build_media_trivia_block(npc_name: str) -> str:
    return (
        "<!--==Media==\n"
        '<gallery widths="150" bordercolor="transparent" spacing="small" captionalign="center">\n'
        f"File:{npc_name} location.png|In game representation and location\n"
        "</gallery>\n\n"
        "==Trivia==\n"
        "* \n"
        "-->\n"
    )


def build_history(npc_name: str) -> str:
    patch = constants.PATCH_VERSION.replace("PBE ", "").strip()
    return (
        "==History==\n"
        f"*{{{{History|{patch}|[[{npc_name}]] npc added to the game.}}}}\n"
    )


def build_navbox() -> str:
    return "\n{{NPC navbox}}\n"

# ---------------------------------------------------------------------------
# Top-level assembler
# ---------------------------------------------------------------------------

def build_page_wikitext(
    npc_name: str,
    one_liners: list[str],
    cycles_text: str,
    schedule_text: str,
) -> str:
    npc_type = _determine_npc_type(cycles_text, one_liners)

    parts = [
        build_infobox(npc_type),
        "\n",
        build_summary(npc_name),
        "\n",
        build_type_blurb(npc_type),
        "\n",
        build_schedule(npc_name, schedule_text),
        "\n",
        build_quests(),
        "\n",
        build_dialogue(one_liners, cycles_text),
        "\n",
        build_media_trivia_block(npc_name),
        "\n",
        build_history(npc_name),
        "\n",
        build_navbox(),
    ]
    return "".join(parts).strip() + "\n"


def process_one_liner_file(one_liner_text: str) -> list[str]:
    """Convenience wrapper: extract {{chat|...}} lines from raw file text."""
    return extract_chat_templates(one_liner_text)
