"""
All cutscenes exporter — Layer 3 of the pipeline.

Reads Cutscene.cs files from the Scripts directory, localizes dialogue
using English.prefab, and writes one .txt file per cutscene to
Wiki Formatted/Cutscenes/.

Usage:
    python exporters/all_cutscenes.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils import file_utils, text_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_INPUT_DIRECTORY  = os.path.join(constants.INPUT_DIRECTORY, "Scripts")
_OUTPUT_DIRECTORY = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Cutscenes")
_ENGLISH_PREFAB   = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")

# ---------------------------------------------------------------------------
# Localization
# ---------------------------------------------------------------------------

_HARDCODED_KEYS = {"Yes": "Yes", "No": "No"}


def _load_localization(filepath: str) -> dict:
    with open(filepath, encoding="utf-8") as f:
        text = f.read()
    entries = re.findall(
        r'- Term:\s*(.*?)\n\s*TermType:.*?Languages:\s*- (.*?)\n',
        text,
        re.DOTALL,
    )
    return {
        k.strip().strip('"').replace(" ", ""): v.strip().strip('"')
        for k, v in entries
    }


def _localize_key(key: str, localization: dict) -> str:
    if key in _HARDCODED_KEYS:
        return _HARDCODED_KEYS[key]
    lookup_key = key.strip().replace("_", ".")
    return localization.get(lookup_key, f"[Missing text: {key}]")


def _format_line(indent: int, speaker: str, text_key: str, localization: dict) -> str:
    return f"{'    ' * indent}{speaker}: {text_utils.clean_dialogue(_localize_key(text_key, localization))}\n"

# ---------------------------------------------------------------------------
# Dialogue extraction
# ---------------------------------------------------------------------------

def _extract_dialogue(lines: list[str], localization: dict) -> list[str]:
    i = 0
    indent = 0
    current_speaker = "Narrator"
    results: list[str] = []
    option_lookup: dict = {}
    post_option_lines: list[str] = []
    active_case = None

    def add_line(speaker: str, key: str, level: int = 0) -> None:
        results.append(_format_line(level, speaker, key, localization))

    while i < len(lines):
        line = lines[i].strip()

        if "SetDialogueBustVisuals" in line:
            match = re.search(r"SetDialogueBustVisuals\(([^,]+),\s*([a-zA-Z0-9_.]+)", line)
            if match:
                current_speaker = match.group(2).split(".")[-1].capitalize()
            i += 1
            continue

        if "DialogueSingle(" in line and "," in line:
            match = re.findall(r"ScriptLocalization\.([a-zA-Z0-9_]+)", line)
            if len(match) == 2:
                npc_key, player_key = match
                results.append(_format_line(indent, current_speaker, npc_key, localization))
                results.append(_format_line(indent, "Player", player_key, localization))
                i += 1
                continue

        if "DialogueSingleNoResponse" in line:
            key_match = re.search(r"ScriptLocalization\.([a-zA-Z0-9_]+)", line)
            if key_match:
                add_line(current_speaker, key_match.group(1), indent)
            else:
                raw_match = re.search(r'DialogueSingleNoResponse\("([^"]+)"', line)
                if raw_match:
                    add_line(current_speaker, raw_match.group(1), indent)
            i += 1
            continue

        if "DialogueSingle(" in line and "new List<" in line:
            prompt_key_match = re.search(r"ScriptLocalization\.([a-zA-Z0-9_]+)", line)
            prompt_key = prompt_key_match.group(1) if prompt_key_match else None
            if prompt_key:
                add_line(current_speaker, prompt_key, indent)
            i += 1
            options = []
            while i < len(lines) and not lines[i].strip().startswith("}),"):
                opt_line = lines[i].strip()
                key_match = re.findall(r"ScriptLocalization\.([a-zA-Z0-9_]+)", opt_line)
                if key_match:
                    for key in key_match:
                        if "delegate" in opt_line:
                            options.append(key)
                        else:
                            add_line(current_speaker, key, indent)
                i += 1
            for idx, opt in enumerate(options):
                results.append(
                    f"{'    ' * indent}→ Option {idx + 1}: "
                    f"{text_utils.clean_dialogue(_localize_key(opt, localization))}\n"
                )
                option_lookup[f"case {idx + 1}"] = indent + 1
            i += 1
            continue

        response_case = re.match(r"case (\d+):", line)
        if response_case:
            opt = f"case {response_case.group(1)}"
            indent = option_lookup.get(opt, 1)
            results.append(f"{'    ' * (indent - 1)}[If Option {response_case.group(1)}]\n")
            active_case = int(response_case.group(1))
            i += 1
            continue

        if "DialogueSingle(" in line or "DialogueSingleNoResponse" in line:
            key_match = re.search(r"ScriptLocalization\.([a-zA-Z0-9_]+)", line)
            if key_match:
                add_line(current_speaker, key_match.group(1), indent)
            i += 1
            continue

        if "ScriptLocalization." in line:
            key_match = re.search(r"ScriptLocalization\.([a-zA-Z0-9_]+)", line)
            if key_match:
                value = _localize_key(key_match.group(1), localization)
                if key_match.group(1).startswith("Yes") or key_match.group(1).startswith("No"):
                    results.append(
                        f"{'    ' * indent}→ Option "
                        f"{'1' if 'Yes' in key_match.group(1) else '2'}: {value}\n"
                    )
                else:
                    results.append(
                        f"{'    ' * indent}{current_speaker}: "
                        f"{text_utils.clean_dialogue(value)}\n"
                    )
            i += 1
            continue

        if active_case and not line.strip():
            active_case = None
        elif active_case is None and line:
            post_option_lines.append(line)

        i += 1

    for line in post_option_lines:
        key_match = re.search(r"ScriptLocalization\.([a-zA-Z0-9_]+)", line)
        if key_match:
            results.append(_format_line(indent, current_speaker, key_match.group(1), localization))

    return results

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(_OUTPUT_DIRECTORY)
    localization = _load_localization(_ENGLISH_PREFAB)

    for root, _, files in os.walk(_INPUT_DIRECTORY):
        for filename in files:
            if not filename.endswith("Cutscene.cs"):
                continue
            filepath = os.path.join(root, filename)
            lines = file_utils.read_file_lines(filepath)
            dialogue = _extract_dialogue(lines, localization)

            rel_path = os.path.relpath(filepath, _INPUT_DIRECTORY)
            flat_name = rel_path.replace("\\", "/").replace("/", "-").replace(".cs", ".txt")
            flat_name = re.sub(r"^SunHaven\.Core-", "", flat_name, flags=re.IGNORECASE)

            output_path = os.path.join(_OUTPUT_DIRECTORY, flat_name)
            file_utils.write_lines(output_path, dialogue)

    print(f"✅ Cutscene files written to {_OUTPUT_DIRECTORY}")


if __name__ == "__main__":
    run()
