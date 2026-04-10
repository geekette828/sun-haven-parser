"""
Item page assembler.

Combines all item exporters to produce a complete wiki page for a
single item. Accepts an ItemData object — no JSON loading or
classification calls happen here.

Replaces: formatter/page_assembly/create_item_page.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import config.constants as constants
from builders.item_data import ItemData
from formatters.item.item_infobox import export_infobox
from formatters.item.item_navbox import export_navbox
from formatters.item.item_recipe import export_recipe
from formatters.item.item_summary import export_summary

# ---------------------------------------------------------------------------
# Page-level toggles
# ---------------------------------------------------------------------------

INCLUDE_HISTORY_SECTION = True
INCLUDE_UPCOMING_BANNER = True


# ---------------------------------------------------------------------------
# Section builders (private)
# ---------------------------------------------------------------------------

def _build_banner(item: ItemData) -> str:
    if not INCLUDE_UPCOMING_BANNER:
        return ""
    return f"{{{{upcoming|First appeared in the game files in patch {constants.PATCH_VERSION}.}}}}\n"


def _build_mount_section(item: ItemData) -> str:
    cls = item.classification
    if not cls or cls.subtype.lower() != "mount":
        return ""
    base_name = item.name.rsplit(" Whistle", 1)[0]
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


def _build_wallpaper_flooring_display(item: ItemData) -> str:
    cls = item.classification
    if not cls or cls.subtype.lower() not in ("wallpaper", "flooring"):
        return ""
    base = item.name.replace(" ", "_")
    return f"\n==Display==\n[[File:{base}_display.png|300px]]"


def _build_house_display_section(item: ItemData) -> str:
    cls = item.classification
    if not cls or cls.item_type != "Item" or cls.subtype != "House Customization":
        return ""
    base = item.name.replace(" ", "_")
    if cls.category == "Patio":
        return (
            "\n==Display==\n"
            f"[[File:{base}1.png|200px]] [[Category:House images needed]]\n"
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


def _build_fish_block(item: ItemData) -> str:
    cls = item.classification
    if not cls or cls.item_type.lower() != "fish":
        return ""
    return (
        f"\n===Fished From===\n"
        "Fish availability varies by location and season. The minimum and maximum spawn chances "
        "are based on a fishing level of 0 (with no skills) and level 70 (with all relevant "
        "skills), respectively. For more information on how these values are calculated, see the "
        "[[Fishing/Spawn Chance|Fishing Calculations]] page.\n"
        f"{{{{Fish locations\n"
        f"|name = {item.name}\n"
        "|1_location = \n"
        "   |1_season = \n"
        "   |1_min = \n"
        "   |1_max = \n"
        "}}\n\n"
    )


def _build_history_section(item: ItemData) -> str:
    patch = constants.PATCH_VERSION.replace("PBE ", "").strip()
    return (
        "==History==\n"
        f"*{{{{History|{patch}|[[{item.name}]] added to the game.}}}}\n"
    )


def _build_media_trivia_comment() -> str:
    return (
        "<!--\n"
        "==Media==\n"
        "<gallery widths=\"150\" bordercolor=\"transparent\" spacing=\"small\" captionalign=\"center\">\n"
        "File:filename.png|File Description\n"
        "</gallery>\n\n"
        "==Trivia==\n"
        "*\n"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_item_page(item: ItemData, display_name: str | None = None) -> str:
    """
    Assemble and return the complete wikitext for an item page.

    Args:
        item:         The ItemData object from the builder.
        display_name: Override display name (defaults to item.name).
    """
    title = display_name or item.name
    cls = item.classification

    infobox = export_infobox(item)
    summary = export_summary(item, display_name=title)
    recipe_markup = export_recipe(item)
    navbox = export_navbox(item)

    house_display = _build_house_display_section(item).strip()
    wallpaper_floor_display = _build_wallpaper_flooring_display(item).strip()
    mount_section = _build_mount_section(item).strip()
    fish_block = _build_fish_block(item)
    banner = _build_banner(item)

    page = f"{banner}{infobox}\n\n{summary}"

    if house_display:
        page += f"\n\n{house_display}"
    if wallpaper_floor_display:
        page += f"\n\n{wallpaper_floor_display}"
    if mount_section:
        page += f"\n\n{mount_section}"

    page += f"""

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
        page += "\n" + _build_media_trivia_comment() + "-->\n"
        page += _build_history_section(item) + "\n"
    else:
        page += _build_media_trivia_comment()
        page += "==History==\n*{{History|x.x|Description of change}}-->"

    page += f"\n{navbox}"

    if cls and cls.item_type and item.is_dlc:
        page += "\n\n[[Category:Unknown dlc pack]]"

    return page
