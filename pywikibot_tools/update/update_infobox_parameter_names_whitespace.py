"""
Normalize infobox formatting:
- Ensures spacing around "=" is "|param = value"
- Replaces "selltype" with "currency"
- Applies to pages using Item infobox or Agriculture infobox
- Logs skipped reasons and exceptions
- Sleeps after every page
- Logs progress every 20%
"""

import os
import re
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pywikibot
from utils import file_utils, wiki_utils
from utils.wiki_utils import get_pages_with_template

# Setup
debug_log_path = os.path.join(".hidden", "debug_output", "pywikibot", "infobox_updates.txt")
file_utils.ensure_dir_exists(os.path.dirname(debug_log_path))
site = wiki_utils.get_site()

def log_debug(msg):
    file_utils.append_line(debug_log_path, msg)

def normalize_infobox(text, template_name):
    # Match full template block, including possible inline "}}" at end of last param
    pattern = re.compile(r"(?s)(\{\{" + re.escape(template_name) + r")(\s.*?\|[^}]*?=.*?)\}\}", re.DOTALL)
    match = pattern.search(text)
    if not match:
        log_debug(f"⚠️ Template block not found for {template_name}")
        return None

    full_block = match.group(0)
    header = match.group(1).strip()  # "{{Item infobox"
    body = match.group(2).lstrip()   # remove accidental leading newline

    changed = False
    updated_lines = []

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            param_match = re.match(r"\|(\w+)\s*=\s*(.*)", line)
            if param_match:
                param = param_match.group(1)
                value = param_match.group(2).rstrip()
                if param == "selltype":
                    param = "currency"
                new_line = f"|{param} = {value}"
                if line != new_line:
                    changed = True
                updated_lines.append(new_line)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    if not changed:
        return None

    # Check if '}}' was inline on last param in original block
    inline_closer = re.search(r"(\|\w+\s*=.*\}\})\s*$", full_block)

    if inline_closer:
        # Keep closing braces inline
        updated_lines[-1] = updated_lines[-1].rstrip() + " }}"
        new_block = header + "\n" + "\n".join(updated_lines)
    else:
        # Close on a new line
        new_block = header + "\n" + "\n".join(updated_lines) + "\n}}"

    return text.replace(full_block, new_block)

def process_page(page, index=None, total=None):
    try:
        text = page.text
        modified = None

        if "{{Item infobox" in text:
            modified = normalize_infobox(text, "Item infobox")
        elif "{{agriculture infobox" in text:
            modified = normalize_infobox(text, "agriculture infobox")
        else:
            log_debug(f"⚠️ Skipped: {page.title()} — No matching infobox found")
            print(f"⚠️ Skipped: {page.title()} — No matching infobox")
            return

        if modified and modified != text:
            page.text = modified
            page.save(summary="Normalize infobox spacing and rename selltype to currency")
            log_debug(f"✅ Updated: {page.title()}")
            print(f"✅ Edited: {page.title()}")
        else:
            log_debug(f"➡️ Skipped: {page.title()} — No changes detected")
            print(f"➡️ Skipped: {page.title()}")

    except Exception as e:
        log_debug(f"❌ Error processing {page.title()}: {e}")
        print(f"❌ Error: {page.title()} — {e}")

def main():
    log_debug("🔍 Starting infobox normalization")
    templates = ["Item infobox", "Agriculture infobox"]
    titles = set()

    for template in templates:
        found = get_pages_with_template(template, namespace=0)
        titles.update(found)

    total = len(titles)
    print(f"📄 Found {total} pages using Item or Agriculture infobox.")
    milestones = {int(total * f) for f in [0.2, 0.4, 0.6, 0.8, 1.0]}

    for idx, title in enumerate(sorted(titles), start=1):
        page = pywikibot.Page(site, title)
        process_page(page, idx, total)
        time.sleep(1)

        if idx in milestones:
            pct = int((idx / total) * 100)
            print(f"🔄 Progress: {pct}% complete ({idx}/{total})")

    log_debug(f"✅ Done. Pages checked: {total}")

if __name__ == "__main__":
    main()
