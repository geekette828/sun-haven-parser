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
def _format_json_ingredients(inputs: Any) -> str:
    return ';'.join(f"{item['name']}*{item['amount']}" for item in inputs or [])

def _normalize_ingredient_list(s: str) -> str:
    return normalize_list_string(s.replace('Inputs:', ''))

def _format_json_time(hours: Any) -> str:
    try:
        h = float(hours)
    except (ValueError, TypeError):
        return ''
    if h >= 1:
        hours_i = int(h)
        minutes = int(round((h - hours_i) * 60))
        return f"{hours_i}h{minutes}m" if minutes else f"{hours_i}h"
    return f"{int(round(h * 60))}m"

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
    'workbench': ('workbench', lambda v: (v or '').strip()),
    'ingredients': (None, lambda rec: _normalize_ingredient_list(
        _format_json_ingredients(rec.get('inputs'))
    )),
    'time': (None, lambda rec: _format_json_time(rec.get('hoursToCraft'))),
    'yield': (None, lambda rec: str(rec.get('output', {}).get('amount', '')).strip()),
    'product': (None, lambda rec: (rec.get('output', {}).get('name') or '').strip()),
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
