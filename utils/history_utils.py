import re
import mwparserfromhell
from datetime import datetime

import mwparserfromhell
from datetime import datetime

def append_history_entry(wikitext: str, summary: str, patch: str) -> str:
    """
    Ensures the ==History== section exists and appends a new bullet with the given patch and summary.
    Handles commented-out, missing, or already-present history sections. Uses mwparserfromhell for safety.
    """
    date_str = datetime.today().strftime("%Y-%m-%d")
    new_entry = f"*{{{{History|{patch}|{summary}}}}}"
    parsed = mwparserfromhell.parse(wikitext)

    # 1. Check if history is commented out
    if "<!--" in wikitext and "==History==" in wikitext:
        # Extract the comment block and rebuild with visible History
        comment_start = wikitext.find("<!--")
        comment_end = wikitext.find("-->", comment_start)
        comment_block = wikitext[comment_start:comment_end+3]
        if "==History==" in comment_block:
            pre = comment_block.split("==History==")[0]
            visible_history = f"==History==\n{new_entry}\n"
            new_block = f"<!--{pre.strip()}-->\n\n{visible_history}"
            rest = wikitext[comment_end+3:]
            return wikitext.replace(comment_block, new_block + rest)

    # 2. Check for existing visible History section
    if "==History==" in wikitext:
        lines = wikitext.splitlines()
        out = []
        inserted = False
        for line in lines:
            out.append(line)
            if line.strip() == "==History==" and not inserted:
                inserted = True
            elif inserted and line.startswith("*"):
                continue
            elif inserted:
                out.insert(len(out) - 1, new_entry)
                break
        if not inserted:
            out.append(new_entry)
        return "\n".join(out)

    # 3. No history section — insert before last navbox or category
    nodes = parsed.nodes
    insert_index = len(nodes)

    for i in reversed(range(len(nodes))):
        node = nodes[i]
        if isinstance(node, mwparserfromhell.nodes.Template):
            if "navbox" in node.name.lower():
                insert_index = i
        elif isinstance(node, mwparserfromhell.nodes.Text):
            if node.value.strip().startswith("[[Category:"):
                insert_index = i

    # Clean excessive blank lines before insert
    if insert_index > 0 and isinstance(nodes[insert_index - 1], mwparserfromhell.nodes.Text):
        prev_text = nodes[insert_index - 1].value.rstrip()
        nodes[insert_index - 1].value = prev_text + "\n"

    # Now insert history with exactly 1 blank line before, 2 after
    history_block = f"\n==History==\n*{{{{History|{patch}|{summary}}}}}\n\n\n"
    parsed.insert(insert_index, mwparserfromhell.parse(history_block))
    return str(parsed).strip() + "\n"

