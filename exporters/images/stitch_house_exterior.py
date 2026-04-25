"""
Stitches individual house part images (patio, walls, door, windows, roof) into a
single composite image per style per tier, saved locally for review or wiki upload.

Layer order (bottom to top): Patio → Wall → Door → Window → Roof
- Patio has 1 tier only.
- Wall, Door, Window, Roof each have 3 tiers (index 0–2).

Alignment:
- Canvas height = patio_h + wall_h + roof_h (stacking, keeps scale consistent).
- All parts centered horizontally.
- Patio: bottom of canvas.
- Wall: bottom descends WALL_DESCENT px below patio top (wall overlaps into patio).
- Roof: bottom is ROOF_WALL_OVERLAP px below wall top (eaves hang into wall area).
- Door: bottom at wall bottom, optionally shifted horizontally by DOOR_X_SHIFT.
- Window: top at WINDOW_BELOW_WALL_TOP px below wall top.

Tune the four constants below if a run looks off for a particular style.

Usage:
    python stitch_house_exterior.py                  # all styles, all tiers
    python stitch_house_exterior.py "Log Cabin"      # one style, all tiers
    python stitch_house_exterior.py "Log Cabin" 2    # one style, one tier
    python stitch_house_exterior.py "Log Cabin" 2 --debug
"""

import os
import re
import sys
import argparse

from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils import file_utils, image_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image_input_directory = constants.IMAGE_INPUT_DIRECTORY
output_directory      = os.path.join(constants.OUTPUT_DIRECTORY, "House Exteriors")
file_utils.ensure_dir_exists(output_directory)

# ---------------------------------------------------------------------------
# House configuration
# ---------------------------------------------------------------------------

# Bottom-to-top compositing order
LAYER_ORDER = ["Patio", "Wall", "Door", "Window", "Roof"]

TIER_COUNTS = {
    "Patio":  1,
    "Wall":   3,
    "Door":   3,
    "Window": 3,
    "Roof":   3,
}

# Plural file-name variants used by some exports
PLURAL_MAP = {
    "wall":   "walls",
    "window": "windows",
}

# ---------------------------------------------------------------------------
# Layout constants  (all values in original, pre-scale canvas pixels)
# ---------------------------------------------------------------------------

# How far the wall bottom descends below patio top — the wall overlaps INTO the patio.
# Increase to move wall (and everything anchored to it) further down.
WALL_DESCENT = 84

# How far the roof bottom hangs below the wall top — the eaves overlap into the wall.
# Increase to pull the roof further down over the wall.
ROOF_WALL_OVERLAP = 50

# Per-tier window and door offsets.
# Each tier's wall sprite has its openings at different positions, so these
# are tuned individually.  Keys are 1-indexed tier numbers.
#
#   window_below_wall_top  – window top, in px below wall top (negative = above wall top)
#   window_x_shift         – horizontal nudge for window (positive = right)
#   door_x_shift           – horizontal nudge for door (positive = right)
TIER_LAYOUT = {
    #                                                              door_y_shift: positive = down, negative = up
    1: {"window_below_wall_top":  11, "window_x_shift":  0, "door_x_shift":   0, "door_y_shift":  0},
    2: {"window_below_wall_top":  30, "window_x_shift": -2, "door_x_shift":  25, "door_y_shift":  0},
    3: {"window_below_wall_top": -14, "window_x_shift": -1, "door_x_shift":   1, "door_y_shift":  0},
}

