"""
NPC walk schedule exporter — Layer 3 of the pipeline.

Reads *Path*.asset files from MonoBehaviour and writes one
"<NPC>_schedule.txt" per NPC to Wiki Formatted/NPC Schedules/.

Usage:
    python exporters/npc_walk_schedule.py
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils
from mappings.location_mapping import LOCATION_LINKS, PERSONAL_TERMS

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_INPUT_DIR     = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
_OUTPUT_DIR    = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Schedules")
_DEBUG_LOG     = os.path.join(constants.DEBUG_DIRECTORY, "npc_path_debug.txt")

# ---------------------------------------------------------------------------
# Testing config (set to False for production runs)
# ---------------------------------------------------------------------------

_TESTING       = False
_TEST_NPC_NAME = "Coty"

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_hour_to_time(hour_str: str) -> str:
    try:
        hour = float(hour_str)
        h = int(hour)
        m = int((hour - h) * 60)
        return f"{h}:{m:02}"
    except Exception:
        return hour_str


def _get_link_spans(s: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(r"\[\[.*?\]\]", s)]


def _is_within_links(index: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= index < end for start, end in spans)


def _apply_location_links(info: str, npc_name: str) -> str:
    for phrase, mapping in LOCATION_LINKS.items():
        pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
        info = pattern.sub(
            lambda m: (
                f"[[{mapping['link']}|{mapping.get('display', m.group(0))}]]"
                if "display" in mapping else f"[[{mapping['link']}]]"
            ),
            info,
        )

    link_spans = _get_link_spans(info)

    if npc_name in PERSONAL_TERMS:
        for phrase, link in PERSONAL_TERMS[npc_name].items():
            pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
            for match in reversed(list(pattern.finditer(info))):
                if _is_within_links(match.start(), link_spans):
                    continue
                info = info[:match.start()] + link + info[match.end():]
                link_spans = _get_link_spans(info)

    return info


def _clean_info(text: str, npc_name: str | None = None, group_label: str | None = None) -> str:
    text = text.lstrip("-").strip().strip('"').strip("'").strip()
    text = text[:1].upper() + text[1:]
    text = text.rstrip(" .") + "."

    if group_label and group_label.lower().startswith("married"):
        link_spans = _get_link_spans(text)

        pattern1 = re.compile(r"\b(their|his|her) (house|home)\b", re.IGNORECASE)
        for match in reversed(list(pattern1.finditer(text))):
            if not _is_within_links(match.start(), link_spans):
                text = text[:match.start()] + "[[Home Sweet Home|Player's House]]" + text[match.end():]
                link_spans = _get_link_spans(text)

        for word in ["house", "home"]:
            pattern2 = re.compile(rf"\b{word}\b", re.IGNORECASE)
            for match in reversed(list(pattern2.finditer(text))):
                if not _is_within_links(match.start(), link_spans):
                    text = text[:match.start()] + "[[Home Sweet Home|Player's House]]" + text[match.end():]
                    link_spans = _get_link_spans(text)

    if npc_name:
        text = _apply_location_links(text, npc_name)

    return text

# ---------------------------------------------------------------------------
# Schedule block helpers
# ---------------------------------------------------------------------------

def _parse_block_lines(block_lines: list[str]) -> list[tuple[str, str]]:
    result = []
    for line in block_lines:
        if "— hour " in line:
            name_part, hour = line.split("— hour ")
            result.append((name_part.strip(), hour.strip()))
    return result


def _extract_schedule_key(lines: list[str]) -> str:
    return "\n".join(lines)


def _add_schedule_block(
    title: str,
    entries: list[tuple[str, str]],
    group_id: int,
    schedule_lines: list[str],
    npc_name: str,
) -> int:
    schedule_lines.append(f"|{group_id}_name    = {title}")
    for i, (info, hour) in enumerate(entries, start=1):
        time_str = _format_hour_to_time(hour)
        cleaned  = _clean_info(info, npc_name, title)
        schedule_lines.append(f"|{group_id}_{i}_time  = {time_str}")
        schedule_lines.append(f"|{group_id}_{i}_info  = {cleaned}")
    return group_id + 1


def _group_blocks_by_similarity(path_list: list[tuple[str, list[str]]]) -> dict:
    block_groups: dict = defaultdict(list)
    for fname, lines in path_list:
        key = _extract_schedule_key(lines)
        block_groups[key].append(fname)
    return block_groups


def _get_dominant_block(block_groups: dict) -> tuple:
    return max(block_groups.items(), key=lambda x: len(x[1]))


def _label_from_season(fname: str) -> str:
    match = re.search(r"_(Spring|Summer|Fall|Winter)", fname)
    return match.group(1) if match else "Spring"


def _add_grouped_blocks(
    label: str,
    path_list: list[tuple[str, list[str]]],
    group_id: int,
    schedule_lines: list[str],
    npc_name: str,
) -> int:
    block_groups = _group_blocks_by_similarity(path_list)
    if len(block_groups) == 1:
        block = next(iter(block_groups))
        parsed = _parse_block_lines(block.splitlines())
        return _add_schedule_block(label, parsed, group_id, schedule_lines, npc_name)

    dominant_block, _ = _get_dominant_block(block_groups)
    parsed_dominant = _parse_block_lines(dominant_block.splitlines())
    group_id = _add_schedule_block(label, parsed_dominant, group_id, schedule_lines, npc_name)

    for blk, others in block_groups.items():
        if blk == dominant_block:
            continue
        season = _label_from_season(others[0])
        parsed = _parse_block_lines(blk.splitlines())
        group_id = _add_schedule_block(f"{label} ({season})", parsed, group_id, schedule_lines, npc_name)

    return group_id

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(_OUTPUT_DIR)
    file_utils.ensure_dir_exists(os.path.dirname(_DEBUG_LOG))

    path_files = [
        f for f in os.listdir(_INPUT_DIR)
        if "Path" in f and f.endswith(".asset") and "walkpath" not in f.lower()
    ]

    grouped_by_npc: dict = defaultdict(list)
    for filename in path_files:
        npc_name = filename.split("Path")[0]
        grouped_by_npc[npc_name].append(filename)

    debug_lines: list[str] = []

    for npc, files in grouped_by_npc.items():
        if _TESTING and npc != _TEST_NPC_NAME:
            continue

        paths: dict = defaultdict(list)
        debug_groups: dict = defaultdict(list)

        for filename in sorted(files):
            file_path = os.path.join(_INPUT_DIR, filename)
            try:
                content  = file_utils.read_file_lines(file_path)
                entries: list[tuple[str, str]] = []
                current_name = None

                for line in content:
                    line = line.rstrip()
                    if line.strip().startswith("- name:"):
                        current_name = line.split(":", 1)[1].strip()
                        continue
                    if current_name and line.strip().startswith("hour:"):
                        hour = line.split(":", 1)[1].strip()
                        entries.append((current_name, hour))
                        current_name = None

                if entries:
                    path_lines = [f"- {name} — hour {hour}" for name, hour in entries]
                    key = filename.replace(".asset", "")
                    paths[key].append((filename.replace(".asset", ""), path_lines))
                    debug_groups["\n".join(path_lines)].append(filename.replace(".asset", ""))

            except Exception as exc:
                file_utils.append_line(_DEBUG_LOG, f"[ERROR] Failed to parse {filename}: {exc}")

        schedule_lines = [f"{{{{Schedule |character = {npc}"]
        group_id = 1

        def collect(filter_fn):
            return [(name, lines) for name, entries in paths.items() for _, lines in entries if filter_fn(name)]

        general_a    = collect(lambda n: "PathA" in n and "Married" not in n)
        general_b    = collect(lambda n: "PathB" in n and "Married" not in n)
        general_base = collect(lambda n: (
            "PathA" not in n and "PathB" not in n
            and "Married" not in n and "Rain" not in n and "Locked" not in n
        ))

        def _same_block(list1, list2) -> bool:
            return _extract_schedule_key(list1[0][1]) == _extract_schedule_key(list2[0][1])

        if general_a and general_b:
            if _same_block(general_a, general_b):
                # Both files exist with identical content — write each as its own "General" group
                group_id = _add_grouped_blocks("General", general_a, group_id, schedule_lines, npc)
                group_id = _add_grouped_blocks("General", general_b, group_id, schedule_lines, npc)
            else:
                group_id = _add_grouped_blocks("General (A)", general_a, group_id, schedule_lines, npc)
                group_id = _add_grouped_blocks("General (B)", general_b, group_id, schedule_lines, npc)
        else:
            if general_a:
                group_id = _add_grouped_blocks("General", general_a, group_id, schedule_lines, npc)
            if general_b:
                group_id = _add_grouped_blocks("General", general_b, group_id, schedule_lines, npc)

        if general_base:
            group_id = _add_grouped_blocks("General", general_base, group_id, schedule_lines, npc)

        married = collect(lambda n: "Married" in n and "Rain" not in n)
        if married:
            group_id = _add_grouped_blocks("Married", married, group_id, schedule_lines, npc)

        married_rain = collect(lambda n: "Rain" in n and "Married" in n)
        if married_rain and married:
            base_married_blocks = _group_blocks_by_similarity(married)
            rain_blocks         = _group_blocks_by_similarity(married_rain)
            for blk in rain_blocks:
                if blk not in base_married_blocks:
                    parsed   = _parse_block_lines(blk.splitlines())
                    group_id = _add_schedule_block("Married (Raining)", parsed, group_id, schedule_lines, npc)

        rain = collect(lambda n: "Rain" in n and "Married" not in n)
        if rain:
            general_blocks         = collect(lambda n: "Married" not in n and "Locked" not in n and "Rain" not in n)
            rain_blocks            = _group_blocks_by_similarity(rain)
            general_blocks_grouped = _group_blocks_by_similarity(general_blocks)
            if list(rain_blocks.keys()) != list(general_blocks_grouped.keys()):
                group_id = _add_grouped_blocks("Raining", rain, group_id, schedule_lines, npc)

        locked = collect(lambda n: "Locked" in n)
        for fname, lines in locked:
            parsed   = _parse_block_lines(lines)
            group_id = _add_schedule_block("Locked", parsed, group_id, schedule_lines, npc)

        schedule_lines.append("}}")
        output_path = os.path.join(_OUTPUT_DIR, f"{npc}_schedule.txt")
        file_utils.write_lines(output_path, [line + "\n" for line in schedule_lines])

        debug_lines.append(f"### {npc}")
        for block, fnames in debug_groups.items():
            debug_lines.append(f"Paths: {', '.join(fnames)}")
            debug_lines.append(block)
            debug_lines.append("")

    if debug_lines:
        file_utils.write_lines(_DEBUG_LOG, [line + "\n" for line in debug_lines])

    print(f"✅ NPC schedules written to: {_OUTPUT_DIR}")


if __name__ == "__main__":
    run()
