import os
import sys
import time
import pywikibot

# allow imports from project root
the_path = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(the_path, "..")))

import config.constants as constants
from utils import file_utils
from utils.json_utils import load_json
from utils.wiki_utils import get_pages_with_template
from utils.compare_utils import compare_all_recipes

# Paths
json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "recipes_data.json")
output_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "recipe_compare_v2.txt")
debug_log_path = os.path.join(".hidden", "debug_output", "pywikibot", "recipe_compare_debug_v2.txt")

# Ensure directories exist
os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)


def main():
    # 1. Load wiki recipe pages
    print("📦 Loading recipe pages...")
    wiki_titles = get_pages_with_template("Recipe", namespace=0)
    print(f"🔍 Found {len(wiki_titles)} recipe pages on wiki.")

    # 2. Load JSON data
    print("📦 Loading JSON data from file...")
    data = load_json(json_file_path)
    if not isinstance(data, dict):
        print(f"❌ Error: expected dict, got {type(data)}")
        return
    records = list(data.values())

    # 3. Compare in batches and get results
    print("⚖️  Comparing recipes...")
    results = compare_all_recipes(wiki_titles, records)

    # 4. Write debug log
    print(f"📝 Writing debug log to {debug_log_path}")
    file_utils.write_lines(debug_log_path, results["debug_lines"])

    # 5. Generate summary output
    summary = results["summary"]
    lines = []

    # VALUE MISMATCHES
    lines.append("=== VALUE MISMATCHES ===\n")
    for title, diffs in summary["mismatches"].items():
        lines.append(f"{title}\n")
        for field, wv, jv in diffs:
            lines.append(f" - {field}: wiki='{wv}' vs json='{jv}'\n")

    # MANUAL REVIEW
    lines.append("\n=== MANUAL REVIEW ===\n")
    for product, wcnt, jcnt in summary["manual_review"]:
        lines.append(f"{product} — wiki templates: {wcnt}, json records: {jcnt}\n")

    # JSON ONLY
    lines.append("\n=== JSON ONLY ===\n")
    for raw, rid in summary["json_only"]:
        lines.append(f"{raw} (ID: {rid})\n")

    # WIKI ONLY
    lines.append("\n=== WIKI ONLY ===\n")
    for product in summary["wiki_only"]:
        lines.append(f"{product}\n")

    file_utils.write_lines(output_file_path, lines)
    print(f"✅ Recipe comparison complete: results in {output_file_path}")


if __name__ == "__main__":
    main()