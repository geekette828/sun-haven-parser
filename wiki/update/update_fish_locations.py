"""
Fish locations updater — wiki update script.

Fetches all wiki pages that use {{Fish locations}}, compares against values
computed from fish_spawner_data.json + items_data.json, and updates pages
where the template differs.

Usage:
    python wiki/update/update_fish_locations.py
    python wiki/update/update_fish_locations.py -- "Blazing Herring" "Angel Fish"
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import re

import mwparserfromhell
import pywikibot

import config.constants as constants
from builders.item_builder import _load_cache
from utils import json_utils, file_utils, wiki_utils
from exporters.fish_spawn_chance import _SCENE_LOCATION_MAPPING, _compute_location_rows

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

DRY_RUN = False  # Set False to actually save edits

ARG_PAGES = [a.lstrip("-") for a in sys.argv[1:] if a.lstrip("-")]

_FISH_DATA   = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "fish_spawner_data.json")
_OUTPUT_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "fish_locations_update.txt")
_DEBUG_LOG   = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "fish_locations_update_debug.txt")

BATCH_SIZE     = constants.PWB_SETTINGS["BATCH_SIZE"]
SLEEP_INTERVAL = constants.PWB_SETTINGS["SLEEP_INTERVAL"]

# ---------------------------------------------------------------------------
# Data builder
# ---------------------------------------------------------------------------

def _build_fish_rows(
    fish_spawner_data: dict,
    items_by_name: dict,
) -> dict[str, list[dict]]:
    """
    Build a per-fish list of {location, season, min, max} row dicts,
    de-duplicating identical entries that arise from multiple scenes
    mapping to the same location.

    Returns: { fish_name: [{location, season, min, max}, ...] }
    """
    fish_to_rows: dict[str, list[dict]] = {}

    for scene_name, location_name in _SCENE_LOCATION_MAPPING.items():
        scene_data = fish_spawner_data.get(scene_name)
        if not scene_data:
            continue

        for row in _compute_location_rows(scene_data, items_by_name, location_name):
            entry = {
                "location": row["location"],
                "season":   row["season"],
                "min":      row["min"],
                "max":      row["max"],
            }
            existing = fish_to_rows.setdefault(row["fish"], [])
            if entry not in existing:
                existing.append(entry)

    return fish_to_rows


# ---------------------------------------------------------------------------
# Template builder
# ---------------------------------------------------------------------------

def _build_template(fish_name: str, rows: list[dict]) -> str:
    """
    Build the {{Fish locations}} wikitext for a given fish.

    Year-round fish at seasonal locations get an "Any" entry AND a per-season
    entry.  The "Any" entry is wrapped in a comment so it is hidden in the UI
    but remains visible in the raw wikitext.  Fish whose only entry is "Any"
    (no seasonal variation at that location) are left uncommented.
    """
    sorted_rows = sorted(
        rows,
        key=lambda r: (r["location"], r["season"] == "Any", r["season"]),
    )

    locations_with_seasons = {r["location"] for r in sorted_rows if r["season"] != "Any"}
    active_rows  = [r for r in sorted_rows if not (r["season"] == "Any" and r["location"] in locations_with_seasons)]
    comment_rows = [r for r in sorted_rows if      r["season"] == "Any" and r["location"] in locations_with_seasons]

    lines = ["{{Fish locations"]
    lines.append(f"|name = {fish_name}")

    for idx, row in enumerate(active_rows, start=1):
        lines.append(f"|{idx}_location = {row['location']}")
        lines.append(f"   |{idx}_season = {row['season']}")
        lines.append(f"   |{idx}_min = {row['min']}")
        lines.append(f"   |{idx}_max = {row['max']}")

    for row in comment_rows:
        idx = len(active_rows) + comment_rows.index(row) + 1
        lines.append(f"<!-- |{idx}_location = {row['location']}")
        lines.append(f"   |{idx}_season = {row['season']}")
        lines.append(f"   |{idx}_min = {row['min']}")
        lines.append(f"   |{idx}_max = {row['max']} -->")

    lines.append("}}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Wiki template parser (mirrors compare script)
# ---------------------------------------------------------------------------

def _parse_wiki_entries(wikitext: str) -> set[tuple] | None:
    """
    Extract the active (non-commented) (location, season, min, max) entries
    from the first {{Fish locations}} template.  Returns None if not present.
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
# Template replacer
# ---------------------------------------------------------------------------

