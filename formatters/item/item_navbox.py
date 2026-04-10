"""
Item navbox exporter.

Accepts an ItemData object and returns the appropriate navbox
wikitext template string.

Replaces: formatter/page_section/navbox.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from builders.item_data import ItemData


def export_navbox(item: ItemData) -> str:
    """
    Return the navbox wikitext for the given item.

    Falls back to ``[[Category:Navbox needed]]`` for unrecognised types.
    """
    cls = item.classification
    if cls is None:
        return "[[Category:Navbox needed]]"

    item_type = cls.item_type
    subtype = cls.subtype.lower()
    category = cls.category

    if item_type == "Animal":
        return f"{{{{Animal navbox|{cls.subtype}}}}}"
    if item_type == "Fish":
        return "{{Fish navbox}}"
    if item_type == "Furniture":
        return f"{{{{Furniture navbox|{cls.subtype}}}}}"
    if subtype == "mount":
        return "{{Animal navbox|mounts}}"
    if subtype == "clothing":
        return f"{{{{Clothing navbox|{category}}}}}"
    if subtype in ("armor", "accessory", "weapon", "tool"):
        return f"{{{{Equipment navbox|{cls.subtype}}}}}"
    if subtype == "house customization":
        return "{{Building customization navbox|house}}"

    return "[[Category:Navbox needed]]"
