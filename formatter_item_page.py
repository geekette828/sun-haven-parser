import os
from utils import json_utils, file_utils
import config.constants as constants
from formatter_itemInfobox import create_full_infobox
from formatter_item_page_summary import create_item_summary, parse_infobox
from formatter_item_page_navbox import create_item_navbox  # New import

def create_item_page(item, display_name=None):
    # Generate the item infobox (which already has computed values)
    infobox = create_full_infobox(item)
    # Parse the infobox to extract computed fields
    computed = parse_infobox(infobox)
    # Generate the summary using the computed values; pass display_name if provided
    summary = create_item_summary(item, computed, display_name)
    # Get the appropriate navbox using the new navbox function.
    navbox = create_item_navbox(item)
    
    # Build the base wiki page using your template with double curly brackets.
    page_template = f"""{infobox}

{summary}

==Acquisition==
===Purchased From===
{{{{Shop availability}}}}

===Crafting===
{{{{Recipe/none}}}}

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
    return page_template

def main():
    json_file_path = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "items_data.json")
    output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Wiki Pages")
    file_utils.ensure_dir_exists(output_directory)
    
    try:
        items_data = json_utils.load_json(json_file_path)
    except Exception as e:
        print("Error loading JSON data:", e)
        return

    items_data_lower = { key.lower(): value for key, value in items_data.items() }
    test_items = [
        "iris shirt", 
        "iris skirt", 
        "iris wig",
        "Jiggles",
        "Glorite Watering Can",
        "Acorn Anchovy"
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
