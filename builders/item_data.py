"""
Data models for the Item builder.

ItemData is the intermediate representation produced by the item builder
and consumed by exporters and wiki updaters. It is also serialized to JSON
as a cache / human-readable reference file.

Sub-dataclasses (StatEntry, FoodStatEntry, StatBuffEntry, CropStage,
ItemClassification) represent nested structures extracted from the raw
game files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Sub-dataclasses
# ---------------------------------------------------------------------------

@dataclass
class StatEntry:
    """A single equipment or armor stat (stats / max_stats arrays)."""
    stat_type: int
    value: float


@dataclass
class FoodStatEntry:
    """A food stat increase entry (food_stat array)."""
    increase: float
    stat: int


@dataclass
class StatBuffEntry:
    """A timed stat buff entry (stat_buff array)."""
    stat_type: int
    value: float
    duration: int


@dataclass
class CropStage:
    """A single crop growth stage (crop_stages array)."""
    days_to_grow: float
    guid: Optional[str] = None


@dataclass
class ItemClassification:
    """
    The result of classifying an item.
    Computed once by the builder and stored on ItemData so exporters
    never need to re-derive it.
    """
    item_type: str
    subtype: str
    category: str


# ---------------------------------------------------------------------------
# Primary data model
# ---------------------------------------------------------------------------

@dataclass
class ItemData:
    """
    Fully structured representation of a single Sun Haven item.

    Produced by the item builder from raw MonoBehaviour / GameObject files.
    Cached to JSON for reference and warm reloads.
    Consumed directly by exporters (wikitext) and wiki updaters (pywikibot).
    """

    # --- Identity ---
    asset_name: str
    name: str
    guid: str
    item_id: int
    icon_guid: Optional[str] = None

    # --- Descriptions ---
    description: str = ""
    use_description: str = ""
    help_description: str = ""

    # --- Economy ---
    stack_size: Optional[int] = None
    can_sell: bool = False
    sell_price: int = 0
    orbs_sell_price: int = 0
    ticket_sell_price: int = 0

    # --- Base Stats ---
    rarity: Optional[int] = None
    hearts: Optional[int] = None
    health: Optional[int] = None
    mana: Optional[int] = None
    exp: Optional[int] = None
    required_level: Optional[int] = None
    armor_set: Optional[int] = None
    decoration_type: Optional[int] = None

    # --- Boolean Flags ---
    is_dlc: bool = False
    is_forageable: bool = False
    is_gem: bool = False
    is_animal_product: bool = False
    is_meal: bool = False
    is_fruit: bool = False
    is_artisanry: bool = False
    is_potion: bool = False

    # --- Season Info ---
    has_set_season: Optional[int] = None
    set_season: Optional[int] = None
    seasons: Optional[str] = None

    # --- Complex Stats ---
    stats: list[StatEntry] = field(default_factory=list)
    max_stats: list[StatEntry] = field(default_factory=list)
    food_stat: list[FoodStatEntry] = field(default_factory=list)
    stat_buff: list[StatBuffEntry] = field(default_factory=list)
    crop_stages: list[CropStage] = field(default_factory=list)

    # --- Placement (extracted from prefab files) ---
    placeable_on_tables: bool = False
    placeable_on_walls: bool = False
    placeable_as_rug: bool = False
    placeable_in_water: bool = False
    pickaxeable: bool = False
    axeable: bool = False
    can_rotate: bool = False

    # --- Classification (computed at build time, stored for exporter use) ---
    classification: Optional[ItemClassification] = None
