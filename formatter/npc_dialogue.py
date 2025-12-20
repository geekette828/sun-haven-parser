"""
Read npc_one_liners.json and write one formatted .txt file per NPC.

Output folder:
  <OUTPUT_DIRECTORY>/npc dialogue/

Output files:
  <Name>_one_liner.txt

Format:
  {{chat|<name>|<dialogue>}}
  {{chat|<name>|<dialogue> {{Dialogue token|<lower case condition>}} }}  (when conditional)
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")

import config.constants as constants
from utils import json_utils

# Paths
INPUT_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "npc_one_liners.json")
OUTPUT_FOLDER = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Dialogue")

INVALID_FILENAME_CHARS = r'<>:"/\|?*'
SEASONS = ["Spring", "Summer", "Fall", "Winter"]
SEASON_SET = {s.lower() for s in SEASONS}


def safe_filename(name: str) -> str:
    if not name:
        return "Unknown"
    out = []
    for ch in name:
        out.append("_" if ch in INVALID_FILENAME_CHARS else ch)
    filename = "".join(out).strip().strip(".")
    return filename or "Unknown"


def escape_template_param(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return text.replace("|", "&#124;")


def split_condition(bucket: str):
    """
    Convert a bucket name into:
      (relationship, season)

    relationship: None / "dating" / "married" / "platonic"
    season: None / "spring" / "summer" / "fall" / "winter"

    Buckets come from your JSON keys (e.g., Unconditional, Spring, Dating, DatingWinter, MarriedSpring).
    """
    b = (bucket or "").strip()
    bl = b.lower()

    if bl in {"", "unconditional"}:
        return None, None

    if bl == "platonic":
        return "platonic", None

    if bl in SEASON_SET:
        return None, bl

    # dating + optional season suffix
    if bl.startswith("dating"):
        suffix = bl[len("dating") :]
        season = suffix if suffix in SEASON_SET else None
        return "dating", season

    # married + optional season suffix
    if bl.startswith("married"):
        suffix = bl[len("married") :]
        season = suffix if suffix in SEASON_SET else None
        return "married", season

    # Unknown condition: treat as strangers non-season, but still add token
    return "other", None


def token_string(relationship: str | None, season: str | None) -> str:
    """
    Build the token(s) to append inside the chat template.
    Returns "" if none.
    """
    tokens = []

    if relationship in {"dating", "married"}:
        tokens.append(relationship)

    if season:
        tokens.append(season)

    # platonic gets no tokens; strangers unconditional gets no tokens
    if relationship == "other":
        tokens = []

    if not tokens:
        return ""

    token_markup = " ".join(f"{{{{Dialogue token|{t}}}}}" for t in tokens)
    return f" {token_markup} "


def format_chat_line(npc_name: str, dialogue: str, relationship: str | None, season: str | None) -> str:
    npc = escape_template_param(npc_name.strip())
    line = escape_template_param((dialogue or "").strip())

    # Platonic explicitly gets no token
    if relationship == "platonic":
        return f"{{{{chat|{npc}|{line}}}}}"

    tokens = token_string(relationship, season)
    if tokens:
        return f"{{{{chat|{npc}|{line}{tokens}}}}}"
    return f"{{{{chat|{npc}|{line}}}}}"


def append_entries(lines_out, npc_name: str, entries):
    """
    entries: list of dicts with 'text'
    """
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        text = entry.get("text", "")
        if text:
            lines_out.append(text)


def main() -> None:
    data = json_utils.load_json(INPUT_JSON_PATH)
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict JSON in {INPUT_JSON_PATH}")

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    npc_written = 0
    total_lines = 0

    for npc_name in sorted(data.keys(), key=lambda s: str(s).lower()):
        npc_data = data.get(npc_name, {})
        if not isinstance(npc_data, dict):
            continue

        # Collect into buckets we actually want to print
        strangers_unconditional = []
        strangers_seasonal = {s.lower(): [] for s in SEASONS}
        platonic = []

        dating_unseasonal = []
        dating_seasonal = {s.lower(): [] for s in SEASONS}

        married_unseasonal = []
        married_seasonal = {s.lower(): [] for s in SEASONS}

        # Walk through all buckets in JSON
        for bucket, entries in npc_data.items():
            if not isinstance(entries, list):
                continue

            relationship, season = split_condition(bucket)

            # Pull dialogue strings
            texts = []
            for entry in entries:
                if isinstance(entry, dict) and entry.get("text"):
                    texts.append(entry["text"])

            if not texts:
                continue

            if relationship is None and season is None:
                strangers_unconditional.extend(texts)
            elif relationship is None and season in SEASON_SET:
                strangers_seasonal[season].extend(texts)
            elif relationship == "platonic":
                platonic.extend(texts)
            elif relationship == "dating" and season is None:
                dating_unseasonal.extend(texts)
            elif relationship == "dating" and season in SEASON_SET:
                dating_seasonal[season].extend(texts)
            elif relationship == "married" and season is None:
                married_unseasonal.extend(texts)
            elif relationship == "married" and season in SEASON_SET:
                married_seasonal[season].extend(texts)
            else:
                # Unknown buckets: treat as strangers unconditional (no token)
                strangers_unconditional.extend(texts)

        output_lines = []

        # Strangers
        output_lines.append("===Strangers===")
        for text in strangers_unconditional:
            output_lines.append(format_chat_line(npc_name, text, None, None))
            total_lines += 1

        for season_name in SEASONS:
            season_key = season_name.lower()
            for text in strangers_seasonal[season_key]:
                output_lines.append(format_chat_line(npc_name, text, None, season_key))
                total_lines += 1

        # Platonic
        output_lines.append("")
        output_lines.append("===Platonic===")
        for text in platonic:
            output_lines.append(format_chat_line(npc_name, text, "platonic", None))
            total_lines += 1

        # Dating
        output_lines.append("")
        output_lines.append("===Dating===")
        for text in dating_unseasonal:
            output_lines.append(format_chat_line(npc_name, text, "dating", None))
            total_lines += 1
        for season_name in SEASONS:
            season_key = season_name.lower()
            for text in dating_seasonal[season_key]:
                output_lines.append(format_chat_line(npc_name, text, "dating", season_key))
                total_lines += 1

        # Married
        output_lines.append("")
        output_lines.append("===Married===")
        for text in married_unseasonal:
            output_lines.append(format_chat_line(npc_name, text, "married", None))
            total_lines += 1
        for season_name in SEASONS:
            season_key = season_name.lower()
            for text in married_seasonal[season_key]:
                output_lines.append(format_chat_line(npc_name, text, "married", season_key))
                total_lines += 1

        # If NPC has literally no lines, skip writing
        # (We still would have headers, but no content.)
        has_any_dialogue = any([
            strangers_unconditional,
            any(strangers_seasonal[s.lower()] for s in SEASONS),
            platonic,
            dating_unseasonal,
            any(dating_seasonal[s.lower()] for s in SEASONS),
            married_unseasonal,
            any(married_seasonal[s.lower()] for s in SEASONS),
        ])
        if not has_any_dialogue:
            continue

        npc_written += 1
        outfile = os.path.join(OUTPUT_FOLDER, f"{safe_filename(npc_name)}_one_liner.txt")
        with open(outfile, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(output_lines).rstrip() + "\n")

    print(f"✅ Wrote {npc_written} NPC files to: {OUTPUT_FOLDER}")
    print(f"✅ Total chat lines written: {total_lines}")


if __name__ == "__main__":
    main()