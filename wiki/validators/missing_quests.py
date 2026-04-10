"""
Compare quest names from JSON files to wiki page titles using Pywikibot.
Includes redirect recovery and progress logging.
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.stdout.reconfigure(encoding="utf-8")

from config import constants
from utils import json_utils, file_utils
from utils.wiki_utils import get_site
from itertools import islice

# Setup wiki site
site = get_site()

# Paths and filenames
json_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
quest_files = ["quest_data_BB_SQ.json", "quest_data_MainQuests.json"]

output_dir = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot")
os.makedirs(output_dir, exist_ok=True)

output_both_path = os.path.join(output_dir, "Quest_Comparison_Both.txt")
output_json_only_path = os.path.join(output_dir, "Quest_Comparison_JSONOnly.txt")
recovered_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "QuestCheck_recoveredRedirects.txt")
load_debug_log = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "QuestLoadDebug.txt")

def load_quest_names() -> set[str]:
    """Load quest names from configured JSON files."""
    quest_names = set()
    for filename in quest_files:
        filepath = os.path.join(json_path, filename)
        try:
            data = json_utils.load_json(filepath)
            for quest in data.values():
                name = quest.get("name", "").strip()
                if name:
                    quest_names.add(name)
        except Exception as e:
            file_utils.write_debug_log(f"❌ Error loading {filename}: {e}", load_debug_log)
    return quest_names


def get_all_page_titles() -> set[str]:
    """Get all page titles in the main namespace."""
    return {page.title().strip() for page in site.allpages(namespace=0)}


def recheck_redirects(titles: set[str]) -> set[str]:
    """Check if titles exist via redirect and return recovered ones."""
    recovered = set()

    def chunked(iterable, size):
        it = iter(iterable)
        while chunk := list(islice(it, size)):
            yield chunk

    for batch in chunked(list(titles), 20):
        pages = [site.pages[title] for title in batch]
        while True:
            try:
                for original, page in zip(batch, pages):
                    if page.exists():
                        recovered.add(original)
                break
            except Exception as e:
                if "ratelimited" in str(e).lower():
                    print("⚠️ Rate limited. Sleeping...")
                    time.sleep(20)
                else:
                    raise
        time.sleep(0.1)

    file_utils.write_lines(recovered_log_path, sorted(recovered))
    return recovered


def write_results(both: set[str], json_only: set[str]):
    file_utils.write_lines(output_both_path, sorted(both))
    file_utils.write_lines(output_json_only_path, sorted(json_only))
    print("✅ Quest comparison complete.")


if __name__ == "__main__":
    quest_names = load_quest_names()
    wiki_titles = get_all_page_titles()
    wiki_titles_lower = {title.lower() for title in wiki_titles}

    both = {q for q in quest_names if q.lower() in wiki_titles_lower}
    json_only = quest_names - both

    recovered = recheck_redirects(json_only)
    json_only -= recovered
    both |= recovered

    write_results(both, json_only)
