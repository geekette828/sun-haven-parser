import os
import re
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from utils import file_utils, wiki_utils
import pywikibot

site = wiki_utils.get_site()
debug_log_path = os.path.join(".hidden", "debug_output", "pywikibot", "media_rename_log.txt")
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))

def log_debug(msg):
    file_utils.append_line(debug_log_path, msg)

def normalize_bust_filename(filename):
    if not filename.lower().endswith('.png'):
        return None

    base = filename[:-4]
    parts = base.split(' ')
    if "Bust" not in parts:
        return None

    try:
        bust_index = parts.index("Bust")
        before = " ".join(parts[:bust_index])       # Could be Season or NPC
        after = " ".join(parts[bust_index + 1:])     # Should be either Season-NPC or NPC-emotion

        if '-' not in after:
            return None

        left, emotion = after.split('-', 1)
        emotion = emotion.lower()

        # Heuristic: if before is a season, then `left` must be NPC
        # if before is NPC, then `left` must be season
        if re.match(r"^[A-Z][a-z]+$", before) and re.match(r"^[A-Z][a-z]+$", left):
            # Either order — normalize both ways
            season = before if before in SEASONS else left
            npc = left if before in SEASONS else before
        else:
            return None

        new_filename = f"{season} Bust {npc}-{emotion}.png"
        if new_filename != filename:
            return new_filename
        return None
    except Exception:
        return None

SEASONS = {"Spring", "Summer", "Fall", "Winter", "Swimsuit", "Halloween", "Wedding"}

def rename_file(old_name, new_name):
    old_title = pywikibot.FilePage(site, old_name)
    new_title = pywikibot.FilePage(site, new_name)
    try:
        if not old_title.exists():
            log_debug(f"❌ File does not exist: {old_name}")
            return False
        if new_title.exists():
            log_debug(f"⚠️ Target file already exists: {new_name}")
            return False

        old_title.move(new_title.title(), reason="Normalize RNPC bust filename", movetalk=True, noredirect=True)
        log_debug(f"✅ Renamed: {old_name} → {new_name}")
        return True
    except Exception as e:
        log_debug(f"❌ Error renaming {old_name}: {e}")
        return False

def process_npc(npc_name):
    page_title = f"{npc_name}/Media"
    page = pywikibot.Page(site, page_title)

    if not page.exists():
        log_debug(f"⛔ Page does not exist: {page_title}")
        return

    text = page.text
    updated = text
    changes = 0

    # Grab all <gallery> sections and extract .png filenames
    gallery_matches = re.findall(r'<gallery[^>]*?>(.*?)</gallery>', text, re.DOTALL)
    all_files = []

    for gallery in gallery_matches:
        for line in gallery.strip().splitlines():
            parts = line.strip().split('|')
            if parts:
                fname = parts[0].strip()
                if fname.lower().endswith('.png'):
                    all_files.append(fname)

    log_debug(f"Found {len(all_files)} .png files in galleries on {page_title}")

    for original in all_files:
        corrected = normalize_bust_filename(original)
        if corrected:
            log_debug(f"→ Needs rename: {original} → {corrected}")
            renamed = rename_file(original, corrected)
            if renamed:
                updated = updated.replace(original, corrected)
                changes += 1

    if changes > 0 and updated != text:
        try:
            page.text = updated
            page.save(summary="Updated bust filenames to match naming convention")
            log_debug(f"📝 Updated page: {page_title} ({changes} replacements)")
        except Exception as e:
            log_debug(f"❌ Failed to update page {page_title}: {e}")
    else:
        log_debug(f"✅ No changes needed for {page_title}")

def main():
    rnpc_list = [
        "Anne",
        "Catherine",
        "Iris",
        "Kitty",
        "Lucia",
        "Lynn",
        "Miyeon",
        "Vivi",
        "Xyla",
        "Zaria",
        "Claude",
        "Darius",
        "Donovan",
        "Jun",
        "Kai",
        "Karish",
        "Liam",
        "Lucius",
        "Nathaniel",
        "Shang",
        "Vaan",
        "Wesley",
        "Wornhardt"
    ]

    for i, name in enumerate(rnpc_list, 1):
        name = name.strip()
        if not name:
            continue
        log_debug(f"\n--- [{i}] Processing {name} ---")
        process_npc(name)
        time.sleep(1)  # be nice to the API

if __name__ == "__main__":
    main()
