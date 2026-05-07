import os
import re
import sys
import mwparserfromhell

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from utils import text_utils
from wiki.compare.infobox_fields import FIELD_MAP, FIELD_COMPUTATIONS
from utils.compare_utils import compare_instance_generic
from utils.wiki_utils import get_pages_with_template, parse_template_params


# Common keys across most infoboxes
COMMON_KEYS = ["sell", "currency", "stack", "rarity", "hearts"]

# Single source of truth: all supported infobox templates (exact names as used on-wiki)
INFOBOX_NAMES = [
    "Agriculture infobox",
    "Animal infobox",
    "Clothing infobox",
    "Consumable infobox",
    "Equipment infobox",
    "Fish infobox",
    "Furniture infobox",
    "Item infobox",
]
INFOBOX_NAMES_LOWER = {name.lower() for name in INFOBOX_NAMES}

# Template-specific keys (lowercase template name -> list of keys)
INFOBOX_KEYS = {
    "item infobox": COMMON_KEYS,

    "animal infobox": COMMON_KEYS + [
        "capacity",   # derived from JSON helpDescription
    ],

    "clothing infobox": COMMON_KEYS + [
        "dlc",
    ],

    "consumable infobox": COMMON_KEYS + [
        "restores",
        "statInc",
        "organic",
        "sopShelf",
        "rareFinds",
    ],

    "equipment infobox": COMMON_KEYS + [
        "dlc",
        "effect",
        "requirement",
    ],

    "fish infobox": COMMON_KEYS + [
        "restores",
        "statInc",
        "exp",
    ],

    "furniture infobox": COMMON_KEYS + [
        "dlc",
        "placementType",
        "isRotatable",
    ],

    # Agriculture is special-cased (crop + seed compare)
    "agriculture infobox": COMMON_KEYS,
}

# Agriculture infobox special fields:
# - Crop-side: common fields PLUS restores/statInc (but ignore if JSON null/empty)
# - Seed-side: derived from seed JSON (only if seed exists)
AGRI_CROP_KEYS = [
    "sell",
    "currency",
    "stack",
    "rarity",
    "hearts",
    "restores",
    "statInc",
]
AGRI_SEED_KEYS = ["season", "exp", "growth", "regrowth", "cropYield"]

SEASON_NAMES = {
    0: "Spring",
    1: "Summer",
    2: "Fall",
    3: "Winter",
}

# Debug marker key (added to wiki_params when seed JSON can't be found)
AGRI_MISSING_SEED_KEY = "_missing_seed_json"


def get_keys_for_template(template_name_lower):
    return INFOBOX_KEYS.get(template_name_lower, COMMON_KEYS)


def load_normalized_json(json_file_path):
    from utils import json_utils
    data = json_utils.load_json(json_file_path)
    return {text_utils.normalize_apostrophe(k.lower()): v for k, v in data.items()}


def find_infobox_template(parsed):
    for template in parsed.filter_templates():
        if template.name.strip().lower() in INFOBOX_NAMES_LOWER:
            return template
    return None


def get_infobox_template_name(wikitext):
    parsed = mwparserfromhell.parse(wikitext)
    template = find_infobox_template(parsed)
    return template.name.strip() if template else None


def get_infobox_param_map(wikitext, page_title):
    template_name = get_infobox_template_name(wikitext)
    if not template_name:
        params = {}
    else:
        params = parse_template_params(wikitext, template_name)

    if "name" not in params or not params["name"].strip():
        params["name"] = page_title.lower()

    # Strip HTML comments from all values
    for key, val in params.items():
        params[key] = re.sub(r"<!--.*?-->", "", val).strip()

    return params


def _normalize_text(v):
    if v is None:
        return ""
    s = re.sub(r"\s+", " ", str(v)).strip()
    # Treat "+N" and "N" as identical — wiki pages are inconsistent about the + prefix
    s = re.sub(r"\+(?=[\d.])", "", s)
    return s


def _norm_key(name):
    return text_utils.normalize_apostrophe(str(name or "")).lower().strip()


def _season_string_from_seasons(seasons, seed_name=None):
    # Tree seeds can be grown any season (only applied when seed is known)
    if seed_name:
        sn = str(seed_name).strip().lower()
        if sn.endswith("tree seed") or sn.endswith("tree seeds"):
            return "Any"

    if seasons is None:
        return ""

    if isinstance(seasons, str):
        ints = re.findall(r"\d+", seasons)
        seasons = [int(x) for x in ints] if ints else []

    if isinstance(seasons, int):
        seasons = [seasons]

    if not isinstance(seasons, (list, tuple)):
        return ""

    season_set = {int(x) for x in seasons if str(x).isdigit()}

    if season_set == {0, 1, 2, 3}:
        return "Any"

    names = [SEASON_NAMES[s] for s in [0, 1, 2, 3] if s in season_set]
    return "; ".join(names) if names else ""


