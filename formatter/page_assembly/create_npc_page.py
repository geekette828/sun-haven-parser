"""
Generate one .txt NPC page per NPC name.

Inputs:
- Unique NPC list:
  OUTPUT_FILE_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "Unique_NPC_Names_For_Patch.txt")

- Dialogue folder:
  OUTPUT_FOLDER = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Dialogue")
  Files:
    - <NPCNAME>_one_liner.txt
    - <NPCNAME> cycles.txt

Rules:
- Type:
  - Character if cycles exist (non-empty)
  - Texture if only one-liners exist
- One-liners:
  - Strip headers like ===Strangers===, ===Platonic===, etc.
  - Keep only {{chat|...}} lines
- Cycles:
  - Drop the cycles .txt content verbatim into the Conversations section

Output:
- One file per NPC:
  OUTPUT_DIRECTORY/Wiki Formatted/NPC Pages/<NPCNAME>.txt
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import config.constants as constants
from datetime import datetime


TEST_RUN = False

#Paths
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Pages")
dialogue_output_folder = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Dialogue")
schedule_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Schedules")
npc_names_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Unique_NPC_Names_For_Patch.txt")

debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "wiki formatted", "npc_pages_build.log")


TEXTURE_BLURB = (
    "This [[characters|character]] is a texture NPC — a type of non-playable character designed to add depth "
    "and life to the world rather than serve as a major figure in the story. Texture NPCs usually have minimal "
    "dialogue, often just a single line that offers a glimpse into their personality, environment, or the current "
    "season. They might appear or disappear depending on the time of year or specific in-game events, helping the "
    "world feel more dynamic and lived-in."
)

CHARACTER_BLURB = "This [[characters|character]] is an interactable NPC."

def to_title_case(name: str) -> str:
    return " ".join(word.capitalize() for word in name.split())

def get_schedule_file_path(npc_name: str) -> str:
    return os.path.join(schedule_directory, f"{npc_name}_schedule.txt")

def load_schedule_text(npc_name: str) -> str:
    path = get_schedule_file_path(npc_name)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def log_debug(message: str) -> None:
    os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def safe_mkdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def read_text_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def read_npc_names() -> list[str]:
    resolved_path = npc_names_file_path
    log_debug(f"🔍 Using NPC names file: {resolved_path}")

    raw = read_text_file(resolved_path)

    seen_lower = set()
    names = []

    for line in raw.splitlines():
        raw_name = line.strip()
        if not raw_name:
            continue

        title_name = to_title_case(raw_name)
        key = title_name.lower()

        if key in seen_lower:
            continue

        seen_lower.add(key)
        names.append(title_name)

    return sorted(names, key=lambda x: x.lower())


def get_one_liner_file_path(npc_name: str) -> str:
    return os.path.join(dialogue_output_folder, f"{npc_name}_one_liner.txt")


def get_cycles_file_path(npc_name: str) -> str:
    return os.path.join(dialogue_output_folder, f"{npc_name} cycles.txt")


def extract_chat_templates(one_liner_text: str) -> list[str]:
    """
    Keep only lines that contain {{chat|...}}.
    Strip out section headers like ===Strangers===, ===Platonic===, etc.
    """
    chat_lines = []
    for line in one_liner_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("===") and stripped.endswith("==="):
            continue
        if "{{chat|" in stripped:
            chat_lines.append(stripped)
    return chat_lines


def determine_npc_type(cycles_text: str, one_liners: list[str]) -> str:
    if cycles_text.strip():
        return "Character"
    return "Texture"


def build_infobox(npc_type: str) -> str:
    return (
        "{{NPC infobox\n"
        f"|type = {npc_type}\n"
        "|race = \n"
        "|species = \n"
        "|birthday = \n"
        "|gender = \n"
        "|occupation = \n"
        "|region = \n"
        "|residence = \n"
        "|relationships = \n"
        "<!-- Animations -->\n"
        "|blinking = \n"
        "|breathing = \n"
        "|walking =  \n"
        "}}\n"
    )


def build_summary(npc_name: str) -> str:
    return f"'''{npc_name}''' is a character the player can encounter<!--When/Where-->.\n"


def build_type_blurb(npc_type: str) -> str:
    if npc_type == "Texture":
        return TEXTURE_BLURB + "\n"
    return CHARACTER_BLURB + "\n"


def build_schedule(npc_name: str, schedule_text: str) -> str:
    intro = (
        f"{npc_name} currently has only one schedule that they follow, "
        "regardless if it is sunny or rainy.\n"
    )

    if schedule_text:
        return "==Schedule==\n" + intro + schedule_text.strip() + "\n"

    return (
        "==Schedule==\n"
        + intro +
        f"{{{{Schedule |character = {npc_name}\n"
        "|1_name    = General\n"
        "|1_1_time  = 6:00\n"
        "|1_1_info  = \n"
        "}}\n"
    )

def build_quests() -> str:
    return "==Quests==\n{{Quest involves NPC}}\n"


def build_dialogue(one_liners: list[str], cycles_text: str) -> str:
    parts = [
        "==Dialogue==\n",
        "===General Dialogue===\n",
        "General non-conversational dialogue between this character and the player.\n",
    ]

    if one_liners:
        parts.append("\n".join(one_liners).strip() + "\n")

    # Only add Conversations section if cycles exist
    if cycles_text.strip():
        parts.extend([
            "\n===Conversations===\n",
            cycles_text.strip() + "\n",
        ])

    return "".join(parts)


def build_media_trivia_block(npc_name: str) -> str:
    return (
        "<!--==Media==\n"
        '<gallery widths="150" bordercolor="transparent" spacing="small" captionalign="center">\n'
        f"File:{npc_name} location.png|In game representation and location\n"
        "</gallery>\n\n"
        "==Trivia==\n"
        "* \n"
        "-->\n"
    )


def build_history(npc_name: str) -> str:
    patch = constants.PATCH_VERSION.replace("PBE ", "").strip()
    return (
        "==History==\n"
        f"*{{{{History|{patch}|[[{npc_name}]] npc added to the game.}}}}\n"
    )


def build_navbox() -> str:
    return "\n{{NPC navbox}}\n"


def build_page_wikitext(
    npc_name: str,
    one_liners: list[str],
    cycles_text: str,
    schedule_text: str
) -> str:
    npc_type = determine_npc_type(cycles_text, one_liners)

    parts = [
        build_infobox(npc_type),
        "\n",
        build_summary(npc_name),
        "\n",
        build_type_blurb(npc_type),
        "\n",
        build_schedule(npc_name, schedule_text),
        "\n",
        build_quests(),
        "\n",
        build_dialogue(one_liners, cycles_text),
        "\n",
        build_media_trivia_block(npc_name),
        "\n",
        build_history(npc_name),
        "\n",
        build_navbox(),
    ]
    return "".join(parts).strip() + "\n"

def write_output_file(npc_name: str, text: str) -> str:
    safe_mkdir(output_directory)
    file_path = os.path.join(output_directory, f"{npc_name}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    return file_path


def main() -> None:
    log_debug("🔄 Starting NPC page generation...")

    safe_mkdir(output_directory)

    npc_names = read_npc_names()
    log_debug(f"🔍 NPC names loaded: {len(npc_names)}")

    created = 0
    missing_one_liners = 0
    missing_cycles = 0
    missing_schedules = 0

    for npc_name in npc_names:
        one_liner_path = get_one_liner_file_path(npc_name)
        cycles_path = get_cycles_file_path(npc_name)
        schedule_path = get_schedule_file_path(npc_name)

        one_liner_text = read_text_file(one_liner_path)
        cycles_text = read_text_file(cycles_path)
        schedule_text = load_schedule_text(npc_name)

        if not one_liner_text:
            missing_one_liners += 1
            log_debug(f"🛠️ Missing one-liner file for {npc_name}: {one_liner_path}")

        if not cycles_text:
            missing_cycles += 1
            log_debug(f"🛠️ Missing cycles file for {npc_name}: {cycles_path}")

        if not schedule_text:
            missing_schedules += 1
            log_debug(f"🛠️ No schedule file for {npc_name}, using default schedule.")

        one_liners = extract_chat_templates(one_liner_text)

        if one_liner_text and not one_liners:
            log_debug(
                f"🛠️ No {{chat|...}} lines found in one-liner file for {npc_name}: {one_liner_path}"
            )

        page_text = build_page_wikitext(
            npc_name=npc_name,
            one_liners=one_liners,
            cycles_text=cycles_text,
            schedule_text=schedule_text,
        )

        out_path = write_output_file(npc_name, page_text)
        created += 1
        log_debug(f"✅ Wrote NPC page: {out_path}")

    log_debug(
        f"✅ Done. Pages created: {created}, "
        f"Missing one-liners: {missing_one_liners}, "
        f"Missing cycles: {missing_cycles}, "
        f"Missing schedules: {missing_schedules}"
    )

    log_debug("🔄 Starting NPC page generation...")

    if not os.path.exists(dialogue_output_folder):
        log_debug(f"🛠️ Dialogue folder does not exist: {dialogue_output_folder}")
        print(f"ERROR: Dialogue folder does not exist: {dialogue_output_folder}")
        return

    safe_mkdir(output_directory)

    npc_names = read_npc_names()
    log_debug(f"🔍 NPC names loaded: {len(npc_names)}")
    print(f"NPC names loaded: {len(npc_names)}")

    if not npc_names:
        log_debug("🛠️ NPC name list is empty. Nothing to do.")
        print("No NPC names loaded. Nothing to do.")
        return

    created = 0
    skipped = 0
    missing_one_liners = 0
    missing_cycles = 0

    for npc_name in npc_names:
        one_liner_path = get_one_liner_file_path(npc_name)
        cycles_path = get_cycles_file_path(npc_name)

        one_liner_text = read_text_file(one_liner_path)
        cycles_text = read_text_file(cycles_path)

        if not one_liner_text and not cycles_text:
            skipped += 1
            log_debug(f"🛠️ Skipping {npc_name}: missing both dialogue files.")
            continue

        if not one_liner_text:
            missing_one_liners += 1
            log_debug(f"🛠️ Missing one-liner file for {npc_name}: {one_liner_path}")

        if not cycles_text:
            missing_cycles += 1
            log_debug(f"🛠️ Missing cycles file for {npc_name}: {cycles_path}")

        one_liners = extract_chat_templates(one_liner_text)

        if one_liner_text and not one_liners:
            log_debug(f"🛠️ No {{chat|...}} lines found in one-liner file for {npc_name}: {one_liner_path}")

        schedule_text = load_schedule_text(npc_name)

        page_text = build_page_wikitext(
            npc_name,
            one_liners,
            cycles_text,
            schedule_text
        )

        if TEST_RUN:
            log_debug(f"📝 TEST_RUN: Built page for {npc_name} (not writing file).")
            continue

        out_path = write_output_file(npc_name, page_text)
        created += 1
        log_debug(f"✅ Wrote: {out_path}")

    summary = (
        f"Done. Created: {created}, Skipped: {skipped}, "
        f"Missing one-liners: {missing_one_liners}, Missing cycles: {missing_cycles}"
    )
    log_debug(f"✅ {summary}")
    print(summary)

    log_debug("🔄 Starting NPC page generation...")

    safe_mkdir(output_directory)

    npc_names = read_npc_names()
    log_debug(f"🔍 NPC names loaded: {len(npc_names)}")

    created = 0
    skipped = 0
    missing_one_liners = 0
    missing_cycles = 0

    for npc_name in npc_names:
        one_liner_path = get_one_liner_file_path(npc_name)
        cycles_path = get_cycles_file_path(npc_name)

        one_liner_text = read_text_file(one_liner_path)
        cycles_text = read_text_file(cycles_path)

        if not one_liner_text and not cycles_text:
            log_debug(f"🛠️ No dialogue files found for {npc_name}. Generating Texture page anyway.")

        if not one_liner_text:
            missing_one_liners += 1
            log_debug(f"🛠️ Missing one-liner file for {npc_name}: {one_liner_path}")

        if not cycles_text:
            missing_cycles += 1
            log_debug(f"🛠️ Missing cycles file for {npc_name}: {cycles_path}")

        one_liners = extract_chat_templates(one_liner_text)

        if one_liner_text and not one_liners:
            log_debug(f"🛠️ No {{chat|...}} lines found in one-liner file for {npc_name}: {one_liner_path}")

        schedule_text = load_schedule_text(npc_name)

        page_text = build_page_wikitext(
            npc_name,
            one_liners,
            cycles_text,
            schedule_text
        )

        if TEST_RUN:
            log_debug(f"📝 TEST_RUN: Built page for {npc_name} (not writing file).")
            continue

        out_path = write_output_file(npc_name, page_text)
        created += 1
        log_debug(f"✅ Wrote: {out_path}")

    log_debug(
        f"✅ Done. Created: {created}, Skipped: {skipped}, "
        f"Missing one-liners: {missing_one_liners}, Missing cycles: {missing_cycles}"
    )


if __name__ == "__main__":
    main()
