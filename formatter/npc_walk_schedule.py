import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
import re
from collections import defaultdict
from mappings.location_mapping import LOCATION_LINKS, PERSONAL_TERMS
from utils import file_utils

# Testing Config
testing = False
test_npc_name = "Claude"  # Case-sensitive match (e.g., "Claude")

# Paths
input_directory = os.path.join(constants.INPUT_DIRECTORY, "MonoBehaviour")
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "NPC Schedules")
file_utils.ensure_dir_exists(output_directory)

debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "npc_path_debug.txt")
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

def format_hour_to_time(hour_str):
    try:
        hour = float(hour_str)
        h = int(hour)
        m = int((hour - h) * 60)
        return f"{h}:{m:02}"
    except:
        return hour_str

def apply_location_links(info, npc_name):
    def get_link_spans(s):
        return [(m.start(), m.end()) for m in re.finditer(r"\[\[.*?\]\]", s)]

    def is_within_links(index, spans):
        return any(start <= index < end for start, end in spans)

    for phrase, mapping in LOCATION_LINKS.items():
        pattern = re.compile(rf'\b{re.escape(phrase)}\b', re.IGNORECASE)
        info = pattern.sub(
            lambda m: f"[[{mapping['link']}|{mapping.get('display', m.group(0))}]]"
            if 'display' in mapping else f"[[{mapping['link']}]]",
            info
        )

    link_spans = get_link_spans(info)

    if npc_name in PERSONAL_TERMS:
        for phrase, link in PERSONAL_TERMS[npc_name].items():
            pattern = re.compile(rf'\b{re.escape(phrase)}\b', re.IGNORECASE)
            matches = list(pattern.finditer(info))
            for match in reversed(matches):
                if is_within_links(match.start(), link_spans):
                    continue
                info = info[:match.start()] + link + info[match.end():]
                link_spans = get_link_spans(info)

    return info

def clean_info(text, npc_name=None, group_label=None):
    text = text.lstrip("-").strip().strip('"').strip("'").strip()
    text = text[:1].upper() + text[1:]
    text = text.rstrip(" .") + "."

    def get_link_spans(s):
        return [(m.start(), m.end()) for m in re.finditer(r"\[\[.*?\]\]", s)]

    def is_within_links(index, spans):
        return any(start <= index < end for start, end in spans)

    if group_label and group_label.lower().startswith("married"):
        link_spans = get_link_spans(text)

        # Replace "<pronoun> house/home"
        pattern1 = re.compile(r'\b(their|his|her) (house|home)\b', re.IGNORECASE)
        for match in reversed(list(pattern1.finditer(text))):
            if not is_within_links(match.start(), link_spans):
                text = text[:match.start()] + '[[Home Sweet Home|Player\'s House]]' + text[match.end():]
                link_spans = get_link_spans(text)

        # Replace just "house" and "home"
        for word in ["house", "home"]:
            pattern2 = re.compile(rf'\b{word}\b', re.IGNORECASE)
            for match in reversed(list(pattern2.finditer(text))):
                if not is_within_links(match.start(), link_spans):
                    text = text[:match.start()] + '[[Home Sweet Home|Player\'s House]]' + text[match.end():]
                    link_spans = get_link_spans(text)

    if npc_name:
        text = apply_location_links(text, npc_name)

    return text

def parse_block_lines(block_lines):
    result = []
    for line in block_lines:
        if "— hour " in line:
            name_part, hour = line.split("— hour ")
            result.append((name_part.strip(), hour.strip()))
    return result

def extract_schedule_key(lines):
    return "\n".join(lines)

def add_schedule_block(title, entries, group_id, schedule_lines, npc_name):
    schedule_lines.append(f"|{group_id}_name    = {title}")
    for i, (info, hour) in enumerate(entries, start=1):
        time_str = format_hour_to_time(hour)
        cleaned = clean_info(info, npc_name, title)
        schedule_lines.append(f"|{group_id}_{i}_time  = {time_str}")
        schedule_lines.append(f"|{group_id}_{i}_info  = {cleaned}")
    return group_id + 1

def group_blocks_by_similarity(path_list):
    block_groups = defaultdict(list)
    for fname, lines in path_list:
        key = extract_schedule_key(lines)
        block_groups[key].append(fname)
    return block_groups

def get_dominant_block(block_groups):
    return max(block_groups.items(), key=lambda x: len(x[1]))

def label_from_season(fname):
    match = re.search(r'_(Spring|Summer|Fall|Winter)', fname)
    return match.group(1) if match else "Spring"

