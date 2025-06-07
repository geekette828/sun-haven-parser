"""
Field mapping for comparing Recipe template fields against recipe JSON data.
Exports:
  RECIPE_FIELD_MAP: dict of template_param -> (json_field_key, normalization_fn)
  RECIPE_EXTRA_FIELDS: dict of template_param -> function(json_record, tpl_params, title)
  _normalize_ingredient_list, _normalize_time_string, _normalize_wiki_product
"""

from utils.text_utils import normalize_list_string
from typing import Dict, Tuple, Any, Callable

# JSON‑side helpers
def _normalize_ingredient_list(s: str) -> str:
    return normalize_list_string(s.replace('Inputs:', ''))

def _format_json_ingredients(inputs):
    return "; ".join(f"{item['name']}*{item['amount']}" for item in inputs if item.get("name") and item.get("amount"))

def _format_json_time(hours):
    if not hours:
        return ""
    minutes = int(round(float(hours) * 60))
    return f"{minutes}min"

def _normalize_time_string(s: str) -> str:
    val = (s or '').strip().lower()
    if val.endswith('hr'):
        return val[:-2] + 'h'
    if val.endswith('min'):
        return val[:-3] + 'm'
    return val

# WIKI‑side helper for product fallback
def _normalize_wiki_product(s: str, title: str) -> str:
    v = (s or '').strip()
    return v if v else title

# Mapping of template parameters to JSON fields and normalization functions
RECIPE_FIELD_MAP: Dict[str, Tuple[str, Callable[[Any], str]]] = {
    "workbench": ("workbench", lambda v: (v or "").strip()),
    "ingredients": ("inputs", _format_json_ingredients),
    "time": ("hoursToCraft", _format_json_time),
    "yield": ("output", lambda out: str(out.get("amount", "")).strip() if isinstance(out, dict) else ""),
    "product": ("output", lambda out: (out.get("name") or "").strip() if isinstance(out, dict) else ""),
}

RECIPE_COMPUTE_MAP: Dict[str, Callable[[Any], str]] = {
    "id": lambda rec: str(rec.get("recipeID", "")).strip() if rec else ""
}

# For fields with json_key=None, values come from these computed functions
# These now receive tpl_params and page title for context
RECIPE_EXTRA_FIELDS: Dict[str, Callable[[Dict[str, Any], Dict[str, str], str], str]] = {
    'ingredients': lambda rec, tpl, title: _normalize_ingredient_list(
        _format_json_ingredients(rec.get('inputs'))
    ),
    'time': lambda rec, tpl, title: _normalize_time_string(
        _format_json_time(rec.get('hoursToCraft'))
    ),
    'yield': lambda rec, tpl, title: str(rec.get('output', {}).get('amount', '')).strip(),
    'product': lambda rec, tpl, title: (tpl.get('product') or title).strip(),
}
