import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import config.constants as constants
from utils import json_utils, file_utils
from utils.text_utils import clean_whitespace
from mappings.item_infobox_mapping import format_infobox
from formatter.item_summary import create_item_summary, parse_infobox
from formatter.navbox import create_item_navbox
from formatter.item_recipe import get_recipe_markup_for_item
from mappings.item_classification import classify_item

INCLUDE_HISTORY_SECTION = True  # Toggle for showing ==History== section

def normalize_name(name):
    return clean_whitespace(name).lower()

def build_mount_section(item):
    itemType, _, _ = classify_item(item)
    if itemType.lower() != "mount":
        return ""
    title = item.get("name", "ITEM NAME")
    base_name = title.rsplit(" Whistle", 1)[0]
    if "mount" not in base_name.lower():
        base_name += " Mount"
    return (
        "\n\n==Mount Display==\n"
        "<gallery widths=\"150\" bordercolor=\"transparent\" spacing=\"small\" captionalign=\"center\">\n"
        f"{base_name}.png|Front\n"
        f"{base_name}_Side.png|Side\n"
        "</gallery>\n"
    )

def build_history_section(display_name):
    patch = constants.PATCH_VERSION
    return (
        f"==History==\n"
        f"*{{{{History|{patch}|{display_name} added to the game.}}}}\n"
    )

def build_media_trivia_comment():
    return """<!--
==Media==
<gallery widths=\"200\" bordercolor=\"transparent\" spacing=\"small\" captionalign=\"center\">
File:filename.png|File Description
</gallery>

==Trivia==
*
"""

def create_item_page(item, display_name=None):
    classification = classify_item(item)
    infobox = format_infobox(item, classification, display_name or item.get("name", "ITEM NAME"))
    computed = parse_infobox(infobox)
    summary = create_item_summary(item, computed, display_name)
    mount_section = build_mount_section(item)
    recipe_markup = get_recipe_markup_for_item(item)
    navbox = create_item_navbox(item)

    # Build core page content
    page_template = f"""{infobox}

{summary}
{mount_section}
==Acquisition==
===Purchased From===
{{{{Shop availability}}}}

===Crafting===
{recipe_markup}

===Dropped By===
{{{{Item as drop}}}}

==Item Uses==
{{{{Item as ingredient}}}}

==Gifting==
===Gifting to NPCs===
{{{{Gifted item}}}}

===Gifted From===
* The player does not currently get this item from any NPC.

==Quests==
===Requires===
{{{{Quest requires item}}}}

===Rewards===
{{{{Quest rewards item}}}}
"""

    if INCLUDE_HISTORY_SECTION:
        if display_name is None:
            display_name = item.get("name", "ITEM NAME")
        page_template += "\n" + build_media_trivia_comment() + "-->\n" + build_history_section(display_name) + "\n"
    else:
        page_template += build_media_trivia_comment() + "==History==\n*{{History|x.x|Description of change}}-->"

    page_template += f"\n{navbox}"

    if computed.get("dlc", "false").lower() == "true":
        page_template += "\n\n[[Category:Unknown dlc pack]]"

    return page_template

def main():
    json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
    output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Item Pages")
    file_utils.ensure_dir_exists(output_directory)

    try:
        items_data = json_utils.load_json(json_file_path)
    except Exception as e:
        print("Error loading JSON data:", e)
        return

    items_data_lower = { key.lower(): value for key, value in items_data.items() }
    test_items = [
        "Simple Adamant Hammer"
    ]

    for item_name in test_items:
        key = item_name.lower()
        if key in items_data_lower:
            item = items_data_lower[key]
            page_content = create_item_page(item, display_name=item_name)
            safe_filename = item_name.replace(" ", "_").replace("'", "")
            output_file = os.path.join(output_directory, f"{safe_filename}.txt")
            try:
                file_utils.write_lines(output_file, [page_content])
                print(f"Created wiki page for {item_name}.")
            except Exception as e:
                print(f"Failed to write page for {item_name}: {e}")
        else:
            print(f"Item '{item_name}' not found in data.")

if __name__ == "__main__":
    main()