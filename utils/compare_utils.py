import mwparserfromhell
import time
from typing import Any, Dict, List, Tuple
from utils.text_utils import normalize_apostrophe, clean_whitespace
from utils.wiki_utils import fetch_pages


def parse_all_wiki_templates(
    wikitext: str,
    template_name: str
) -> List[Dict[str, str]]:
    code = mwparserfromhell.parse(wikitext)
    return [
        {param.name.strip(): param.value.strip() for param in tpl.params}
        for tpl in code.filter_templates()
        if tpl.name.matches(template_name)
    ]


def normalize_title(s: str) -> str:
    if not s:
        return ""
    t = normalize_apostrophe(s)
    t = clean_whitespace(t)
    return t.lower()


def normalize_ingredient_list(s: str) -> str:
    raw = s.replace('Inputs:', '')
    items = [item.strip().lower() for item in raw.split(';') if item.strip()]
    items.sort()
    return ';'.join(items)


def format_json_ingredients(inputs: List[Dict[str, Any]]) -> str:
    return ';'.join(f"{item['name']}*{item['amount']}" for item in inputs)


def format_json_time(hours_str: str) -> str:
    try:
        h = float(hours_str)
    except (ValueError, TypeError):
        return ""
    if h >= 1:
        hours = int(h)
        minutes = int(round((h - hours) * 60))
        return f"{hours}h{minutes}m" if minutes else f"{hours}h"
    return f"{int(round(h * 60))}m"


def normalize_time_string(s: str) -> str:
    val = s.strip().lower()
    if val.endswith('hr'):
        return val[:-2] + 'h'
    if val.endswith('min'):
        return val[:-3] + 'm'
    return val


def compare_instance(
    page_title: str,
    tpl_params: Dict[str, str],
    json_record: Dict[str, Any]
) -> List[Tuple[str, str, str]]:
    diffs: List[Tuple[str, str, str]] = []
    # Workbench
    w = tpl_params.get('workbench', '').strip()
    j = json_record.get('workbench', '').strip()
    if w.lower() != j.lower():
        diffs.append(('workbench', w, j))

    # Ingredients
    raw_w = tpl_params.get('ingredients', '')
    w_norm = normalize_ingredient_list(raw_w)
    j_norm = normalize_ingredient_list(format_json_ingredients(json_record.get('inputs', [])))
    if w_norm != j_norm:
        diffs.append(('ingredients', w_norm, j_norm))

    # Time
    raw_wt = tpl_params.get('time', '').strip()
    raw_jt = format_json_time(json_record.get('hoursToCraft', ''))
    if normalize_time_string(raw_wt) != normalize_time_string(raw_jt):
        diffs.append(('time', raw_wt, raw_jt))

    # Yield
    w_val = tpl_params.get('yield', '').strip()
    j_val = str(json_record.get('output', {}).get('amount', '')).strip()
    if w_val != j_val:
        diffs.append(('yield', w_val, j_val))

    # Product
    w_prod = tpl_params.get('product', '').strip() or page_title
    j_prod = json_record.get('output', {}).get('name', 'unknown').strip()
    if w_prod.lower() != j_prod.lower():
        diffs.append(('product', w_prod, j_prod))

    return diffs


