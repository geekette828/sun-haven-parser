import re
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

    # 1. Check for commented-out ==History==
    comment_blocks = list(re.finditer(r"<!--(.*?)-->", wikitext, re.DOTALL))
    for block in comment_blocks:
        block_text = block.group(1)
        if "==History==" in block_text:
            # Clean the comment block: remove ==History== and example bullet
            lines = block_text.splitlines()
            cleaned_lines = []
            skipping = False
            for line in lines:
                if "==History==" in line:
                    skipping = True
                    continue
                if skipping and "*{{History|" in line:
                    continue
                if skipping and (line.strip() == "" or line.strip().startswith("*")):
                    continue
                cleaned_lines.append(line)

            cleaned_comment = "<!--\n" + "\n".join(cleaned_lines).rstrip() + "\n-->\n"
            visible_history = f"==History==\n{new_entry}\n\n"

            # Get full span and rebuild precisely
            start, end = block.span()
            before = wikitext[:start]
            after = wikitext[end:]

            # Clean up after spacing
            before = before.rstrip() + "\n"
            after = after.lstrip()

            # Clean comment block
            cleaned_comment = "<!--\n" + "\n".join(cleaned_lines).rstrip() + "\n-->"
            visible_history = "==History==\n" + new_entry + "\n\n"

            # Combine with clean spacing
            rebuilt = before + cleaned_comment + "\n" + visible_history + after
            return rebuilt

    # 2. Check for existing visible History section
    if "==History==" in wikitext:
        lines = wikitext.splitlines()
        out = []
        in_history = False
        inserted = False

        for i, line in enumerate(lines):
            if line.strip() == "==History==":
                in_history = True
                out.append(line)
                continue

            if in_history:
                # Continue collecting history bullet lines
                if line.strip().startswith("*"):
                    out.append(line)
                    continue
                if not inserted:
                    out.append(new_entry)
                    inserted = True
                in_history = False  # Done with history, resume normal lines

            out.append(line)

        # Fallback if ==History== existed but no bullets were found
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