# ---------------------------------------------------------------------------
ALL_HOUSE_STYLES = [
    "Bamboo", "Basic", "Blue Polka Dot", "Blue Striped",
    "Blue Tiled", "Brown Cobblestone", "Brown Stone",
    "Cardboard", "Castle", "Cat", "Charming",
    "Classic Brick", "Cottage Core", "Cow Print",
    "Deep Sea", "Eastern", "Fall", "Gingerbread",
    "Great City", "Green Plank", "Green Polka Dot",
    "Green Striped", "Greenhouse", "Honeycomb",
    "Ice", "Log Cabin", "Mini Blue Polka Dot",
    "Mini Green Polka Dot", "Mini Purple Polka Dot",
    "Mini Red Polka Dot", "Mini Yellow Polka Dot",
    "Monster Mouth", "Nature", "Neon", "Old Stone",
    "Orange Tiled", "Purple Polka Dot",
    "Purple Ruffled", "Purple Striped", "Red",
    "Red Polka Dot", "Red Prism", "Red Striped",
    "Rickity", "Robotic", "Simple Blue",
    "Simple Green", "Simple Purple", "Simple Red",
    "Simple Yellow", "Slime Drop", "Slimey",
    "Spring", "Steel", "Stone", "Stone Brick",
    "Straw", "Stucco", "Summer", "Terracotta",
    "Terracotta Shackle", "Winter", "Withergate",
    "Yellow", "Yellow Polka Dot", "Yellow Striped",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_name(name):
    """Strip non-alphanumeric characters and lowercase for fuzzy file matching."""
    return re.sub(r'[^a-z0-9]', '', name.lower())


def _search_candidates(candidates, files):
    """
    Return the filename (not full path) of the first candidate that matches any
    file in `files`, using exact-stem or prefix+trailing-digits matching.
    Returns None if no match is found.
    """
    for candidate in candidates:
        norm_stem = normalize_name(os.path.splitext(candidate)[0])
        for filename in files:
            norm_filename_stem = normalize_name(os.path.splitext(filename)[0])
            # Exact stem match
            if norm_filename_stem == norm_stem:
                return filename
            # Prefix match: filename has extra trailing digits after the candidate stem
            # e.g. "spring_roof_tier_2_0" matches candidate "spring_roof_tier_2"
            if norm_filename_stem.startswith(norm_stem):
                suffix = norm_filename_stem[len(norm_stem):]
                if suffix.isdigit():
                    return filename
    return None


def find_part_image(style, part_type, index):
    """
    Locate the PNG image file for a single house part.

    Args:
        style:     House style name, e.g. "Log Cabin".
        part_type: One of the LAYER_ORDER values, e.g. "Wall".
        index:     0-based tier index (Patio always uses 0).

    Returns:
        Absolute file path if found, otherwise None.
    """
    type_lc = part_type.lower()
    candidates          = []
    fallback_candidates = []

    if type_lc == "patio":
        candidates = [
            f"{style}_patio.png",
            f"{style}_house_patio.png",
        ]
    else:
        type_variants = [type_lc]
        if type_lc in PLURAL_MAP:
            type_variants.append(PLURAL_MAP[type_lc])
        for variant in type_variants:
            candidates.append(f"{style}_{variant}_{index}.png")
            candidates.append(f"{style}_{variant}_tier_{index + 1}.png")

        # Fallback for walls: some styles index tiers by their 1-based number rather
        # than 0-based index (e.g. Greenhouse uses _0, _1, _3 for tiers 1, 2, 3).
        if type_lc == "wall":
            for variant in type_variants:
                fallback_candidates.append(f"{style}_{variant}_{index + 1}.png")

    files  = os.listdir(image_input_directory)
    result = _search_candidates(candidates, files)

    if result is None and fallback_candidates:
        result = _search_candidates(fallback_candidates, files)

    return os.path.join(image_input_directory, result) if result else None


def build_output_filename(style, tier):
    """Return the output PNG filename for a composited house image."""
    return f"{style} House Tier {tier}.png"


# ---------------------------------------------------------------------------
# Core compositing
# ---------------------------------------------------------------------------

def composite_house_exterior(style, tier, debug=False):
    """
    Load and composite all house parts for the given style and tier.

    Canvas height = patio_h + wall_h + roof_h so the scale factor stays
    consistent across runs.  Parts are positioned using the layout constants
    at the top of this file:

        patio   → bottom of canvas
        wall    → bottom = patio_top + WALL_DESCENT  (overlaps into patio)
        roof    → bottom = wall_top  + ROOF_WALL_OVERLAP  (eaves hang over wall)
        door    → bottom = wall_bottom, x shifted by DOOR_X_SHIFT
        window  → top    = wall_top   + WINDOW_BELOW_WALL_TOP

    Args:
        style: House style name.
        tier:  1-indexed tier (1, 2, or 3).
        debug: If True, print image sizes and computed positions for each part.

    Returns:
        Composited RGBA PIL Image, or None if no layers could be loaded.
    """
    index = tier - 1  # convert to 0-based for file lookup
    parts = {}        # part_type → PIL Image

    for part_type in LAYER_ORDER:
        part_index = 0 if part_type == "Patio" else index
        filepath = find_part_image(style, part_type, part_index)

        if filepath is None:
            print(f"    ⚠ Missing {part_type} (tier {tier}): {style}")
            continue

        try:
            img = Image.open(filepath).convert("RGBA")
            parts[part_type] = img
        except Exception as e:
            print(f"    ✗ Could not open {part_type} for {style}: {e}")

    if not parts:
        return None

    wall_h  = parts["Wall"].height  if "Wall"  in parts else 0
    roof_h  = parts["Roof"].height  if "Roof"  in parts else 0
    patio_h = parts["Patio"].height if "Patio" in parts else 0

    # Per-tier offsets (fall back to tier 2 values if tier not in table)
    layout = TIER_LAYOUT.get(tier, TIER_LAYOUT[2])
    window_below_wall_top = layout["window_below_wall_top"]
    window_x_shift        = layout["window_x_shift"]
    door_x_shift          = layout["door_x_shift"]
    door_y_shift          = layout["door_y_shift"]

    # Canvas: stacking order gives consistent total height and scale factor
    canvas_width  = max(img.width for img in parts.values())
    canvas_height = patio_h + wall_h + roof_h

    # Vertical reference points (PIL: y=0 is top, increases downward)
    cx = canvas_width // 2

    if "Patio" in parts:
        patio_top_y = canvas_height - patio_h      # top edge of patio band
        wall_bottom = patio_top_y + WALL_DESCENT   # wall descends into patio
    else:
        # No patio exported for this style — anchor wall flush at the canvas bottom.
        patio_top_y = canvas_height
        wall_bottom = canvas_height

    wall_top = wall_bottom - wall_h

    if debug:
        patio_note = "" if "Patio" in parts else " (no patio — wall anchored at bottom)"
        print(f"    Canvas: {canvas_width}x{canvas_height}  cx={cx}")
        print(f"    patio_top={patio_top_y}  wall_top={wall_top}  "
              f"wall_bottom={wall_bottom}  ground={canvas_height}{patio_note}")
        print(f"    {'Part':<10} {'ImgSize':<14} {'PlaceAt (x,y)'}")
        print(f"    {'-'*10} {'-'*14} {'-'*16}")

    canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))

    for part_type in LAYER_ORDER:
        img = parts.get(part_type)
        if img is None:
            continue

        x = cx - img.width // 2  # default: center horizontally

        if part_type == "Patio":
            y = canvas_height - img.height

        elif part_type == "Wall":
            y = wall_top

        elif part_type == "Roof":
            # Roof eaves hang ROOF_WALL_OVERLAP px below the wall top
            roof_bottom = wall_top + ROOF_WALL_OVERLAP
            y = roof_bottom - img.height

        elif part_type == "Door":
            y = wall_bottom - img.height + door_y_shift
            x = cx - img.width // 2 + door_x_shift

        elif part_type == "Window":
            y = wall_top + window_below_wall_top
            x = cx - img.width // 2 + window_x_shift

        else:
            y = canvas_height - img.height

        if debug:
            print(f"    {part_type:<10} {img.width}x{img.height:<10} ({x},{y})")

        temp = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        temp.alpha_composite(img, dest=(x, y))
        canvas = Image.alpha_composite(canvas, temp)

    return canvas


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

