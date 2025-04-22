"""
Generic comparison utilities for JSON↔Wiki template comparisons.
"""

from typing import List, Tuple, Dict, Callable, Any
from utils.text_utils import clean_whitespace, normalize_apostrophe
from utils.wiki_utils import get_pages_with_template, fetch_pages, parse_template_params


def normalize_title(s: str) -> str:
    """
    Normalize a string for lookups: replace curly apostrophes, collapse whitespace, lowercase.
    """
    t = normalize_apostrophe(s or "")
    return clean_whitespace(t).lower()


def compare_instance_generic(
    tpl_params: Dict[str, str],
    json_record: Dict[str, Any],
    field_map: Dict[str, Tuple[str, Callable[[Any], str]]],
    extra_fields: Dict[str, Callable[[Dict[str, Any], Dict[str, str], str], str]] = None,
    page_title: str = "",
) -> List[Tuple[str, str, str]]:
    """
    Compare a single template instance against a JSON record. No template-specific logic here.

    Args:
        tpl_params: parameters from the wiki template (param_name -> value)
        json_record: the corresponding JSON object
        field_map: mapping of template param -> (json key, normalization function)
        extra_fields: param -> function(json_record, tpl_params, page_title)
        page_title: the title of the current page, for template-specific logic (like product fallback)

    Returns:
        List of (param_name, wiki_value, json_value) for any mismatches.
    """
    diffs: List[Tuple[str, str, str]] = []
    for tpl_key, (json_key, norm_fn) in field_map.items():
        wiki_val = tpl_params.get(tpl_key, "").strip()
        if tpl_key == "product" and not wiki_val:
            wiki_val = page_title.strip()
        if extra_fields and tpl_key in extra_fields:
            json_val = extra_fields[tpl_key](json_record, tpl_params, page_title)
        else:
            raw_val = json_record.get(json_key)
            json_val = norm_fn(raw_val)
        if clean_whitespace(wiki_val) != clean_whitespace(json_val):
            diffs.append((tpl_key, wiki_val, json_val))
    return diffs


def compare_all_generic(
    template_name: str,
    json_by_key: Dict[str, Dict[str, Any]],
    field_map: Dict[str, Tuple[str, Callable[[Any], str]]],
    extra_fields: Dict[str, Callable[[Dict[str, Any], Dict[str, str], str], str]] = None,
    key_fn: Callable[[str], str] = normalize_title,
    namespace: int = None,
    batch_size: int = 50,
) -> Dict[str, Any]:
    """
    Compare all wiki pages transcluding `template_name` against JSON records.

    Emits periodic progress updates every 250 items.

    Returns:
        {
          "debug_lines": [...],
          "summary": { "mismatches", "wiki_only", "json_only" }
        }
    """
    titles = get_pages_with_template(template_name, namespace)
    total = len(titles)
    processed = 0

    mismatches: Dict[str, List[Tuple[str, str, str]]] = {}
    wiki_only: List[str] = []
    json_keys = set(json_by_key.keys())
    debug_lines: List[str] = []

    for i in range(0, total, batch_size):
        batch = titles[i : i + batch_size]
        wikitexts = fetch_pages(batch, batch_size)

        for title in batch:
            processed += 1
            if processed % 250 == 0:
                pct = int((processed / total) * 100)
                print(f"  🔄 {template_name} compare: {pct}% complete ({processed}/{total})")

            tpl_params = parse_template_params(wikitexts.get(title, ""), template_name)
            if not tpl_params:
                wiki_only.append(title)
                debug_lines.append(f"[WIKI ONLY] {title}\n")
                continue

            # Normalize fields if applicable
            if template_name == "Recipe":
                from mappings.recipe_mapping import (
                    _normalize_ingredient_list,
                    _normalize_time_string,
                )
                tpl_params['ingredients'] = _normalize_ingredient_list(tpl_params.get('ingredients', ''))
                tpl_params['time'] = _normalize_time_string(tpl_params.get('time', ''))

            record_key = key_fn(tpl_params.get("product") or title)
            record = json_by_key.get(record_key)
            if not record:
                wiki_only.append(title)
                debug_lines.append(f"[WIKI ONLY] {title}\n")
                continue

            diffs = compare_instance_generic(tpl_params, record, field_map, extra_fields, title)
            tag = "[MISMATCH]" if diffs else "[MATCH]  "
            debug_lines.append(f"{tag} {title}\n")
            if diffs:
                mismatches[title] = diffs
                for field, wv, jv in diffs:
                    debug_lines.append(f"  - {field}: wiki='{wv}' vs json='{jv}'\n")

            json_keys.discard(record_key)

    for key in sorted(json_keys):
        debug_lines.append(f"[JSON ONLY] {key}\n")

    return {
        "debug_lines": debug_lines,
        "summary": {
            "mismatches": mismatches,
            "wiki_only": wiki_only,
            "json_only": list(json_keys),
        },
    }
