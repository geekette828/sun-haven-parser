import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils import file_utils, text_utils

# Define paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "Scripts")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Cutscenes")
english_prefab_path = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")
file_utils.ensure_dir_exists(output_directory)

# Load localization data from English.prefab
def load_localization_dict(filepath):
    lines = file_utils.read_file_lines(filepath)
    text = "\n".join(lines)
    pattern = r'"(.*?)"\s*:\s*"((?:[^"\\]|\\.)*)"'
    matches = re.findall(pattern, text)
    return {key: val.encode().decode('unicode_escape') for key, val in matches}

localization = load_localization_dict(english_prefab_path)

def localize(key):
    if not key or key.lower() in {"null", "none"}:
        return "Narrator"
    return localization.get(key.strip(), key.strip())

# Extract relevant dialogue lines from .cs content
def extract_cutscene_dialogue(lines):
    results = []
    current_speaker = "Narrator"

    for line in lines:
        line = line.strip()
        if not line or line.startswith("//"):
            continue

        if "SetDialogueBustVisuals" in line:
            match = re.search(r"SetDialogueBustVisuals\([^,]+,\s*([a-zA-Z0-9_.]+)", line)
            if match:
                current_speaker = match.group(1).split('.')[-1]
            continue

        if "SetDefaultBox" in line:
            match = re.search(r"SetDefaultBox\(([^)]+)\)", line)
            if match:
                current_speaker = match.group(1).split('.')[-1]
            continue

        key_match = re.search(r"ScriptLocalization\.([a-zA-Z0-9_]+)", line)
        if key_match:
            results.append((current_speaker, key_match.group(1)))
            continue

        text_match = re.search(r'DialogueSingleNoResponse\("([^"]+)"', line)
        if text_match:
            cleaned = text_utils.clean_dialogue(text_match.group(1))
            results.append((current_speaker, cleaned))

    return results

# Main routine
def main():
    summary = []

    for root, _, files in os.walk(input_directory):
        for filename in files:
            if not filename.endswith("Cutscene.cs"):
                continue

            filepath = os.path.join(root, filename)
            lines = file_utils.read_file_lines(filepath)
            dialogue_lines = extract_cutscene_dialogue(lines)

            out_lines = []
            for speaker_key, text_key in dialogue_lines:
                speaker = localize(speaker_key)
                dialogue = localization.get(text_key.strip(), f"[Missing text: {text_key.strip()}]")
                out_lines.append(f"{speaker}: {text_utils.clean_dialogue(dialogue)}\n")

            rel_path = os.path.relpath(filepath, input_directory)
            flat_name = rel_path.replace("\\", "/").replace("/", "-").replace(".cs", ".txt")
            flat_name = re.sub(r"^SunHaven\.Core-", "", flat_name)

            output_path = os.path.join(output_directory, flat_name)
            file_utils.write_lines(output_path, out_lines)
            summary.append((flat_name, len(out_lines)))

    print("✅ Cutscene dialogue extraction complete:")
    for name, count in summary:
        print(f" - {name}: {count} lines")

if __name__ == "__main__":
    main()