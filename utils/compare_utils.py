import os
import re
from typing import List, Tuple, Dict, Callable, Any
from config.skip_items import SKIP_FIELDS
from utils.text_utils import (
    clean_whitespace,
    normalize_apostrophe,
    normalize_value,
    normalize_bool,
    normalize_for_compare
)

def normalize_title(s: str) -> str:
    t = normalize_apostrophe(s or "")
    return clean_whitespace(t).lower()

def extract_required_level(value: str) -> str:
    if not value:
        return ""
    match = re.search(r"\|\s*(\d+)\s*\}\}", value)
    if match:
        return match.group(1)
    return value

def compare_instance_generic(
    json_obj: Dict[str, Any],
    wiki_params: Dict[str, str],
    keys_to_check: List[str],
    field_map: Dict[str, Tuple[str, Callable[[Any], str]]],
    compute_map: Dict[str, Callable[[Dict[str, Any]], str]],
    normalize_bool_fn: Callable[[Any], str],
    skip_fields_map: Dict[str, List[str]] = {}
) -> List[Tuple[str, str, str]]:

    differences = []
    expected_values = {}

    item_name = json_obj.get("Name", "").strip()
    skip_fields = skip_fields_map.get(item_name, [])

    can_sell = json_obj.get("canSell", 1)

    for field, (json_key, normalize_fn) in field_map.items():
        if field in skip_fields:
            continue
        expected_values[field] = normalize_fn(json_obj.get(json_key))

    for field, compute_fn in compute_map.items():
        if field in skip_fields:
            continue
        expected_values[field] = compute_fn(json_obj)

    for key in keys_to_check:
        if key in skip_fields:
            continue

        if key == "name" and key not in wiki_params:
            continue

        if key == "statInc" and re.search(r"»\(\+?999\)", expected_values.get(key, "")):
            continue

        if key == "requirement":
            raw_val = expected_values.get(key, "")
            if raw_val in ("", "0", "null"):
                continue
            expected_val = extract_required_level(raw_val)
            actual_val = extract_required_level(wiki_params.get(key, ""))
            if expected_val != actual_val:
                differences.append((key, expected_val, wiki_params.get(key, "")))
            continue

        if key in {"dlc", "organic"}:
            expected_val = normalize_bool_fn(expected_values.get(key, "false"))
            actual_val = normalize_bool_fn(wiki_params.get(key, ""))
            if expected_val == "true" and actual_val != "true":
                differences.append((key, "true", wiki_params.get(key, "")))
            continue

        if key == "sell":
            expected_val = "no" if not can_sell else expected_values.get(key, "")
            actual_val = wiki_params.get(key, "")
            if normalize_for_compare(expected_val) != normalize_for_compare(actual_val):
                differences.append((key, expected_val, actual_val))
            continue

        if key == "currency" and not can_sell:
            continue

        expected_val = expected_values.get(key, "")
        actual_val = wiki_params.get(key, "")
        if normalize_for_compare(expected_val) != normalize_for_compare(actual_val):
            differences.append((key, expected_val, actual_val))

    return differences

def compare_grouped_variants(
    wiki_title: str,
    wiki_params: Dict[str, str],
    json_data: Dict[str, Dict[str, Any]],
    keys_to_check: List[str],
    field_map: Dict[str, Tuple[str, Callable[[Any], str]]],
    compute_map: Dict[str, Callable[[Dict[str, Any]], str]],
    normalize_bool_fn: Callable[[Any], str]
) -> Tuple[List[str], List[str], List[str]]:
    variant_keys = [k for k in json_data if k.startswith(wiki_title.lower() + " (")]
    mismatches = []
    full_matches = []

    variant_keys_to_check = [k for k in keys_to_check if k != "name"]

    for key in variant_keys:
        json_obj = json_data[key]
        diffs = compare_instance_generic(
            json_obj,
            wiki_params,
            variant_keys_to_check,
            field_map,
            compute_map,
            normalize_bool_fn
        )
        variant_label = key.split("(", 1)[-1].rstrip(")")
        if diffs:
            for field, actual, expected in diffs:
                mismatches.append(f"    - ({variant_label}) {field}: expected '{expected}' but found '{actual}'")
        else:
            full_matches.append(f"    - ({variant_label}) full match")
    return variant_keys, mismatches, full_matches