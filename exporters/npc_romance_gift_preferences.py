"""
NPC romance gift preferences exporter — Layer 3 of the pipeline.

Reads GiftTable.asset files from MonoBehaviour and writes
npc_gift_preferences.txt with {{NPC Gift Preferences}} wikitext.

Item IDs are resolved from the item builder cache via _load_cache().

Usage:
    python exporters/npc_romance_gift_preferences.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from builders.item_builder import _load_cache
from utils import file_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_INPUT_DIR      = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
_OUTPUT_FILE    = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "npc_gift_preferences.txt")
_DEBUG_LOG      = os.path.join(constants.DEBUG_DIRECTORY, "create_npc_gift_debug.txt")

# ---------------------------------------------------------------------------
# Items to exclude from output
# ---------------------------------------------------------------------------

_SKIP_ITEMS = {"red rose bouquet", "blue rose bouquet"}

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _extract_ids_between_sections(lines: list[str], section_header: str) -> list[str]:
    ids = []
    in_section = False
    for line in lines:
        line = line.strip()
        if line.startswith(section_header):
            in_section = True
            continue
        if in_section:
            if re.match(r"^[a-zA-Z0-9_]+:", line):
                break
            m = re.match(r"- id:\s*(\d+)", line)
            if m:
                ids.append(m.group(1))
    return ids


def _extract_response_block(lines: list[str], section_header: str) -> str:
    responses = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(section_header):
            in_section = True
            continue
        if in_section:
            if re.match(r"^[a-zA-Z0-9_]+:", stripped):
                break
            if stripped.startswith("- response:"):
                text = (
                    stripped.split(":", 1)[1]
                    .strip()
                    .replace("ITEM", "[''item'']")
                    .replace("XX", "{{PLAYER}}")
                    .replace("PPP", "{{PARENT}}")
                )
                responses.append(text)
    return " / ".join(responses)


def _convert_ids_to_names(id_list: list[str], id_to_name: dict) -> str:
    names = []
    for item_id in id_list:
        name = id_to_name.get(item_id)
        if name:
            if name.lower() not in _SKIP_ITEMS:
                names.append(name)
        else:
            names.append(f"[Unknown {item_id}]")
    return "; ".join(names)

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_OUTPUT_FILE))
    file_utils.ensure_dir_exists(os.path.dirname(_DEBUG_LOG))

    # Build id → name from item builder cache
    items = _load_cache()
    id_to_name: dict[str, str] = {str(item.item_id): item.name for item in items.values()}

    results: list[str] = []

    for filename in os.listdir(_INPUT_DIR):
        if not filename.endswith("GiftTable.asset"):
            continue

        npc_name = filename.replace("GiftTable.asset", "")
        filepath = os.path.join(_INPUT_DIR, filename)
        lines = file_utils.read_file_lines(filepath)

        love_ids    = _extract_ids_between_sections(lines, "love2:")
        like_ids    = _extract_ids_between_sections(lines, "like2:")
        dislike_ids = _extract_ids_between_sections(lines, "dislike2:")

        love_response    = _extract_response_block(lines, "loveGiftResponses:")
        like_response    = _extract_response_block(lines, "likeGiftResponses:")
        good_response    = _extract_response_block(lines, "goodGiftResponses:")
        dislike_response = _extract_response_block(lines, "dislikeGiftResponses:")

        block = [
            f"### {npc_name} ###",
            "{{NPC Gift Preferences",
            f"|loveResponse = {love_response}",
            f"|love = {_convert_ids_to_names(love_ids, id_to_name)}",
            "|loveGroups = [[:Category:Universally loved gifts|Universally Loved Items]]",
            "",
            f"|likeResponse = {like_response}",
            f"|like = {_convert_ids_to_names(like_ids, id_to_name)}",
            "|likeGroups = [[:Category:Universally liked gifts|Universally Liked Items]]",
            "",
            f"|goodResponse = {good_response}",
            "",
            f"|dislikeResponse = {dislike_response}",
            f"|dislike = {_convert_ids_to_names(dislike_ids, id_to_name)}",
            "|dislikeGroups = [[:Category:Universally disliked gifts|Universally Disliked Items]]",
            "}}\n",
        ]

        results.append("\n".join(block))

    file_utils.write_lines(_OUTPUT_FILE, [line + "\n" for line in results])
    print(f"✅ Gift tables written to: {_OUTPUT_FILE}")


if __name__ == "__main__":
    run()