def _parse_growth_yield_regrowth_from_help(help_desc):
    """
    Handles variations like:
    - take / takes
    - yield / yields
    - crop / crops

    If no yield is found, default cropYield to 1.
    """
    if not help_desc:
        return "", "1", ""

    hd = str(help_desc)

    growth = ""
    crop_yield = ""
    regrowth = ""

    m = re.search(
        r"take(?:s)?\s*<style=Help>\s*(\d+)\s*day(?:s)?\s*</style>\s*to grow",
        hd,
        flags=re.I
    )
    if m:
        growth = m.group(1)

    m = re.search(
        r"yield(?:s)?\s*<style=Help>\s*(\d+(?:\.\d+)?)\s*crop(?:s)?",
        hd,
        flags=re.I
    )
    if m:
        crop_yield = m.group(1)

    m = re.search(
        r"take(?:s)?\s*<style=Help>\s*(\d+)\s*day(?:s)?\s*</style>\s*to regrow",
        hd,
        flags=re.I
    )
    if m:
        regrowth = m.group(1)

    if not crop_yield:
        crop_yield = "1"

    return growth, crop_yield, regrowth


def _agriculture_seed_expected(seed_item, fallback_seed_name=None):
    if not seed_item:
        return {}

    seed_name = seed_item.get("name") or fallback_seed_name or ""

    season = _season_string_from_seasons(seed_item.get("seasons"), seed_name)
    exp = seed_item.get("exp", "")

    # Growth: parse from helpDescription first (matches in-game text exactly).
    # Fall back to last crop_stage's days_to_grow + 1 if helpDescription has no growth info.
    growth, _, _ = _parse_growth_yield_regrowth_from_help(seed_item.get("help_description", ""))
    if not growth:
        crop_stages = seed_item.get("crop_stages", [])
        if crop_stages:
            growth = str(int(crop_stages[-1]["days_to_grow"]) + 1)

    # CropYield: parse from helpDescription (matches in-game text exactly,
    # handles fractional yields like 1.5, and avoids dropRange.x truncation).
    _, crop_yield, _ = _parse_growth_yield_regrowth_from_help(seed_item.get("help_description", ""))

    # Regrowth: use regrowable flag + days_to_regrow field.
    # Only report a regrowth value when the crop actually regrows.
    if seed_item.get("regrowable", False):
        days = seed_item.get("days_to_regrow")
        regrowth = str(int(days)) if days else ""
    else:
        regrowth = ""

    return {
        "season": _normalize_text(season),
        "exp": _normalize_text(exp),
        "growth": _normalize_text(growth),
        "cropYield": _normalize_text(crop_yield),
        "regrowth": _normalize_text(regrowth),
    }


def _parse_animal_capacity_from_help(help_desc):
    """
    Example: "Counts as 2 barn animal capacity"
    Returns "2" or "" if not found.
    """
    if not help_desc:
        return ""
    hd = str(help_desc)
    m = re.search(r"Counts\s+as\s+(\d+)\s+barn\s+animal\s+capacity", hd, flags=re.I)
    return m.group(1) if m else ""


# Fields whose semicolon-separated parts can appear in any order on-wiki.
_ORDER_INSENSITIVE_FIELDS = {"effect", "statInc", "restores"}


def _normalize_for_compare(field, value):
    """Normalise a field value for comparison.

    For semicolon-separated fields the order of parts is irrelevant,
    so sort them before comparing to avoid false mismatches.
    """
    s = _normalize_text(value)
    if field in _ORDER_INSENSITIVE_FIELDS and s:
        parts = [p.strip() for p in s.split(";") if p.strip()]
        return "; ".join(sorted(parts))
    return s


def _diff_if_changed(field, expected, actual):
    exp_n = _normalize_for_compare(field, expected)
    act_n = _normalize_for_compare(field, actual)
    if exp_n == act_n:
        return None
    return (field, exp_n, act_n)


