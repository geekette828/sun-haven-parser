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
    with open(filepath, encoding="utf-8") as f:
        text = f.read()
    entries = re.findall(r'- Term:\s*(.*?)\n\s*TermType:.*?Languages:\s*- (.*?)\n', text, re.DOTALL)
    return {k.strip().strip('"').replace(" ", ""): v.strip().strip('"') for k, v in entries}

localization = load_localization_dict(english_prefab_path)

HARDCODED_KEYS = {
    "Yes": "Yes",
    "No": "No"
}

def localize_key(key):
    if key in HARDCODED_KEYS:
        return HARDCODED_KEYS[key]
    lookup_key = key.strip().replace("_", ".")
    return localization.get(lookup_key, f"[Missing text: {key}]")

def format_line(indent, speaker, text_key):
    return f"{'    ' * indent}{speaker}: {text_utils.clean_dialogue(localize_key(text_key))}\n"

def extract_dialogue(lines):
    i = 0
    indent = 0
    current_speaker = "Narrator"
    results = []
    option_lookup = {}
    post_option_lines = []
    active_case = None

    def add_line(speaker, key, level=0):
        results.append(format_line(level, speaker, key))

    while i < len(lines):
        line = lines[i].strip()

        if "SetDialogueBustVisuals" in line:
            match = re.search(r"SetDialogueBustVisuals\(([^,]+),\s*([a-zA-Z0-9_.]+)", line)
            if match:
                npc_field = match.group(2)
                current_speaker = npc_field.split(".")[-1].capitalize()
            i += 1
            continue

        if "DialogueSingle(" in line and "," in line:
            match = re.findall(r"ScriptLocalization\.([a-zA-Z0-9_]+)", line)
            if len(match) == 2:
                npc_key, player_key = match
                results.append(format_line(indent, current_speaker, npc_key))
                results.append(format_line(indent, "Player", player_key))
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
                results.append(f"{'    ' * indent}→ Option {idx + 1}: {text_utils.clean_dialogue(localize_key(opt))}\n")
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
                value = localize_key(key_match.group(1))
                if key_match.group(1).startswith("Yes") or key_match.group(1).startswith("No"):
                    results.append(f"{'    ' * indent}→ Option {1 if 'Yes' in key_match.group(1) else 2}: {value}\n")
                else:
                    results.append(f"{'    ' * indent}{current_speaker}: {text_utils.clean_dialogue(value)}\n")
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
            results.append(format_line(indent, current_speaker, key_match.group(1)))

    return results

def main():
    for root, _, files in os.walk(input_directory):
        for filename in files:
            if not filename.endswith("Cutscene.cs"):
                continue
            filepath = os.path.join(root, filename)
            lines = file_utils.read_file_lines(filepath)
            dialogue = extract_dialogue(lines)

            rel_path = os.path.relpath(filepath, input_directory)
            flat_name = rel_path.replace("\\", "/").replace("/", "-").replace(".cs", ".txt")
            flat_name = re.sub(r"^SunHaven\.Core-", "", flat_name, flags=re.IGNORECASE)

            output_path = os.path.join(output_directory, flat_name)
            file_utils.write_lines(output_path, dialogue)

if __name__ == "__main__":
    main()
