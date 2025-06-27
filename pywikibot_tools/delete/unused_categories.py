'''
This script uses Special:UnusedCategories to efficiently find and delete unused categories that start or end with a specific phrase. 
It logs all actions, deletes matching empty categories using Pywikibot, and skips those that don’t match the phrase.
'''

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from utils import file_utils, wiki_utils

# Define paths
debug_log_path = os.path.join(constants.DEBUG_DIRECTORY, "pywikibot", "delete_unused_categories_debug.txt")

file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

# Configurations
PHRASE = "Drops "  # Change this to the desired phrase
MATCH_START = True
MATCH_END = False

site = wiki_utils.get_site()

def log_debug(msg):
    file_utils.append_line(debug_log_path, msg)

def should_match(title):
    title_lower = title.lower()
    phrase_lower = PHRASE.lower()
    if MATCH_START and title_lower.startswith(phrase_lower):
        return True
    if MATCH_END and title_lower.endswith(phrase_lower):
        return True
    return False

def main():
    log_debug("🔍 Starting unused category cleanup via site.querypage('Unusedcategories')")
    count_deleted = 0
    count_skipped = 0

    for page in site.querypage('Unusedcategories'):
        cat_title = page.title(with_ns=False)  # Strip "Category:"
        if not should_match(cat_title):
            continue

        try:
            log_debug(f"🗑️ Deleting: {page.title()}")
            page.delete(reason="Unused category cleanup", prompt=False)
            count_deleted += 1
            time.sleep(1)
        except Exception as e:
            log_debug(f"❌ Error deleting {page.title()}: {e}")
            count_skipped += 1

    log_debug(f"✅ Complete. Deleted: {count_deleted}, Skipped: {count_skipped}")

if __name__ == "__main__":
    main()