def process_style(style, tier=None, debug=False, no_scale=False):
    """
    Composite and save house exterior images for one style.

    Args:
        style:    House style name.
        tier:     Specific tier (1–3), or None to process all three tiers.
        debug:    If True, print image sizes and computed positions for each part.
        no_scale: If True, skip upscaling so the saved PNG is 1:1 with the canvas.
                  Use this when calibrating constants — pixel measurements in the
                  saved image will then match the constant values directly.
    """
    tiers = [tier] if tier is not None else range(1, 4)

    for t in tiers:
        result = composite_house_exterior(style, t, debug=debug)
        if result is None:
            print(f"    ✗ Skipped tier {t} — no layers found.")
            continue

        result = image_utils.crop_whitespace(result)
        if not no_scale:
            result = image_utils.scale_image_to_min_size(result, 500)

        output_filename = build_output_filename(style, t)
        output_path = os.path.join(output_directory, output_filename)
        result.save(output_path)
        print(f"    ✓ Saved: {output_filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Stitch house exterior parts into a single composite image."
    )
    parser.add_argument(
        "style",
        nargs="?",
        help="House style name (e.g. 'Log Cabin'). Omit to process all styles.",
    )
    parser.add_argument(
        "tier",
        nargs="?",
        type=int,
        choices=[1, 2, 3],
        help="Tier number (1–3). Omit to process all tiers.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print image sizes and computed canvas positions for each part.",
    )
    parser.add_argument(
        "--no-scale",
        action="store_true",
        help="Skip upscaling — saves at raw canvas size (1:1) for calibration.",
    )
    args = parser.parse_args()

    if args.style:
        print(f"🏠 {args.style}")
        process_style(args.style, args.tier, debug=args.debug, no_scale=args.no_scale)
    else:
        total = len(ALL_HOUSE_STYLES)
        for idx, style in enumerate(ALL_HOUSE_STYLES, 1):
            print(f"🏠 [{idx}/{total}] {style}")
            process_style(style, debug=args.debug, no_scale=args.no_scale)

    print(f"\n✅ Done. Output saved to: {output_directory}")


if __name__ == "__main__":
    main()
