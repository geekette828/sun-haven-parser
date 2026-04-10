"""
Create NPC pages exporter — Layer 3 of the pipeline.

Reads NPC names from Unique_NPC_Names_For_Patch.txt and dialogue files
from Wiki Formatted/NPC Dialogue/, then writes one .txt wiki page per NPC
to Wiki Formatted/NPC Pages/.

Run after: all_npc_names.py, npc_dialogue.py, npc_cycles.py, npc_walk_schedule.py

Usage:
    python exporters/create_npc_pages.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from formatters.pages.npc_page import build_page_wikitext, process_one_liner_file

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_OUTPUT_DIR        = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Pages")
_DIALOGUE_DIR      = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Dialogue")
_SCHEDULE_DIR      = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Schedules")
_NPC_NAMES_FILE    = os.path.join(constants.OUTPUT_DIRECTORY, "Unique_NPC_Names_For_Patch.txt")
_DEBUG_LOG         = os.path.join(constants.DEBUG_DIRECTORY, "wiki formatted", "npc_pages_build.log")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_debug(message: str) -> None:
    os.makedirs(os.path.dirname(_DEBUG_LOG), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def _to_title_case(name: str) -> str:
    return " ".join(word.capitalize() for word in name.split())


def _read_npc_names() -> list[str]:
    if not os.path.exists(_NPC_NAMES_FILE):
        _log_debug(f"NPC names file not found: {_NPC_NAMES_FILE}")
        return []

    seen_lower: set[str] = set()
    names: list[str] = []

    with open(_NPC_NAMES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            raw_name = line.strip()
            if not raw_name:
                continue
            title_name = _to_title_case(raw_name)
            key = title_name.lower()
            if key not in seen_lower:
                seen_lower.add(key)
                names.append(title_name)

    return sorted(names, key=lambda x: x.lower())


def _read_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def _load_schedule(npc_name: str) -> str:
    path = os.path.join(_SCHEDULE_DIR, f"{npc_name}_schedule.txt")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    os.makedirs(_OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(_DIALOGUE_DIR):
        _log_debug(f"Dialogue folder does not exist: {_DIALOGUE_DIR}")
        print(f"ERROR: Dialogue folder does not exist: {_DIALOGUE_DIR}")
        return

    npc_names = _read_npc_names()
    _log_debug(f"NPC names loaded: {len(npc_names)}")
    print(f"NPC names loaded: {len(npc_names)}")

    if not npc_names:
        _log_debug("NPC name list is empty. Nothing to do.")
        print("No NPC names loaded. Nothing to do.")
        return

    created           = 0
    skipped           = 0
    missing_one_liners = 0
    missing_cycles    = 0
    missing_schedules = 0

    for npc_name in npc_names:
        one_liner_path = os.path.join(_DIALOGUE_DIR, f"{npc_name} one liners.txt")
        cycles_path    = os.path.join(_DIALOGUE_DIR, f"{npc_name} cycles.txt")

        one_liner_text = _read_file(one_liner_path)
        cycles_text    = _read_file(cycles_path)
        schedule_text  = _load_schedule(npc_name)

        if not one_liner_text and not cycles_text:
            skipped += 1
            _log_debug(f"Skipping {npc_name}: missing both dialogue files.")
            continue

        if not one_liner_text:
            missing_one_liners += 1
            _log_debug(f"Missing one-liner file for {npc_name}: {one_liner_path}")

        if not cycles_text:
            missing_cycles += 1
            _log_debug(f"Missing cycles file for {npc_name}: {cycles_path}")

        if not schedule_text:
            missing_schedules += 1
            _log_debug(f"No schedule file for {npc_name}, using default.")

        one_liners = process_one_liner_file(one_liner_text)
        if one_liner_text and not one_liners:
            _log_debug(f"No {{{{chat|...}}}} lines found for {npc_name}: {one_liner_path}")

        page_text = build_page_wikitext(
            npc_name=npc_name,
            one_liners=one_liners,
            cycles_text=cycles_text,
            schedule_text=schedule_text,
        )

        out_path = os.path.join(_OUTPUT_DIR, f"{npc_name}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page_text)

        created += 1
        _log_debug(f"Wrote NPC page: {out_path}")

    summary = (
        f"Done. Created: {created}, Skipped: {skipped}, "
        f"Missing one-liners: {missing_one_liners}, Missing cycles: {missing_cycles}, "
        f"Missing schedules: {missing_schedules}"
    )
    _log_debug(f"✅ {summary}")
    print(f"✅ {summary}")


if __name__ == "__main__":
    run()
