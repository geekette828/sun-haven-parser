"""
Wiki field-comparison tables for the Recipe template.

Maps {{Recipe}} template parameters to recipe JSON fields for the compare
and update tools. Wikitext generation lives in formatters/item/item_recipe.py;
workbench normalisation lives in mappings/workbench_aliases.py.

Exports:
  RECIPE_FIELD_MAP    – template_param -> (json_field_key, normalization_fn)
  RECIPE_COMPUTE_MAP  – template_param -> fn(json_record) -> str
  RECIPE_EXTRA_FIELDS – template_param -> fn(json_record, tpl_params, title) -> str
"""

from utils import recipe_utils
from typing import Dict, Tuple, Any, Callable

RECIPE_FIELD_MAP: Dict[str, Tuple[str, Callable[[Any], str]]] = {
    "workbench": ("workbench", lambda v: (v or "").strip()),
    "ingredients": ("inputs", recipe_utils.format_json_ingredients),
    "time": ("hours_to_craft", recipe_utils.format_time),
    "yield": ("output", lambda out: str(out.get("amount", "")).strip() if isinstance(out, dict) else ""),
    "product": ("output", lambda out: (out.get("name") or "").strip() if isinstance(out, dict) else ""),
}

RECIPE_COMPUTE_MAP: Dict[str, Callable[[Any], str]] = {
    "id": lambda rec: str(rec.get("recipe_id", "")).strip() if rec else ""
}

RECIPE_EXTRA_FIELDS: Dict[str, Callable[[Dict[str, Any], Dict[str, str], str], str]] = {
    'ingredients': lambda rec, tpl, title: recipe_utils.normalize_ingredient_list(
        recipe_utils.format_json_ingredients(rec.get('inputs'))
    ),
    'time': lambda rec, tpl, title: recipe_utils.format_time(
        recipe_utils.format_time(rec.get('hours_to_craft'))
    ),
    'yield': lambda rec, tpl, title: str(rec.get('output', {}).get('amount', '')).strip(),
    'product': lambda rec, tpl, title: (tpl.get('product') or title).strip(),
}