def _replace_template(text: str, new_template: str) -> str:
    """Swap the existing {{Fish locations}} template for new_template."""
    code = mwparserfromhell.parse(text)
    for tpl in code.filter_templates():
        if tpl.name.strip().lower() == "fish locations":
            code.replace(tpl, new_template)
            return str(code)
    return text


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_OUTPUT_FILE))
    file_utils.ensure_dir_exists(os.path.dirname(_DEBUG_LOG))

    # Build expected data
    fish_spawner_data = json_utils.load_json(_FISH_DATA)
    items             = _load_cache()
    items_by_name     = {item.name: item for item in items.values()}
    fish_to_rows      = _build_fish_rows(fish_spawner_data, items_by_name)
    expected_lower    = {name.lower(): name for name in fish_to_rows}

    # Build expected active-entry sets for comparison (excludes commented Any rows)
    expected_active: dict[str, set[tuple]] = {}
    for fish_name, rows in fish_to_rows.items():
        locations_with_seasons = {r["location"] for r in rows if r["season"] != "Any"}
        active_rows = [r for r in rows if not (r["season"] == "Any" and r["location"] in locations_with_seasons)]
        expected_active[fish_name] = {
            (r["location"], r["season"], r["min"], r["max"]) for r in active_rows
        }

    # Page list
    pages = list(ARG_PAGES) if ARG_PAGES else wiki_utils.get_pages_with_template("Fish locations")
    total = len(pages)

    site         = wiki_utils.get_site()
    debug_lines: list[str] = []
    updated:     list[str] = []
    skipped:     list[str] = []
    change_lines: list[str] = []

    for i in range(0, total, BATCH_SIZE):
        batch      = pages[i : i + BATCH_SIZE]
        page_texts = wiki_utils.fetch_pages(batch, batch_size=BATCH_SIZE)

        for title in batch:
            text      = page_texts.get(title, "")
            title_key = title.lower()

            # Skip pages we have no data for
            if title_key not in expected_lower:
                skipped.append(title)
                debug_lines.append(f"[NO DATA] {title}")
                continue

            canonical = expected_lower[title_key]

            # Parse current wiki entries
            wiki_entries = _parse_wiki_entries(text)
            if wiki_entries is None:
                skipped.append(title)
                debug_lines.append(f"[NO TEMPLATE] {title}")
                continue

            # Compare active (non-commented) expected entries to wiki
            if wiki_entries == expected_active[canonical]:
                debug_lines.append(f"[NO CHANGE] {title}")
                continue

            # Build and apply the updated template
            new_template = _build_template(canonical, fish_to_rows[canonical])
            new_text     = _replace_template(text, new_template)

            change_lines.append(title)
            change_lines.append("")

            page = pywikibot.Page(site, title)

            try:
                if not DRY_RUN:
                    page.text = new_text
                    page.save(summary="Update fish locations from data")
                    if not ARG_PAGES:
                        time.sleep(SLEEP_INTERVAL)

                updated.append(title)
                status = "DRY RUN" if DRY_RUN else "UPDATED"
                debug_lines.append(f"[{status}] {title}")

            except Exception as exc:
                skipped.append(title)
                debug_lines.append(f"[FAILED] {title} - {exc}")

        if i // BATCH_SIZE % 10 == 0:
            processed = i + len(batch)
            percent   = round((processed / total) * 100, 1)
            print(
                f"     🔄 Reviewed {processed} of {total} pages "
                f"({percent}% complete). Sleeping {SLEEP_INTERVAL} seconds."
            )
            if not ARG_PAGES:
                time.sleep(SLEEP_INTERVAL)

    with open(_DEBUG_LOG, "w", encoding="utf-8") as dbg:
        dbg.write("\n".join(debug_lines))
    with open(_OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("\n".join(change_lines))

    print(f"✅ Fish locations update complete. {len(updated)} updated, {len(skipped)} skipped.")


if __name__ == "__main__":
    run()
