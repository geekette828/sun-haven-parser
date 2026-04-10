"""
All NPC names exporter — Layer 3 of the pipeline.

Reads English.prefab to extract unique NPC names and writes npc_list.txt
and Unique_NPC_Names_For_Patch.txt.

Usage:
    python exporters/all_npc_names.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_INPUT_PREFAB   = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")
_OUTPUT_DIR     = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted")
_OUTPUT_FILE    = os.path.join(_OUTPUT_DIR, "npc_list.txt")
_UNIQUE_FILE    = os.path.join(constants.OUTPUT_DIRECTORY, "Unique_NPC_Names_For_Patch.txt")
_DEBUG_LOG      = os.path.join(constants.DEBUG_DIRECTORY, "npc_list_debug.txt")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_on_capitals(name: str) -> str:
    """Split CamelCase into words: HungrySlime → Hungry Slime."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)


def _extract_npc_names(prefab_path: str) -> list[str]:
    if not os.path.exists(prefab_path):
        raise FileNotFoundError(f"English.prefab not found at: {prefab_path}")

    npc_names: set[str] = set()
    pattern = re.compile(r"\b(?:NPC|RNPC|TNPC)\.([^\s\.]+)\.")

    with open(prefab_path, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, start=1):
            for m in pattern.finditer(line):
                name = (m.group(1) or "").strip()
                if name:
                    npc_names.add(name)
                else:
                    file_utils.append_line(
                        _DEBUG_LOG,
                        f"[WARN] Empty name match on line {line_num}: {line.strip()}",
                    )

    return sorted(npc_names, key=lambda x: x.lower())

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(_OUTPUT_DIR)
    file_utils.ensure_dir_exists(os.path.dirname(_DEBUG_LOG))

    raw_names  = _extract_npc_names(_INPUT_PREFAB)
    split_names = [_split_on_capitals(name) for name in raw_names]

    # npc_list.txt — split names for display
    file_utils.write_lines(_OUTPUT_FILE, [name + "\n" for name in split_names])

    # Unique_NPC_Names_For_Patch.txt — used by create_npc_pages exporter
    file_utils.write_lines(_UNIQUE_FILE, [name + "\n" for name in split_names])

    print(f"✅ Extracted {len(split_names)} unique NPCs from English.prefab.")
    print(f"📄 Output saved to: {_OUTPUT_FILE}")
    print(f"📄 Unique names saved to: {_UNIQUE_FILE}")


if __name__ == "__main__":
    run()
