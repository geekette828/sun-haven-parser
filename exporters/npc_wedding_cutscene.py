"""
NPC wedding cutscene exporter — Layer 3 of the pipeline.

Reads English.prefab for Wedding.* terms and writes
_All_Wedding_Dialogue.txt with {{Marriage ceremony}} and {{chat}} wikitext.

Usage:
    python exporters/npc_wedding_cutscene.py
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils.text_utils import clean_game_dialogue, clean_whitespace

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_INPUT_PREFAB = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")
_OUTPUT_FILE  = os.path.join(
    constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Dialogue", "_All_Wedding_Dialogue.txt"
)
_DEBUG_LOG    = os.path.join(constants.DEBUG_DIRECTORY, "wedding_dialogue_missing_titles.log")

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_TERM_SPEECH_RE = re.compile(r"^Wedding\.Speech\.([A-Za-z0-9_]+)$")
_TERM_VOWS_RE   = re.compile(r"^Wedding\.Vows\.([A-Za-z0-9_]+)$")
_TERM_TITLE_RE  = re.compile(r"^Wedding\.Title\.([A-Za-z0-9_]+)$")
_TERM_OL_RE     = re.compile(r"^Wedding\.([A-Za-z0-9_]+)\.OL$")

_SUPPRESS_NAMES = {"GreatCity", "NV", "WG", "BSD"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_debug(message: str) -> None:
    os.makedirs(os.path.dirname(_DEBUG_LOG), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def _unquote_unescape(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
    value = (
        value
        .replace(r"\\", "\\")
        .replace(r"\"", '"')
        .replace(r"\n", "\n")
        .replace(r"\r", "\r")
        .replace(r"\t", "\t")
    )
    return value.strip()


def _clean_text(raw_text: str) -> str:
    return clean_whitespace(clean_game_dialogue(raw_text))


def _parse_wedding_terms(prefab_path: str) -> dict:
    """Return {term: cleaned_english_text} for all Wedding.* terms."""
    if not os.path.exists(prefab_path):
        raise FileNotFoundError(f"Missing prefab file: {prefab_path}")

    term_to_text: dict = {}

    term_line_re      = re.compile(r"^\s*-\s*Term:\s*(.+?)\s*$")
    languages_line_re = re.compile(r"^\s*Languages:\s*$")
    languages_item_re = re.compile(r"^\s*-\s*(.*)\s*$")

    current_term       = None
    want_languages_item = False

    with open(prefab_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            term_match = term_line_re.match(line)
            if term_match:
                current_term        = _unquote_unescape(term_match.group(1))
                want_languages_item = False
                continue

            if not current_term or not current_term.startswith("Wedding."):
                continue

            if languages_line_re.match(line):
                want_languages_item = True
                continue

            if want_languages_item:
                item_match = languages_item_re.match(line)
                if item_match:
                    raw_text = _unquote_unescape(item_match.group(1))
                    term_to_text[current_term] = _clean_text(raw_text)
                    current_term        = None
                    want_languages_item = False

    return term_to_text

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    os.makedirs(os.path.dirname(_OUTPUT_FILE), exist_ok=True)

    term_to_text = _parse_wedding_terms(_INPUT_PREFAB)

    speech_names: set[str] = set()
    vows_names:   set[str] = set()
    title_names:  set[str] = set()
    ol_names:     set[str] = set()

    for term in term_to_text.keys():
        m = _TERM_SPEECH_RE.match(term)
        if m:
            speech_names.add(m.group(1))
            continue
        m = _TERM_VOWS_RE.match(term)
        if m:
            vows_names.add(m.group(1))
            continue
        m = _TERM_TITLE_RE.match(term)
        if m:
            title_names.add(m.group(1))
            continue
        m = _TERM_OL_RE.match(term)
        if m:
            ol_names.add(m.group(1))

    speech_names -= _SUPPRESS_NAMES
    vows_names   -= _SUPPRESS_NAMES
    title_names  -= _SUPPRESS_NAMES
    ol_names     -= _SUPPRESS_NAMES

    ceremony_names  = sorted(speech_names | vows_names | title_names, key=lambda s: s.lower())
    ol_names_sorted = sorted(ol_names, key=lambda s: s.lower())

    output_lines: list[str] = []

    for name in ceremony_names:
        title_text  = term_to_text.get(f"Wedding.Title.{name}")
        speech_text = term_to_text.get(f"Wedding.Speech.{name}", "")
        vows_text   = term_to_text.get(f"Wedding.Vows.{name}", "")

        if not title_text:
            _log_debug(f"Missing wedding title for NPC '{name}'")
            title_text = "MISSING TITLE"

        output_lines.append(f"### {name} ###")
        output_lines.append(f"{{{{Marriage ceremony|{name}")
        output_lines.append(f"|npcTitle = {title_text}")
        output_lines.append(f"|speech = {speech_text}")
        output_lines.append(f"|vows = {vows_text}")
        output_lines.append("}}")
        output_lines.append("")

    output_lines.append("### Guest One-liners")
    for name in ol_names_sorted:
        ol_text = term_to_text.get(f"Wedding.{name}.OL", "")
        if ol_text:
            output_lines.append(f"{{{{chat|{name}|{ol_text}}}}}")

    with open(_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines).rstrip() + "\n")

    print(f"✅ Wrote: {_OUTPUT_FILE}")
    print(f"🛠️ Missing title log: {_DEBUG_LOG}")
    print(f"🔍 Found ceremony NPCs: {len(ceremony_names)}")
    print(f"🔍 Found OL entries: {len(ol_names_sorted)}")


if __name__ == "__main__":
    run()
