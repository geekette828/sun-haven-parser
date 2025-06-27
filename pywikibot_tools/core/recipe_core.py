import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from utils import text_utils, recipe_utils
from utils.compare_utils import compare_instance_generic
from utils.wiki_utils import get_pages_with_template, fetch_pages, parse_template_params
from mappings.recipe_mapping import RECIPE_FIELD_MAP, RECIPE_COMPUTE_MAP, RECIPE_EXTRA_FIELDS

def load_normalized_json(json_file_path):
    from utils import json_utils
    data = json_utils.load_json(json_file_path)
    return {k.strip().lower(): v for k, v in data.items()}

def get_recipe_pages(TEST_RUN=False, test_list=None):
    return test_list if TEST_RUN and test_list else get_pages_with_template("Recipe", namespace=0)

def get_recipe_none_pages(TEST_RUN=False, test_list=None):
    return test_list if TEST_RUN and test_list else get_pages_with_template("Recipe/none", namespace=0)

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
        name = output.get("name", "").lower().replace("(", "").replace(")", "").strip()
        if name == title_lc.replace("(", "").replace(")", "").strip():
            return key, record
    return None, None

# NEW preferred matching logic
def match_json_recipe(template, page_title, data, num_templates_on_page):
    logs = []
    recipe_id = template.get("id").value.strip() if template.has("id") else None
    product = template.get("product").value.strip() if template.has("product") else page_title

    if recipe_id:
        entry = data.get(recipe_id.lower())
        if entry:
            return entry, logs
        logs.append(f"[ID NOT FOUND] {page_title} - Recipe ID {recipe_id} not found in JSON data")

    name_matches = [k for k, v in data.items()
                    if isinstance(v.get("output"), dict) and v["output"].get("name", "").strip().lower() == product.lower()]

    if len(name_matches) == 1 and num_templates_on_page == 1:
        return data[name_matches[0]], logs

    if not name_matches:
        logs.append(f"[NO MATCH] {page_title} - No JSON recipes found for product '{product}'")
        return None, logs

    logs.append(f"[MULTI MATCH] {page_title} - Multiple JSON recipes found for '{product}'")
    return None, logs
