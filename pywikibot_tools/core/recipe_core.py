import os
import re
import sys
import mwparserfromhell

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from mappings.recipe_mapping import RECIPE_FIELD_MAP, RECIPE_COMPUTE_MAP, RECIPE_EXTRA_FIELDS
from utils.compare_utils import compare_instance_generic
from utils import text_utils, recipe_utils
from utils.wiki_utils import get_pages_with_template, fetch_pages, parse_template_params


def load_normalized_json(json_file_path):
    from utils import json_utils
    data = json_utils.load_json(json_file_path)
    return {k.strip().lower(): v for k, v in data.items()}


def get_recipe_pages(TEST_RUN=False, test_list=None):
    return test_list if TEST_RUN and test_list else get_pages_with_template("Recipe", namespace=0)


def get_recipe_param_map(wikitext, page_title):
    params = parse_template_params(wikitext, "Recipe")
    if "product" not in params or not params["product"].strip():
        params["product"] = page_title.strip()

    for key, val in params.items():
        params[key] = re.sub(r"<!--.*?-->", "", val).strip()

    return params


def compare_extra_fields(json_entry, tpl_params, keys_to_check, title):
    diffs = []
    for field in keys_to_check:
        if field not in RECIPE_EXTRA_FIELDS:
            continue
        expected = RECIPE_EXTRA_FIELDS[field](json_entry, tpl_params, title)
        actual = tpl_params.get(field, "").strip()
        if expected != actual:
            diffs.append((field, expected, actual))
    return diffs


def compare_page_to_json(title, text, json_entry, keys_to_check, skip_fields_map=None):
    wiki_params = get_recipe_param_map(text, title)

    if "time" in keys_to_check:
        json_entry["time"] = recipe_utils.format_time(json_entry.get("hoursToCraft", 0))

    if "ingredients" in keys_to_check:
        json_entry["ingredients"] = "; ".join(
            f"{i.get('name', '').strip()}*{i.get('amount', 1)}"
            for i in json_entry.get("inputs", [])
        )

    diffs = compare_instance_generic(
        json_entry,
        wiki_params,
        keys_to_check,
        RECIPE_FIELD_MAP,
        RECIPE_COMPUTE_MAP,
        text_utils.normalize_bool,
        skip_fields_map=skip_fields_map or {}
    )

    diffs.extend(compare_extra_fields(json_entry, wiki_params, keys_to_check, title))
    return diffs, wiki_params


def find_json_by_product_name(data, page_title):
    title_lc = page_title.lower()
    for key, record in data.items():
        output = record.get("output", {})
        name = output.get("name", "").lower()
        if name == title_lc:
            return key, record
    return None, None


def match_templates_by_id(page_title, wikitext, json_data):
    parsed = mwparserfromhell.parse(wikitext)
    matches = []
    logs = []

    for template in parsed.filter_templates():
        if template.name.strip().lower() != "recipe":
            continue

        template_id = template.get("id").value.strip() if template.has("id") else None
        if not template_id:
            logs.append(f"[MISSING ID] {page_title} - Skipping template with no ID")
            continue

        matched_json = next(
            (v for v in json_data.values() if str(v.get("recipeID")) == template_id),
            None
        )

        if not matched_json:
            logs.append(f"[UNKNOWN ID] {page_title} - ID {template_id} not found in JSON")
            continue

        matches.append((template, matched_json, template_id))

    return matches, logs
