"""
Compare quest names from JSON files to wiki page titles using Pywikibot.
Includes redirect checking and shared config setup.
"""

import sys
import os
import time
from itertools import islice
import pywikibot

import config.constants as constants
from utils import json_utils, file_utils

# Setup PWB and site
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
pywikibot.config.throttle = constants.PWB_SETTINGS["throttle"]
pywikibot.config.max_retries = constants.PWB_SETTINGS["max_retries"]
pywikibot.config.retry_wait = constants.PWB_SETTINGS["retry_wait"]
pywikibot.config.user_agent = constants.PWB_SETTINGS["user_agent"]
site = pywikibot.Site("en", "sunhaven")

# Paths
json_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data")
quest_files = ["quest_data_BB_SQ.json", "quest_data_MainQuests.json"]
output_dir = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot")
debug_dir = os.path.join(constants.OUTPUT_DIRECTORY, "Debug")
os.makedirs(output_dir, exist_ok=True)
os.makedirs(debug_dir, exist_ok=True)

output_both_path = os.path.join(output_dir, "Quest_Comparison_Both.txt")
output_json_only_path = os.path.join(output_dir, "Quest_Comparison_JSONOnly.txt")
recovered_log_path = os.path.join(debug_dir, "QuestCheck_recoveredRedirects.txt")

# Load quest names from JSON
def load_quest_names():
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
            file_utils.write_debug_log(f"❌ Error loading {filename}: {e}", os.path.join(debug_dir, "QuestLoadDebug.txt"))
    return quest_names

# Get all wiki pages (namespace 0)
def get_all_wiki_pages():
    all_pages = set()
    for page in site.allpages(namespace=0):
        all_pages.add(page.title().strip())
    return all_pages

# Recheck JSON-only quests for redirect matches
def recheck_json_only(json_only):
    recovered = set()
    to_check = list(json_only)

    def chunked(iterable, size):
        it = iter(iterable)
        while True:
            chunk = list(islice(it, size))
            if not chunk:
                break
            yield chunk

    batch_size = 20
    for batch in chunked(to_check, batch_size):
        pages = [pywikibot.Page(site, name) for name in batch]
        while True:
            try:
                for original, page in zip(batch, pages):
                    if page.exists():
                        recovered.add(original)
                break
            except pywikibot.exceptions.APIError as e:
                if 'ratelimited' in str(e).lower():
                    print(f"⚠️ Rate limited. Sleeping for {batch_size} seconds...")
                    time.sleep(batch_size)
                    batch_size = min(batch_size * 2, 60)
                else:
                    raise
        time.sleep(0.1)

    file_utils.write_lines(recovered_log_path, [f"{q}\n" for q in sorted(recovered)])
    return recovered

# Write output files
def write_outputs(both, json_only):
    file_utils.write_lines(output_both_path, [q + "\n" for q in sorted(both)])
    file_utils.write_lines(output_json_only_path, [q + "\n" for q in sorted(json_only)])
    print("✅ Quest comparison complete.")

# Main logic
if __name__ == "__main__":
    quest_names = load_quest_names()
    wiki_titles = get_all_wiki_pages()
    wiki_titles_lower = {t.lower() for t in wiki_titles}

    both = {q for q in quest_names if q.lower() in wiki_titles_lower}
    json_only = quest_names - both

    recovered = recheck_json_only(json_only)
    json_only -= recovered
    both |= recovered

    write_outputs(both, json_only)