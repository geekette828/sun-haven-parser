# formatter_item_page.py
import os
from utils import json_utils, file_utils
from utils.text_utils import clean_whitespace
import config.constants as constants
from formatter.item_page.infobox import create_full_infobox
from formatter.item_page.summary import create_item_summary, parse_infobox
from formatter.item_page.navbox import create_item_navbox
from formatter.item_page.recipe import get_recipe_markup_for_item

def normalize_name(name):
    return clean_whitespace(name).lower()

def create_item_page(item, display_name=None):
    # Generate the item infobox (which already has computed values)
    infobox = create_full_infobox(item)
    # Parse the infobox to extract computed fields
    computed = parse_infobox(infobox)
    # Generate the summary using computed values; pass display_name if provided.
    summary = create_item_summary(item, computed, display_name)
    # Get the appropriate navbox using the new navbox function.
    navbox = create_item_navbox(item)
    
    # Determine if we need to add a Mount Display section.
    from formatter.item_page.infobox_classifications import classify_item
    itemType, subtype, _ = classify_item(item)
    mount_section = ""
    if itemType.lower() == "mount":
        title = item.get("name", "ITEM NAME")
        base_name = title.rsplit(" Whistle", 1)[0]
        if "mount" not in base_name.lower():
            base_name += " Mount"
        mount_section = (
            "\n\n==Mount Display==\n"
            "<gallery widths=\"150\" bordercolor=\"transparent\" spacing=\"small\" captionalign=\"center\">\n"
            f"{base_name}.png|Front\n"
            f"{base_name}_Side.png|Side\n"
            "</gallery>\n"
        )
    
    # Lookup the recipe for this item. Use the item name as the lookup key.
    recipe_markup = get_recipe_markup_for_item(item)
    
    # Build the complete page template.
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
<!--
==Media==
<gallery widths="200" bordercolor="transparent" spacing="small" captionalign="center">
File:filename.png|File Description
</gallery>

==Trivia==
*

==History==
*{{{{History|x.x|Description of change}}}}-->

{navbox}"""
    
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
    test_items = [ #This is not used when called from pywikibot_create_item_page.py
        "Beach Sand Floor Tile"
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
