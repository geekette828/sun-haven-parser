import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils, text_utils  # text_utils kept for consistency with your utils pattern

# Paths
INPUT_PREFAB_PATH = os.path.join(constants.INPUT_DIRECTORY, "English.prefab")

output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted")
file_utils.ensure_dir_exists(output_directory)

# Output files
output_file_path = os.path.join(output_directory, "npc_list.txt")
debug_log_path = os.path.join(".hidden", "debug_output", "npc_list_debug.txt")
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

def split_on_capitals(name):
    """
    Split CamelCase / PascalCase names into words.
    Example: HungrySlime -> Hungry Slime
    """
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', name)

def extract_npc_names_from_english_prefab(prefab_path):
    """
    Extract unique NPC names from English.prefab by scanning for term keys that start with:
    - NPC.<Name>.
    - RNPC.<Name>.
    - TNPC.<Name>.
    """
    if not os.path.exists(prefab_path):
        raise FileNotFoundError(f"English.prefab not found at: {prefab_path}")

    npc_names = set()

    # Match anywhere in a line: NPC.<Name>. or RNPC.<Name>. or TNPC.<Name>.
    # Name is captured as any run of non-dot, non-whitespace characters.
    pattern = re.compile(r"\b(?:NPC|RNPC|TNPC)\.([^\s\.]+)\.")

    with open(prefab_path, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, start=1):
            for m in pattern.finditer(line):
                name = (m.group(1) or "").strip()
                if name:
                    npc_names.add(name)
                else:
                    file_utils.write_debug_log(
                        f"[WARN] Empty name match on line {line_num}: {line.strip()}",
                        debug_log_path
                    )

    return sorted(npc_names, key=lambda x: x.lower())


# Extract and save
npc_list = extract_npc_names_from_english_prefab(INPUT_PREFAB_PATH)
npc_list = [split_on_capitals(name) for name in npc_list]
file_utils.write_lines(output_file_path, [name + "\n" for name in npc_list])

print(f"✅ Extracted {len(npc_list)} unique NPCs from English.prefab.")
print(f"📄 Output saved to: {output_file_path}")
print(f"📝 Debug log saved to: {debug_log_path}")