def add_grouped_blocks(label, path_list, group_id, schedule_lines, npc_name):
    block_groups = group_blocks_by_similarity(path_list)
    if len(block_groups) == 1:
        block = next(iter(block_groups))
        parsed = parse_block_lines(block.splitlines())
        return add_schedule_block(label, parsed, group_id, schedule_lines, npc_name)

    dominant_block, filenames = get_dominant_block(block_groups)
    parsed_dominant = parse_block_lines(dominant_block.splitlines())
    group_id = add_schedule_block(label, parsed_dominant, group_id, schedule_lines, npc_name)

    for blk, others in block_groups.items():
        if blk == dominant_block:
            continue
        season = label_from_season(others[0])
        parsed = parse_block_lines(blk.splitlines())
        group_id = add_schedule_block(f"{label} ({season})", parsed, group_id, schedule_lines, npc_name)

    return group_id

path_files = [
    f for f in os.listdir(input_directory)
    if "Path" in f and f.endswith(".asset") and "walkpath" not in f.lower()
]

grouped_by_npc = defaultdict(list)
for filename in path_files:
    npc_name = filename.split("Path")[0]
    grouped_by_npc[npc_name].append(filename)

debug_lines = []

for npc, files in grouped_by_npc.items():
    if testing and npc != test_npc_name:
        continue

    paths = defaultdict(list)
    debug_groups = defaultdict(list)

    for filename in sorted(files):
        file_path = os.path.join(input_directory, filename)
        try:
            content = file_utils.read_file_lines(file_path)
            joined = "\n".join(content)
            matches = re.findall(r"- name: (.*?)\s+hour: ([0-9.]+)", joined)
            if matches:
                path_lines = [f"- {name} — hour {hour}" for name, hour in matches]
                key = filename.replace(".asset", "")
                paths[key].append((filename.replace(".asset", ""), path_lines))
                debug_groups["\n".join(path_lines)].append(filename.replace(".asset", ""))
        except Exception as e:
            file_utils.append_line(debug_log_path, f"[ERROR] Failed to parse {filename}: {e}")

    schedule_lines = [f"{{{{Schedule |character = {npc}"]
    group_id = 1

    def collect(filter_fn):
        return [(name, lines) for name, entries in paths.items() for _, lines in entries if filter_fn(name)]

    generalA = collect(lambda n: "PathA" in n and "Married" not in n)
    generalB = collect(lambda n: "PathB" in n and "Married" not in n)

    def same_block(list1, list2):
        return extract_schedule_key(list1[0][1]) == extract_schedule_key(list2[0][1])

    if generalA and generalB and same_block(generalA, generalB):
        group_id = add_grouped_blocks("General", generalA, group_id, schedule_lines, npc)
    else:
        if generalA:
            group_id = add_grouped_blocks("General (A)", generalA, group_id, schedule_lines, npc)
        if generalB:
            group_id = add_grouped_blocks("General (B)", generalB, group_id, schedule_lines, npc)

    married = collect(lambda n: "Married" in n and "Rain" not in n)
    if married:
        group_id = add_grouped_blocks("Married", married, group_id, schedule_lines, npc)

    married_rain = collect(lambda n: "Rain" in n and "Married" in n)
    if married_rain:
        base_married_block = group_blocks_by_similarity(married)
        rain_blocks = group_blocks_by_similarity(married_rain)
        if any(rb not in base_married_block for rb in rain_blocks):
            for blk in rain_blocks:
                if blk not in base_married_block:
                    parsed = parse_block_lines(blk.splitlines())
                    group_id = add_schedule_block("Married (Raining)", parsed, group_id, schedule_lines, npc)

    rain = collect(lambda n: "Rain" in n and "Married" not in n)
    if rain:
        general_blocks = collect(lambda n: ("PathA" in n or "PathB" in n) and "Married" not in n)
        rain_blocks = group_blocks_by_similarity(rain)
        general_blocks_grouped = group_blocks_by_similarity(general_blocks)

        if list(rain_blocks.keys()) == list(general_blocks_grouped.keys()):
            # Raining is identical to General – no need to re-add
            pass
        else:
            group_id = add_grouped_blocks("Raining", rain, group_id, schedule_lines, npc)

    locked = collect(lambda n: "Locked" in n)
    for fname, lines in locked:
        parsed = parse_block_lines(lines)
        group_id = add_schedule_block("Locked", parsed, group_id, schedule_lines, npc)

    schedule_lines.append("}}")
    output_path = os.path.join(output_directory, f"{npc}_schedule.txt")
    file_utils.write_lines(output_path, [line + "\n" for line in schedule_lines])

    debug_lines.append(f"### {npc}")
    for block, filenames in debug_groups.items():
        debug_lines.append(f"Paths: {', '.join(filenames)}")
        debug_lines.append(block)
        debug_lines.append("")

if debug_lines:
    file_utils.write_lines(debug_log_path, [line + "\n" for line in debug_lines])

print(f"✅ NPC schedules written to: {output_directory}")
