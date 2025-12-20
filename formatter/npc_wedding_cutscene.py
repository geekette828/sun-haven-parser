import os
import sys
import re
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils.text_utils import clean_game_dialogue, clean_whitespace

# Paths
INPUT_PREFAB_FILE = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")
OUTPUT_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Dialogue", "_All_Wedding_Dialogue.txt")
DEBUG_LOG_PATH = os.path.join(constants.DEBUG_DIRECTORY, "wedding_dialogue_missing_titles.log")


TERM_SPEECH_RE = re.compile(r"^Wedding\.Speech\.([A-Za-z0-9_]+)$")
TERM_VOWS_RE = re.compile(r"^Wedding\.Vows\.([A-Za-z0-9_]+)$")
TERM_TITLE_RE = re.compile(r"^Wedding\.Title\.([A-Za-z0-9_]+)$")
TERM_OL_RE = re.compile(r"^Wedding\.([A-Za-z0-9_]+)\.OL$")

SUPPRESS_NAMES = {"GreatCity", "NV", "WG", "BSD"}

def log_debug(message: str) -> None:
    os.makedirs(os.path.dirname(DEBUG_LOG_PATH), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def _unquote_unescape(value: str) -> str:
    if value is None:
        return ""

    value = value.strip()

    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]

    value = value.replace(r"\\", "\\")
    value = value.replace(r"\"", '"')
    value = value.replace(r"\n", "\n")
    value = value.replace(r"\r", "\r")
    value = value.replace(r"\t", "\t")

    return value.strip()


def _clean_text(raw_text: str) -> str:
    cleaned = clean_game_dialogue(raw_text)
    cleaned = clean_whitespace(cleaned)
    return cleaned


def parse_wedding_terms(prefab_path: str) -> dict:
    """
    Return dict: term -> cleaned_text

    English.prefab stores the English string under 'Languages:' as the first list item.
    """
    if not os.path.exists(prefab_path):
        raise FileNotFoundError(f"Missing prefab file: {prefab_path}")

    term_to_text = {}

    term_line_re = re.compile(r"^\s*-\s*Term:\s*(.+?)\s*$")
    languages_line_re = re.compile(r"^\s*Languages:\s*$")
    languages_item_re = re.compile(r"^\s*-\s*(.*)\s*$")

    current_term = None
    want_languages_item = False

    with open(prefab_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            term_match = term_line_re.match(line)
            if term_match:
                current_term = _unquote_unescape(term_match.group(1))
                want_languages_item = False
                continue

            if not current_term:
                continue

            # Only parse wedding keys
            if not current_term.startswith("Wedding."):
                continue

            if languages_line_re.match(line):
                want_languages_item = True
                continue

            if want_languages_item:
                item_match = languages_item_re.match(line)
                if item_match:
                    raw_text = _unquote_unescape(item_match.group(1))
                    term_to_text[current_term] = _clean_text(raw_text)

                    current_term = None
                    want_languages_item = False

    return term_to_text


def main() -> None:
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    term_to_text = parse_wedding_terms(INPUT_PREFAB_FILE)

    # Gather NPC names
    speech_names = set()
    vows_names = set()
    title_names = set()
    ol_names = set()

    for term in term_to_text.keys():
        m = TERM_SPEECH_RE.match(term)
        if m:
            speech_names.add(m.group(1))
            continue

        m = TERM_VOWS_RE.match(term)
        if m:
            vows_names.add(m.group(1))
            continue

        m = TERM_TITLE_RE.match(term)
        if m:
            title_names.add(m.group(1))
            continue

        m = TERM_OL_RE.match(term)
        if m:
            ol_names.add(m.group(1))
            continue

    # Suppress unwanted pseudo-names
    speech_names -= SUPPRESS_NAMES
    vows_names -= SUPPRESS_NAMES
    title_names -= SUPPRESS_NAMES
    ol_names -= SUPPRESS_NAMES

    ceremony_names = sorted((speech_names | vows_names | title_names), key=lambda s: s.lower())
    ol_names_sorted = sorted(ol_names, key=lambda s: s.lower())

    output_lines = []

    for name in ceremony_names:
        title_term = f"Wedding.Title.{name}"
        speech_term = f"Wedding.Speech.{name}"
        vows_term = f"Wedding.Vows.{name}"

        title_text = term_to_text.get(title_term)
        speech_text = term_to_text.get(speech_term, "")
        vows_text = term_to_text.get(vows_term, "")

        if not title_text:
            log_debug(f"Missing wedding title for NPC '{name}' (term {title_term})")
            title_text = "MISSING TITLE"

        output_lines.append(f"### {name} ###")
        output_lines.append(f"{{{{Marriage ceremony|{name}")
        output_lines.append(f"|npcTitle = {title_text}")
        output_lines.append(f"|speech = {speech_text}")
        output_lines.append(f"|vows = {vows_text}")
        output_lines.append("}}")
        output_lines.append("")

    # OL header + chats
    output_lines.append("### Guest One-liners")
    for name in ol_names_sorted:
        ol_term = f"Wedding.{name}.OL"
        ol_text = term_to_text.get(ol_term, "")
        if ol_text:
            output_lines.append(f"{{{{chat|{name}|{ol_text}}}}}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines).rstrip() + "\n")

    print(f"✅ Wrote: {OUTPUT_FILE}")
    print(f"🛠️ Missing title log: {DEBUG_LOG_PATH}")
    print(f"🔍 Found ceremony NPCs: {len(ceremony_names)}")
    print(f"🔍 Found OL entries: {len(ol_names_sorted)}")


if __name__ == "__main__":
    main()