def compare_all_recipes(
    recipe_pages: List[str],
    json_records: List[dict],
    template_name: str = "Recipe",
    batch_size: int = 50
) -> Dict[str, Any]:
    """
    Compare wiki recipe templates in paginated batches against JSON records.

    Returns a dict with:
      - debug_lines: List[str]
      - summary: {
          'mismatches': Dict[str, List[Tuple[str, str, str]]],
          'manual_review': List[Tuple[str, int, int]],
          'json_only': List[Tuple[str, int]],
          'wiki_only': List[str]
        }
    """
    # Build JSON pools using recipeID for JSON and id for templates
    json_by_product: Dict[str, List[dict]] = {}
    json_by_id: Dict[int, List[dict]] = {}
    for rec in json_records:
        raw = rec.get('output', {}).get('name', '')
        key = normalize_title(raw)
        json_by_product.setdefault(key, []).append(rec)
        try:
            rid = int(rec.get('recipeID', 0) or 0)
        except:
            rid = 0
        if rid > 100:
            json_by_id.setdefault(rid, []).append(rec)

    total = len(recipe_pages)
    processed = 0
    debug_lines: List[str] = []
    mismatches: Dict[str, List[Tuple[str, str, str]]] = {}
    manual_review: List[Tuple[str, int, int]] = []
    wiki_only: List[str] = []

    # Process in batches
    for i in range(0, total, batch_size):
        batch = recipe_pages[i:i+batch_size]
        wikitexts = fetch_pages(batch, len(batch))
        for page_title in batch:
            processed += 1
            if processed % 250 == 0:
                pct = int((processed / total) * 100)
                print(f"  🔄 Matching recipes: {pct}% complete ({processed}/{total})")

            text = wikitexts.get(page_title, "")
            tpl_list = parse_all_wiki_templates(text, template_name)
            if not tpl_list:
                continue

            product_name = tpl_list[0].get('product', '').strip() or page_title
            key = normalize_title(product_name)
            json_list = list(json_by_product.get(key, []))
            w_count = len(tpl_list)
            j_count = len(json_list)

            # No JSON records
            if j_count == 0:
                wiki_only.append(product_name)
                manual_review.append((product_name, w_count, j_count))
                for tpl in tpl_list:
                    tid = int(tpl.get('id', '').strip() or 0)
                    debug_lines.append(f"[MANUAL REVIEW]   {product_name} (ID: {tid})\n")
                continue

            # Single-recipe
            if w_count == 1 and j_count == 1:
                tpl = tpl_list[0]
                tid = int(tpl.get('id', '').strip() or 0)
                # Match by recipeID if valid, else by product name
                if tid > 100 and json_by_id.get(tid):
                    rec = json_by_id[tid].pop(0)
                    json_by_product[key].remove(rec)
                else:
                    rec = json_by_product[key].pop(0)
                    rid = int(rec.get('recipeID', 0) or 0)
                    if rid > 100 and rec in json_by_id.get(rid, []):
                        json_by_id[rid].remove(rec)
                diffs = compare_instance(page_title, tpl, rec)
                tag = "[MISMATCH]" if diffs else "[MATCH]"
                debug_lines.append(f"{tag:<16}{product_name} (ID: {tid})\n")
                if diffs:
                    mismatches[f"{product_name} (ID {tid})"] = diffs
                    for f, wv, jv in diffs:
                        debug_lines.append(f"   - {f}: wiki='{wv}' vs json='{jv}'\n")
                continue

            # Multi-recipe
            if j_count != w_count:
                manual_review.append((product_name, w_count, j_count))
            for tpl in tpl_list:
                tid = int(tpl.get('id', '').strip() or 0)
                # Only match if valid recipeID
                if tid > 100 and json_by_id.get(tid):
                    rec = json_by_id[tid].pop(0)
                    if rec in json_by_product[key]:
                        json_by_product[key].remove(rec)
                    diffs = compare_instance(page_title, tpl, rec)
                    tag = "[MISMATCH]" if diffs else "[MATCH]"
                    debug_lines.append(f"{tag:<16}{product_name} (ID: {tid})\n")
                    if diffs:
                        mismatches[f"{product_name} (ID {tid})"] = diffs
                        for f, wv, jv in diffs:
                            debug_lines.append(f"   - {f}: wiki='{wv}' vs json='{jv}'\n")
                else:
                    debug_lines.append(f"[MANUAL REVIEW]   {product_name} (ID: {tid})\n")
        time.sleep(2)

    # JSON-only leftovers
    json_only: List[Tuple[str, int]] = []
    for key, recs in json_by_product.items():
        for rec in recs:
            raw = rec.get('output', {}).get('name', '')
            rid = int(rec.get('recipeID', 0) or 0)
            debug_lines.append(f"[NOT IN WIKI]     {raw} (ID: {rid})\n")
            json_only.append((raw, rid))

    summary = {
        'mismatches': mismatches,
        'manual_review': manual_review,
        'json_only': json_only,
        'wiki_only': wiki_only
    }
    return {'debug_lines': debug_lines, 'summary': summary}
