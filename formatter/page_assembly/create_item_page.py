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
INCLUDE_UPCOMING_BANNER = True

def normalize_name(name):
    return clean_whitespace(name).lower()

def build_mount_section(item):
    _, subtype, _ = classify_item(item)
    if subtype.lower() != "mount":
        return ""
    title = item.get("Name") or item.get("name") or "ITEMNAME"
    base_name = title.rsplit(" Whistle", 1)[0]
    if "mount" not in base_name.lower():
        base_name += " Mount"
    return (
        "\n==Display==\n"
        "Mount image needed [[Category:Mount image needed]]\n"
        "<gallery widths=\"150\" bordercolor=\"transparent\" spacing=\"small\" captionalign=\"center\">\n"
        f"{base_name}_Front.png|Front\n"
        f"{base_name}.png|Side\n"
        "</gallery>\n"
    )

def build_wallpaper_flooring_display(item, display_name):
    _, subtype, _ = classify_item(item)
    if subtype.lower() in ("wallpaper", "flooring"):
        base_name = display_name.replace(" ", "_")
        return (
            "\n==Display==\n"
            f"[[File:{base_name}_display.png|300px]]"
        )
    return ""

def build_house_display_section(item, display_name):
    itemType, subtype, category = classify_item(item)
    if itemType != "Item" or subtype != "House Customization":
        return ""

    base = display_name.replace(" ", "_")
    
    # Skip Patio (no numbered images)
    if category == "Patio":
        return (
        "\n==Display==\n"
        f'[[File:{base}1.png|200px]] [[Category:House images needed]]\n'
    )

    return (
        "\n==Display==\n"
        '{| class="table-bottom tablexsmall" style="text-align: center; border-spacing: 10px;"\n'
        "|-\n"
        f'|style="vertical-align: bottom; width:33%;"|[[File:{base}1.png|150px]]<br>Tier 1 House\n'
        f'|style="vertical-align: bottom; width:33%;"|[[File:{base}2.png|150px]]<br>Tier 2 House\n'
        f'|style="vertical-align: bottom; width:33%;"|[[File:{base}3.png|150px]]<br>Tier 3 House\n'
        "|} [[Category:House images needed]]\n"
    )

def build_history_section(display_name):
    patch = constants.PATCH_VERSION
    return (
        f"==History==\n"
        f"*{{{{History|{patch}|[[{display_name}]] added to the game.}}}}\n"
    )

def build_media_trivia_comment():
    return """<!--
==Media==
<gallery widths=\"150\" bordercolor=\"transparent\" spacing=\"small\" captionalign=\"center\">
File:filename.png|File Description
</gallery>

==Trivia==
*
"""

def create_item_page(item, display_name=None):
    classification = classify_item(item)
    itemType, subtype, category = classification

    display_title = display_name or item.get("name", "ITEMNAME")

    infobox = format_infobox(item, classification, display_title)
    computed = parse_infobox(infobox)
    summary = create_item_summary(item, computed, display_title)
    house_display = build_house_display_section(item, display_title).strip()
    wallpaper_floor_display = build_wallpaper_flooring_display(item, display_title).strip()
    mount_section = build_mount_section(item, display_title).strip()
    recipe_markup = get_recipe_markup_for_item(item)
    navbox = create_item_navbox(item)

    banner = (
        f"{{{{upcoming|First appeared in the game files in PBE patch {constants.PATCH_VERSION}.}}}}\n"
        if INCLUDE_UPCOMING_BANNER else ""
    )

    is_fish = (
        (itemType or "").lower() == "fish"
        or (subtype or "").lower() == "fish"
    )

    fish_block = (
        f"""
===Fished From===
Fish availability varies by location and season. The minimum and maximum spawn chances are based on a fishing level of 0 (with no skills) and level 70 (with all relevant skills), respectively. For more information on how these values are calculated, see the [[Fishing/Spawn Chance|Fishing Calculations]] page.
{{{{Fish locations
|name = {display_title}
|1_location = 
   |1_season = 
   |1_min = 
   |1_max = 
}}}}

"""
        if is_fish else ""
    )

    page_template = f"""{banner}{infobox}\n\n{summary}"""

    if house_display:
        page_template += f"\n\n{house_display}"
    if wallpaper_floor_display:
        page_template += f"\n\n{wallpaper_floor_display}"
    if mount_section:
        page_template += f"\n\n{mount_section}"

    page_template += f"""

==Acquisition==
{fish_block}===Purchased From===
{{{{Shop availability}}}}

===Crafting===
{recipe_markup}

===Collected From===
{{{{Item collected from}}}}

==Item Uses==
{{{{Item as ingredient}}}}

==Gifting==
===Gifting to NPCs===
{{{{Gifted item}}}}

===Gifted From===
{{{{Gift sources}}}}

==Quests==
===Requires===
{{{{Quest requires item}}}}

===Rewards===
{{{{Quest rewards item}}}}
"""

    if INCLUDE_HISTORY_SECTION:
        page_template += "\n" + build_media_trivia_comment() + "-->\n" + build_history_section(display_title) + "\n"
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
        "Ethereal Pegasus Mount Whistle", "Astral Wallpaper", "Arcade Flooring", "Spring Door", "Myths and Muses Chair"
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