def compare_page_to_json(title, text, item_data, keys_to_check, skip_fields_map=None, all_data=None):
    """
    Compare a wiki page's infobox to JSON data.

    - Uses template-specific key lists for most infobox types.
    - Special-cases Agriculture infobox (crop + seed compare).
    """
    wiki_params = get_infobox_param_map(text, title)
    template_name = (get_infobox_template_name(text) or "").strip().lower()

    skip_fields = []
    if isinstance(skip_fields_map, dict):
        skip_fields = skip_fields_map.get(title, []) or []
    elif isinstance(skip_fields_map, (list, set, tuple)):
        skip_fields = list(skip_fields_map)

    # Agriculture special compare
    if template_name == "agriculture infobox":
        diffs = []

        # Crop-side compare:
        # Includes restores/statInc, but ignore if JSON has null/empty/missing for that key.
        crop_keys = []
        for key in AGRI_CROP_KEYS:
            if skip_fields and key in skip_fields:
                continue

            json_val = item_data.get(key)

            # Ignore empty/null crop fields (especially restores/statInc)
            if json_val in (None, "", [], {}):
                continue

            crop_keys.append(key)

        if crop_keys:
            crop_diffs = compare_instance_generic(
                item_data,
                wiki_params,
                crop_keys,
                FIELD_MAP,
                FIELD_COMPUTATIONS,
                text_utils.normalize_bool,
                skip_fields_map=skip_fields_map
            )
            diffs.extend(crop_diffs or [])

        # Seed-side compare:
        seed_name = wiki_params.get("seed", "").strip()
        seed_key = _norm_key(seed_name)

        seed_item = None
        if all_data:
            seed_item = all_data.get(seed_key)

            # Plural / singular fallback (Seeds <-> Seed)
            if not seed_item:
                if seed_key.endswith("seeds"):
                    seed_item = all_data.get(seed_key[:-1])
                elif seed_key.endswith("seed"):
                    seed_item = all_data.get(seed_key + "s")

        # If seed not found in JSON: skip seed compare and record for logging
        if not seed_item:
            if seed_name:
                wiki_params[AGRI_MISSING_SEED_KEY] = seed_name
            if skip_fields:
                diffs = [d for d in diffs if d[0] not in skip_fields]
            return diffs, wiki_params

        seed_expected = _agriculture_seed_expected(seed_item, fallback_seed_name=seed_name)

        for field in AGRI_SEED_KEYS:
            if skip_fields and field in skip_fields:
                continue

            expected = seed_expected.get(field, "")
            actual = wiki_params.get(field, "")

            d = _diff_if_changed(field, expected, actual)
            if d:
                diffs.append(d)

        if skip_fields:
            diffs = [d for d in diffs if d[0] not in skip_fields]
        return diffs, wiki_params

    # Non-agriculture: template-specific compare keys
    keys = get_keys_for_template(template_name)

    if skip_fields:
        keys = [k for k in keys if k not in skip_fields]

    # Animal special compute: capacity from JSON helpDescription
    if template_name == "animal infobox":
        base_keys = [k for k in keys if k != "capacity"]

        diffs = compare_instance_generic(
            item_data,
            wiki_params,
            base_keys,
            FIELD_MAP,
            FIELD_COMPUTATIONS,
            text_utils.normalize_bool,
            skip_fields_map=skip_fields_map
        ) or []

        if not skip_fields or "capacity" not in skip_fields:
            expected_capacity = _parse_animal_capacity_from_help(item_data.get("help_description"))
            actual_capacity = wiki_params.get("capacity", "")

            d = _diff_if_changed("capacity", expected_capacity, actual_capacity)
            if d:
                diffs.append(d)

        if skip_fields:
            diffs = [d for d in diffs if d[0] not in skip_fields]
        return diffs, wiki_params

    diffs = compare_instance_generic(
        item_data,
        wiki_params,
        keys,
        FIELD_MAP,
        FIELD_COMPUTATIONS,
        text_utils.normalize_bool,
        skip_fields_map=skip_fields_map
    )

    if skip_fields and diffs:
        diffs = [d for d in diffs if d[0] not in skip_fields]
    return diffs, wiki_params


def update_template_fields(template, diffs):
    for field, expected, _ in diffs:
        expected = f" {expected}"  # Ensure space after '='

        if template.has(field):
            param = template.get(field)
            param.value = expected
            if not str(param.value).endswith("\n"):
                param.value = str(param.value) + "\n"
        elif field == "name":
            continue
        else:
            template.add(field, expected + "\n")


def update_infobox_text(text, diffs):
    parsed = mwparserfromhell.parse(text)
    template = find_infobox_template(parsed)
    if template:
        update_template_fields(template, diffs)
        result = str(parsed)
        result = re.sub(r"\n+\}\}$", "\n}}", result)
        result = re.sub(r"(?<!\n)([^\n\S]*)(\n}})$", r"  }}", result)
        return result
    return text


def get_infobox_pages(TEST_RUN=False, test_list=None):
    if TEST_RUN and test_list:
        return test_list

    pages = []
    seen = set()
    for name in INFOBOX_NAMES:
        for page_title in get_pages_with_template(name, namespace=0):
            if page_title not in seen:
                seen.add(page_title)
                pages.append(page_title)
    return pages


def extract_subtype(wikitext):
    parsed = mwparserfromhell.parse(wikitext)
    template = find_infobox_template(parsed)
    if template and template.has("subtype"):
        return str(template.get("subtype").value).strip()
    return ""


def get_base_variant_key(normalized_title, data, subtype=None):
    base_match = re.match(r"^(.*) \(([^)]+)\)$", normalized_title)
    if base_match:
        base_title = base_match.group(1)
        if base_title in data:
            return base_title, "VARIANTS"

    if subtype in ["Mount", "Pet"]:
        parts = normalized_title.split(" ", 1)
        if len(parts) == 2 and parts[1] in data:
            return parts[1], "VARIANTS"

    return None, ""
