"""
NPC dialogue (one-liners) exporter — Layer 3 of the pipeline.

Reads npc_dialogue.json and writes one "<NPC> one liners.txt" per NPC
to Wiki Formatted/NPC Dialogue/.

Usage:
    python exporters/npc_dialogue.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.stdout.reconfigure(encoding="utf-8")

import config.constants as constants
from utils import json_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_INPUT_JSON    = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "npc_dialogue.json")
_OUTPUT_FOLDER = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Dialogue")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_INVALID_FILENAME_CHARS = r'<>:"/\|?*'
_SEASONS     = ["Spring", "Summer", "Fall", "Winter"]
_SEASON_SET  = {s.lower() for s in _SEASONS}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    if not name:
        return "Unknown"
    out = ["_" if ch in _INVALID_FILENAME_CHARS else ch for ch in name]
    filename = "".join(out).strip().strip(".")
    return filename or "Unknown"


def _escape_template_param(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return text.replace("|", "&#124;")


def _split_condition(bucket: str):
    b  = (bucket or "").strip()
    bl = b.lower()

    if bl in {"", "unconditional"}:
        return None, None
    if bl == "platonic":
        return "platonic", None
    if bl in _SEASON_SET:
        return None, bl
    if bl.startswith("dating"):
        suffix = bl[len("dating"):]
        return "dating", (suffix if suffix in _SEASON_SET else None)
    if bl.startswith("married"):
        suffix = bl[len("married"):]
        return "married", (suffix if suffix in _SEASON_SET else None)
    return "other", None


def _token_string(relationship: str | None, season: str | None) -> str:
    tokens = []
    if relationship in {"dating", "married"}:
        tokens.append(relationship)
    if season:
        tokens.append(season)
    if relationship == "other":
        tokens = []
    if not tokens:
        return ""
    markup = " ".join(f"{{{{Dialogue token|{t}}}}}" for t in tokens)
    return f" {markup} "


def _format_chat_line(npc_name: str, dialogue: str, relationship: str | None, season: str | None) -> str:
    npc  = _escape_template_param(npc_name.strip())
    line = _escape_template_param((dialogue or "").strip())

    if relationship == "platonic":
        return f"{{{{chat|{npc}|{line}}}}}"

    tokens = _token_string(relationship, season)
    if tokens:
        return f"{{{{chat|{npc}|{line}{tokens}}}}}"
    return f"{{{{chat|{npc}|{line}}}}}"

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    data = json_utils.load_json(_INPUT_JSON)
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict JSON in {_INPUT_JSON}")

    os.makedirs(_OUTPUT_FOLDER, exist_ok=True)

    npc_written  = 0
    total_lines  = 0

    for npc_name in sorted(data.keys(), key=lambda s: str(s).lower()):
        npc_obj = data.get(npc_name, {})
        if not isinstance(npc_obj, dict):
            continue

        npc_data = npc_obj.get("one_liners", {})
        if not isinstance(npc_data, dict):
            continue

        # Bucket accumulators
        strangers_unconditional: list[str] = []
        strangers_seasonal: dict[str, list[str]] = {s.lower(): [] for s in _SEASONS}
        platonic: list[str] = []
        dating_unseasonal: list[str] = []
        dating_seasonal: dict[str, list[str]] = {s.lower(): [] for s in _SEASONS}
        married_unseasonal: list[str] = []
        married_seasonal: dict[str, list[str]] = {s.lower(): [] for s in _SEASONS}

        for bucket, entries in npc_data.items():
            if not isinstance(entries, list):
                continue
            texts = [e["text"] for e in entries if isinstance(e, dict) and e.get("text")]
            if not texts:
                continue

            relationship, season = _split_condition(bucket)

            if relationship is None and season is None:
                strangers_unconditional.extend(texts)
            elif relationship is None and season in _SEASON_SET:
                strangers_seasonal[season].extend(texts)
            elif relationship == "platonic":
                platonic.extend(texts)
            elif relationship == "dating" and season is None:
                dating_unseasonal.extend(texts)
            elif relationship == "dating" and season in _SEASON_SET:
                dating_seasonal[season].extend(texts)
            elif relationship == "married" and season is None:
                married_unseasonal.extend(texts)
            elif relationship == "married" and season in _SEASON_SET:
                married_seasonal[season].extend(texts)
            else:
                strangers_unconditional.extend(texts)

        has_any = any([
            strangers_unconditional,
            any(strangers_seasonal[s.lower()] for s in _SEASONS),
            platonic,
            dating_unseasonal,
            any(dating_seasonal[s.lower()] for s in _SEASONS),
            married_unseasonal,
            any(married_seasonal[s.lower()] for s in _SEASONS),
        ])
        if not has_any:
            continue

        output_lines: list[str] = []

        output_lines.append("===Strangers===")
        for text in strangers_unconditional:
            output_lines.append(_format_chat_line(npc_name, text, None, None))
            total_lines += 1
        for season_name in _SEASONS:
            for text in strangers_seasonal[season_name.lower()]:
                output_lines.append(_format_chat_line(npc_name, text, None, season_name.lower()))
                total_lines += 1

        output_lines.append("")
        output_lines.append("===Platonic===")
        for text in platonic:
            output_lines.append(_format_chat_line(npc_name, text, "platonic", None))
            total_lines += 1

        output_lines.append("")
        output_lines.append("===Dating===")
        for text in dating_unseasonal:
            output_lines.append(_format_chat_line(npc_name, text, "dating", None))
            total_lines += 1
        for season_name in _SEASONS:
            for text in dating_seasonal[season_name.lower()]:
                output_lines.append(_format_chat_line(npc_name, text, "dating", season_name.lower()))
                total_lines += 1

        output_lines.append("")
        output_lines.append("===Married===")
        for text in married_unseasonal:
            output_lines.append(_format_chat_line(npc_name, text, "married", None))
            total_lines += 1
        for season_name in _SEASONS:
            for text in married_seasonal[season_name.lower()]:
                output_lines.append(_format_chat_line(npc_name, text, "married", season_name.lower()))
                total_lines += 1

        npc_written += 1
        outfile = os.path.join(_OUTPUT_FOLDER, f"{_safe_filename(npc_name)} one liners.txt")
        with open(outfile, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(output_lines).rstrip() + "\n")

    print(f"✅ Wrote {npc_written} NPC one-liner files to: {_OUTPUT_FOLDER}")
    print(f"✅ Total chat lines written: {total_lines}")


if __name__ == "__main__":
    run()
