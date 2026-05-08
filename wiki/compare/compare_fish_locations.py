"""
Fish locations compare — wiki vs. data.

Fetches all wiki pages that use {{Fish locations}}, parses the template,
and compares against values computed from fish_spawner_data.json + items_data.json.

Output mirrors compare_item_infobox.py:
  - Mismatches  (fish with differing entries between data and wiki)
  - Data Only   (fish in our data but no {{Fish locations}} template on wiki)
  - Wiki Only   (wiki has {{Fish locations}} but no matching entry in our data)

Usage:
    python wiki/compare/compare_fish_locations.py
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import re

import mwparserfromhell

import config.constants as constants
from builders.item_builder import _load_cache
from utils import json_utils, file_utils, wiki_utils
from exporters.fish_spawn_chance import _SCENE_LOCATION_MAPPING, _compute_location_rows

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_FISH_DATA   = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "fish_spawner_data.json")
_OUTPUT_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "fish_locations_compare.txt")
_DEBUG_LOG   = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "fish_locations_compare_debug.txt")

TEST_RUN   = False
TEST_PAGES = ["Blazing Herring", "Angel Fish", "Turkeyfish"]

BATCH_SIZE     = constants.PWB_SETTINGS["BATCH_SIZE"]
SLEEP_INTERVAL = constants.PWB_SETTINGS["SLEEP_INTERVAL"]

# ---------------------------------------------------------------------------
# Expected data builder
# ---------------------------------------------------------------------------

def _build_expected_data(
    fish_spawner_data: dict,
    items_by_name: dict,
) -> dict[str, set[tuple]]:
    """
    Compute expected (location, season, min, max) entries per fish from
    scene data, using the same logic as the exporter.

    Returns: { fish_name (original case): {(location, season, min, max), ...} }
    """
    fish_to_entries: dict[str, set] = {}

    for scene_name, location_name in _SCENE_LOCATION_MAPPING.items():
        scene_data = fish_spawner_data.get(scene_name)
        if not scene_data:
            continue

        for row in _compute_location_rows(scene_data, items_by_name, location_name):
            entry = (row["location"], row["season"], row["min"], row["max"])
            fish_to_entries.setdefault(row["fish"], set()).add(entry)

    return fish_to_entries

# ---------------------------------------------------------------------------
# Wiki template parser
# ---------------------------------------------------------------------------

def _parse_fish_locations(wikitext: str) -> set[tuple] | None:
    """
    Extract all (location, season, min, max) entries from the first
    {{Fish locations}} template found in wikitext.

    Returns None if the template is not present on the page.
    """
    code = mwparserfromhell.parse(wikitext)

    for tpl in code.filter_templates():
        if tpl.name.strip().lower() == "fish locations":
            params = {
                p.name.strip(): re.sub(r"<!--.*?-->", "", str(p.value), flags=re.DOTALL).strip()
                for p in tpl.params
            }
            entries: set[tuple] = set()
            i = 1
            while f"{i}_location" in params:
                location = params.get(f"{i}_location", "")
                season   = params.get(f"{i}_season", "")
                min_raw  = params.get(f"{i}_min", "").rstrip("%")
                max_raw  = params.get(f"{i}_max", "").rstrip("%")
                try:
                    min_val = round(float(min_raw), 2)
                    max_val = round(float(max_raw), 2)
                except ValueError:
                    min_val = min_raw
                    max_val = max_raw
                entries.add((location, season, min_val, max_val))
                i += 1
            return entries

    return None

# ---------------------------------------------------------------------------
# Comparison helper
# ---------------------------------------------------------------------------

def _compare_entries(
    expected: set[tuple],
    actual: set[tuple],
) -> tuple[list, list, list]:
    """
    Compare two sets of (location, season, min, max) tuples.

    Returns:
      data_only  — entries present in expected but missing from wiki
      wiki_only  — entries present on wiki but not in our data
      value_diff — (location, season) matches but min/max differ:
                   [(location, season, exp_min, exp_max, act_min, act_max), ...]
    """
    exp_by_key = {(loc, season): (mn, mx) for loc, season, mn, mx in expected}
    act_by_key = {(loc, season): (mn, mx) for loc, season, mn, mx in actual}

    data_only: list  = []
    wiki_only: list  = []
    value_diff: list = []

    for key, (exp_min, exp_max) in exp_by_key.items():
        if key not in act_by_key:
            data_only.append((*key, exp_min, exp_max))
        else:
            act_min, act_max = act_by_key[key]
            if (exp_min, exp_max) != (act_min, act_max):
                value_diff.append((*key, exp_min, exp_max, act_min, act_max))

    for key, (act_min, act_max) in act_by_key.items():
        if key not in exp_by_key:
            wiki_only.append((*key, act_min, act_max))

    return data_only, wiki_only, value_diff

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_OUTPUT_FILE))
    file_utils.ensure_dir_exists(os.path.dirname(_DEBUG_LOG))

    # Build expected data from scene JSON + items cache
    fish_spawner_data = json_utils.load_json(_FISH_DATA)
    items             = _load_cache()
    items_by_name     = {item.name: item for item in items.values()}
    expected_data     = _build_expected_data(fish_spawner_data, items_by_name)

    # Build a lowercase lookup for matching wiki page titles
    expected_lower = {name.lower(): name for name in expected_data}

    # Fetch wiki pages
    pages = TEST_PAGES if TEST_RUN else wiki_utils.get_pages_with_template("Fish locations")

    total     = len(pages)
    processed = 0

    mismatches:  list = []
    data_only:   list = sorted(expected_data.keys())   # remove as we find wiki matches
    wiki_only:   list = []
    debug_lines: list = []

    for i in range(0, total, BATCH_SIZE):
        batch      = pages[i : i + BATCH_SIZE]
        page_texts = wiki_utils.fetch_pages(batch, batch_size=BATCH_SIZE)

        for title in batch:
            processed += 1
            text      = page_texts.get(title, "")
            title_key = title.lower()

            wiki_entries = _parse_fish_locations(text)

            if wiki_entries is None:
                # Page exists but has no {{Fish locations}} template
                wiki_only.append(title)
                debug_lines.append(f"[NO TEMPLATE] {title}")
                continue

            if title_key not in expected_lower:
                # Wiki has template but we have no data for this fish
                wiki_only.append(title)
                debug_lines.append(f"[WIKI ONLY] {title}")
                continue

            # Found a match — remove from data_only tracking
            canonical = expected_lower[title_key]
            if canonical in data_only:
                data_only.remove(canonical)

            d_only, w_only, v_diff = _compare_entries(
                expected_data[canonical], wiki_entries
            )

            if d_only or w_only or v_diff:
                mismatches.append((title, d_only, w_only, v_diff))
                debug_lines.append(f"[MISMATCH] {title}")
                for loc, season, mn, mx in d_only:
                    debug_lines.append(f"    [MISSING FROM WIKI] {loc} | {season}: {mn}% → {mx}%")
                for loc, season, mn, mx in w_only:
                    debug_lines.append(f"    [EXTRA ON WIKI] {loc} | {season}: {mn}% → {mx}%")
                for loc, season, emn, emx, amn, amx in v_diff:
                    debug_lines.append(
                        f"    [WRONG VALUES] {loc} | {season}: "
                        f"expected {emn}%→{emx}%, found {amn}%→{amx}%"
                    )
            else:
                debug_lines.append(f"[MATCH] {title}")

        if i // BATCH_SIZE % 10 == 0:
            percent = round((processed / total) * 100, 1)
            print(
                f"     🔄 Reviewed {processed} of {total} pages "
                f"({percent}% complete). Sleeping {SLEEP_INTERVAL} seconds."
            )
            if not TEST_RUN:
                time.sleep(SLEEP_INTERVAL)

    # Write report
    with open(_OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("=== Mismatches ===\n")
        for title, d_only, w_only, v_diff in mismatches:
            out.write(f"{title}\n")
            for loc, season, mn, mx in sorted(d_only):
                out.write(f"    - [MISSING FROM WIKI] {loc} | {season}: {mn}% → {mx}%\n")
            for loc, season, mn, mx in sorted(w_only):
                out.write(f"    - [EXTRA ON WIKI] {loc} | {season}: {mn}% → {mx}%\n")
            for loc, season, emn, emx, amn, amx in sorted(v_diff):
                out.write(
                    f"    - [WRONG VALUES] {loc} | {season}: "
                    f"expected {emn}%→{emx}%, found {amn}%→{amx}%\n"
                )
            out.write("\n")

        out.write("=== Data Only ===\n")
        for name in sorted(data_only, key=str.lower):
            out.write(f"{name}\n")

        out.write("\n=== Wiki Only ===\n")
        for name in sorted(wiki_only, key=str.lower):
            out.write(f"{name}\n")

    with open(_DEBUG_LOG, "w", encoding="utf-8") as dbg:
        dbg.write("\n".join(debug_lines))

    print(f"✅ Fish locations comparison complete. See: {_OUTPUT_FILE}")


if __name__ == "__main__":
    run()
