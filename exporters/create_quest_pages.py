"""
Create quest pages exporter — Layer 3 of the pipeline.

Reads quest_data_MainQuests.json and quest_data_BB_SQ.json and writes one
.txt wiki page per quest to Wiki Formatted/Quest Pages/.

Usage:
    python exporters/create_quest_pages.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from formatters.pages.quest_page import create_quest_page
from utils import json_utils, file_utils
from utils.file_utils import sanitize_filename

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_JSON_DIR   = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
_OUTPUT_DIR = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Quest Pages")

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(_OUTPUT_DIR)

    main_quests     = json_utils.load_json(os.path.join(_JSON_DIR, "quest_data_MainQuests.json"))
    bulletin_quests = json_utils.load_json(os.path.join(_JSON_DIR, "quest_data_BB_SQ.json"))

    # Flatten all quests into one dict keyed by quest_name
    all_quests: dict = {}
    for section in main_quests.values():
        for q in section:
            name = q.get("quest_name", "")
            if name:
                all_quests[name] = q
    for section in bulletin_quests.values():
        for q in section:
            name = q.get("quest_name", "")
            if name:
                all_quests[name] = q

    created = 0
    for name, quest in all_quests.items():
        page_text = create_quest_page(quest)
        safe_name = sanitize_filename(name)
        filename  = os.path.join(_OUTPUT_DIR, f"{safe_name}.txt")
        file_utils.write_lines(filename, [page_text])
        created += 1

    print(f"✅ {created} quest pages written to {_OUTPUT_DIR}")


if __name__ == "__main__":
    run()
