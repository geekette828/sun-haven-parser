# -*- coding: utf-8 -*-
"""
update_item_infobox_flags.py

Adds `topShelf = true` and/or `rareFinds = true` to {{Item infobox}} or {{Agriculture infobox}}
based on items_data.json flags:
- isAnimalProduct == 1  -> topShelf = true
- isForageable  == 1    -> rareFinds = true

Follows project path bootstrap + constants usage.
No emojis in edit summary; emojis allowed in console/log output.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import re
import json
import logging
import traceback
from typing import Dict, Any, Tuple

import config.constants as constants
from utils import file_utils

import pywikibot
try:
    import mwparserfromhell as mwp
except ImportError:
    mwp = None

# -------------------------
# Flags
# -------------------------
DRY_RUN = False
TEST_RUN = True
SAMPLE_LIMIT = 20

# Console/log icons (console only; not used in edit summary)
ICON_SCAN = "🔍"
ICON_WORK = "🔄"
ICON_DONE = "✅"
ICON_EDIT = "📝"
ICON_DEBUG = "🛠️"

# -------------------------
# Paths / files (via constants)
# -------------------------
ITEMS_JSON_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
DEBUG_LOG_PATH = os.path.join(constants.DEBUG_DIRECTORY, "update_item_infobox_flags_debug.txt")

# -------------------------
# Edit summary (no emojis)
# -------------------------
EDIT_SUMMARY = (
    "Add infobox flags from items_data.json: "
    "`topShelf = true` for Animal Products, `rareFinds = true` for Forageables."
)

# -------------------------
# Logging
# -------------------------
def setup_logger(debug_log_path: str):
    logger = logging.getLogger("update_item_infobox_flags")
    logger.setLevel(logging.DEBUG)
    file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))
    fh = logging.FileHandler(debug_log_path, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(fh)
    return logger

# -------------------------
# JSON helpers
# -------------------------
def load_items_data(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def candidates_from_json(items_data: Dict[str, Any]) -> Dict[str, Tuple[bool, bool]]:
    """
    Returns { page_title: (needs_topShelf, needs_rareFinds) } for items with either flag == 1.
    """
    out: Dict[str, Tuple[bool, bool]] = {}
    for name, item in items_data.items():
        is_animal = str(item.get("isAnimalProduct", 0)) == "1"
        is_forage = str(item.get("isForageable", 0)) == "1"
        if is_animal or is_forage:
            out[name] = (is_animal, is_forage)
    return out

# -------------------------
# Template matching (strict to two names)
# -------------------------
ALLOWED = {"item infobox", "agriculture infobox"}

def _normalize_name(text: str) -> str:
    """normalize to compare against ALLOWED"""
    name = str(text).strip().lower()
    if name.startswith("template:"):
        name = name[len("template:"):]
    name = name.replace("_", " ").replace("-", " ")
    name = " ".join(name.split())
    return name

def _find_target_infobox(code):
    """
    Find exactly {{Item infobox}} or {{Agriculture infobox}} (case-insensitive).
    Prefer Item; fall back to Agriculture.
    Returns (template, matched_label)
    """
    item_tpl = None
    agri_tpl = None
    for tpl in code.filter_templates(recursive=True):
        n = _normalize_name(tpl.name.strip_code())
        if n not in ALLOWED:
            continue
        if n == "item infobox":
            item_tpl = tpl
            break
        if n == "agriculture infobox" and agri_tpl is None:
            agri_tpl = tpl
    if item_tpl is not None:
        return item_tpl, "Item infobox"
    if agri_tpl is not None:
        return agri_tpl, "Agriculture infobox"
    return None, ""

# -------------------------
# Param insertion (newline-aware)
# -------------------------
def ensure_params_with_newlines(template, add_top_shelf: bool, add_rare_finds: bool) -> bool:
    """
    Add params only if missing; set separators to encourage line breaks.
    (We still enforce layout post-render for absolute correctness.)
    """
    def hasp(k: str) -> bool:
        kl = k.lower()
        return any(str(p.name).strip().lower() == kl for p in template.params)

    need_top  = add_top_shelf  and not hasp("topshelf")
    need_rare = add_rare_finds and not hasp("rarefinds")
    if not (need_top or need_rare):
        return False

    changed = False
    before_len = len(template.params)

    # Add in stable order and try to set line breaks
    if need_top:
        template.add("topShelf", "true", preserve_spacing=True)
        try:
            template.params[len(template.params) - 1].separator = "\n"
        except Exception:
            pass
        changed = True
    if need_rare:
        template.add("rareFinds", "true", preserve_spacing=True)
        try:
            template.params[len(template.params) - 1].separator = "\n"
        except Exception:
            pass
        changed = True

    # Newline before the first inserted param (after last existing)
    if before_len > 0:
        try:
            template.params[before_len - 1].separator = "\n|"
        except Exception:
            pass

    return changed

# -------------------------
# Post-render enforcement of line layout + comment
# -------------------------
_TOP_RARE_INLINE = re.compile(r'(?<!\n)[ \t]*\|(topShelf|rareFinds)\s*=\s*', re.IGNORECASE)
_ENDS_AFTER_TOP_RARE = re.compile(r'(\|\s*(?:topShelf|rareFinds)\s*=\s*true[^\S\r\n]*)(}}\s*)', re.IGNORECASE)

def _force_line_layout(text: str) -> str:
    """
    Ensure our inserted params start at line-begins and that '}}' is on its own line.
    """
    # 1) Force newline BEFORE any inline topShelf/rareFinds
    text = _TOP_RARE_INLINE.sub(r'\n|\1 = ', text)
    # 2) Ensure closing braces are on a new line when they follow our keys on same line
    text = _ENDS_AFTER_TOP_RARE.sub(r'\1\n\2', text)
    return text

def _inject_item_data_comment(page_text: str, infobox_wikitext: str) -> str:
    """
    If the infobox doesn't already contain <!-- Item Data-->, insert it immediately
    BEFORE the first occurrence of |topShelf or |rareFinds (case-insensitive).
    Returns the possibly-modified page_text (replacing exactly one instance of the infobox).
    """
    # If comment already present, or neither param present, do nothing
    if "<!-- Item Data-->" in infobox_wikitext:
        return page_text

    lower = infobox_wikitext.lower()
    idx_top  = lower.find("|topshelf")
    idx_rare = lower.find("|rarefinds")

    indices = [i for i in (idx_top, idx_rare) if i != -1]
    if not indices:
        return page_text  # nothing to do

    insert_at = min(indices)

    new_infobox = infobox_wikitext[:insert_at] + "\n<!-- Item Data-->\n" + infobox_wikitext[insert_at:]
    return page_text.replace(infobox_wikitext, new_infobox, 1)

# -------------------------
# Page update
# -------------------------
def update_page(site, logger, title: str, flags: Tuple[bool, bool]) -> Tuple[bool, str]:
    add_top, add_rare = flags
    page = pywikibot.Page(site, title)

    if not page.exists():
        msg = f"{ICON_DEBUG} Missing page: {title}"
        logger.info(msg)
        return (False, msg)

    text = page.text

    if mwp is None:
        msg = f"{ICON_DEBUG} mwparserfromhell not installed; cannot edit: {title}"
        logger.error(msg)
        return (False, msg)

    code = mwp.parse(text)
    infobox, which = _find_target_infobox(code)

    if not infobox:
        msg = f"{ICON_DEBUG} No {{Item infobox}} or {{Agriculture infobox}} found on: {title}"
        logger.info(msg)
        return (False, msg)

    changed = ensure_params_with_newlines(infobox, add_top, add_rare)
    if not changed:
        msg = f"{ICON_SCAN} Up-to-date (no changes): {title} [{which}]"
        logger.info(msg)
        return (False, msg)

    # Render text from AST
    new_text = str(code)

    # Inject the comment BEFORE our params only if it's not already present in this infobox
    infobox_wikitext_now = str(infobox)
    new_text = _inject_item_data_comment(new_text, infobox_wikitext_now)

    # HARD-enforce line layout for our params & closing braces
    new_text = _force_line_layout(new_text)

    if DRY_RUN:
        msg = f"{ICON_EDIT} DRY_RUN — would save [{which}] on: {title}"
        logger.info(msg)
        return (True, msg)

    try:
        page.text = new_text
        page.save(summary=EDIT_SUMMARY, minor=False, force=False)
        msg = f"{ICON_DONE} Saved [{which}]: {title}"
        logger.info(msg)
        return (True, msg)
    except Exception as e:
        msg = f"{ICON_DEBUG} Save failed for {title}: {e}"
        logger.exception(msg)
        return (False, msg)

def log_progress(i: int, total: int, logger):
    if total <= 0:
        return
    if i % 50 == 0 or i == total:
        pct = int((i / total) * 100)
        logger.info(f"{ICON_WORK} Progress: {i}/{total} ({pct}%)")

# -------------------------
# Main
# -------------------------
def main():
    file_utils.ensure_dir_exists(os.path.dirname(DEBUG_LOG_PATH))
    logger = setup_logger(DEBUG_LOG_PATH)

    logger.info(f"{ICON_WORK} Starting infobox updater (topShelf/rareFinds).")
    logger.info(f"{ICON_SCAN} Reading JSON: {ITEMS_JSON_PATH}")

    try:
        items_data = load_items_data(ITEMS_JSON_PATH)
        logger.info("Loaded items_data.json successfully.")
    except Exception as e:
        logger.exception(f"Failed to load JSON: {e}")
        return

    candidates = candidates_from_json(items_data)
    titles = sorted(candidates.keys())
    if TEST_RUN:
        titles = titles[:SAMPLE_LIMIT]

    total = len(titles)
    logger.info(f"{ICON_SCAN} Candidates: {total} (TEST_RUN={TEST_RUN}, DRY_RUN={DRY_RUN})")

    site = pywikibot.Site()
    site.login()

    changed = skipped = errs = 0

    for idx, title in enumerate(titles, start=1):
        log_progress(idx, total, logger)
        try:
            did_change, msg = update_page(site, logger, title, candidates[title])
            if did_change:
                changed += 1
            else:
                skipped += 1
            pywikibot.output(msg)  # console echo
        except KeyboardInterrupt:
            logger.warning(f"{ICON_DEBUG} Interrupted by user.")
            break
        except Exception as e:
            errs += 1
            logger.exception(f"{ICON_DEBUG} Error on {title}: {e}\n{traceback.format_exc()}")

    logger.info(f"{ICON_DONE} Finished. Changed: {changed} | Skipped: {skipped} | Errors: {errs}"
                + (f" | DRY_RUN" if DRY_RUN else "")
                + (f" | TEST_RUN" if TEST_RUN else ""))

if __name__ == "__main__":
    main()