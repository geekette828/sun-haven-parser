import os
import sys

# allow imports from project root
this_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(this_dir, "..")))

import config.constants as constants
from utils.file_utils import write_lines
from utils.json_utils import load_json
from utils.compare_utils import compare_instance_generic, normalize_title
from mappings.recipe_mapping import RECIPE_FIELD_MAP, RECIPE_EXTRA_FIELDS, _normalize_time_string
from utils.text_utils import normalize_list_string

# Paths
json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "recipe_compare_report.txt")
debug_log_path = os.path.join(
    ".hidden", "debug_output", "pywikibot", "recipe_compare_debug.txt"
)

# Ensure directories exist
os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)


def main():
    print("📦 Loading recipe JSON data...")
    data = load_json(json_file_path)
    if not isinstance(data, dict):
        print(f"❌ Error: expected dict, got {type(data)}")
        return

    json_records = list(data.values())
    # Build reverse map of product name → all matching JSON entries
    json_by_product = {}
    for rec in json_records:
        key = normalize_title(rec.get("output", {}).get("name", ""))
        json_by_product.setdefault(key, []).append(rec)

    print("⚖️  Comparing recipes...")
    from utils.wiki_utils import get_pages_with_template, fetch_pages, parse_template_params
    titles = get_pages_with_template("Recipe", namespace=0)
    total = len(titles)

    debug_lines = []
    wiki_only = []
    mismatches = {}
    json_keys_used = set()

    for i in range(0, total, 50):
        batch = titles[i:i+50]
        wikitexts = fetch_pages(batch)

        for title_index, title in enumerate(batch, start=i):
            if title_index % 250 == 0 and title_index > 0:
                pct = int((title_index / total) * 100)
                print(f"  🔄 Recipe compare: {pct}% complete ({title_index}/{total})")

            text = wikitexts.get(title, "")
            tpl_params = parse_template_params(text, "Recipe")
            tpl_params["ingredients"] = normalize_list_string(tpl_params.get("ingredients", ""))
            tpl_params["time"] = _normalize_time_string(tpl_params.get("time", ""))

            if not tpl_params:
                wiki_only.append(title)
                debug_lines.append(f"[WIKI ONLY] {title}\n")
                continue

            # Use product as the record key
            product = tpl_params.get("product") or title
            record_key = normalize_title(product)
            possible_matches = json_by_product.get(record_key, [])
            recipe_id = tpl_params.get("id", "").strip()
            id_part = f" (ID: {recipe_id})" if recipe_id else ""

            record = None
            if len(possible_matches) == 1:
                record = possible_matches[0]
            elif len(possible_matches) > 1:
                # Try to match by recipe ID
                record = next((r for r in possible_matches if str(r.get("recipeID", "")) == recipe_id), None)
                if not record:
                    debug_lines.append(f"[MANUAL REVIEW] {title}{id_part} - Multiple JSON matches, ID not found\n")
                    continue
            else:
                wiki_only.append(title)
                debug_lines.append(f"[WIKI ONLY] {title}{id_part}\n")
                continue

            json_keys_used.add(record_key)

            diffs = compare_instance_generic(tpl_params, record, RECIPE_FIELD_MAP, RECIPE_EXTRA_FIELDS, title)
            tag = "[MISMATCH]" if diffs else "[MATCH]   "
            debug_lines.append(f"{tag} {title}{id_part}\n")
            if diffs:
                mismatches[title] = diffs
                for field, wv, jv in diffs:
                    debug_lines.append(f"  - {field}: wiki='{wv}' vs json='{jv}'\n")

    # Identify unused JSON entries
    all_json_keys = set(json_by_product.keys())
    json_only = sorted(all_json_keys - json_keys_used)
    for key in json_only:
        debug_lines.append(f"[JSON ONLY] {key}\n")

    # Final output
    print("📝 Writing debug log...")
    write_lines(debug_log_path, debug_lines)

    lines = []
    lines.append("=== VALUE MISMATCHES ===\n")
    for title, diffs in mismatches.items():
        lines.append(f"{title}\n")
        for field, wv, jv in diffs:
            lines.append(f" - {field}: wiki='{wv}' vs json='{jv}'\n")

    lines.append("\n=== WIKI ONLY ===\n")
    for title in wiki_only:
        lines.append(f"{title}\n")

    lines.append("\n=== JSON ONLY ===\n")
    for key in json_only:
        lines.append(f"{key}\n")

    write_lines(output_file_path, lines)
    print(f"✅ Recipe comparison complete: see report at {output_file_path}")


if __name__ == "__main__":
    main()
