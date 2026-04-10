"""
Image builder — Layer 1 of the pipeline.

Reads .meta files from the Sprite directory and builds a GUID → image
filename lookup, writing images_data.json.

Usage:
    python builders/image_builder.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
from utils import file_utils, json_utils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SPRITE_DIR = os.path.join(constants.INPUT_DIRECTORY, "Sprite")
_CACHE_FILE = os.path.join(constants.OUTPUT_DIRECTORY, "JSON Data", "images_data.json")

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> None:
    file_utils.ensure_dir_exists(os.path.dirname(_CACHE_FILE))

    meta_files  = [f for f in os.listdir(_SPRITE_DIR) if f.endswith(".meta")]
    total       = len(meta_files)
    step        = max(1, total // 10)
    output_data = {}

    for index, filename in enumerate(meta_files, start=1):
        file_path = os.path.join(_SPRITE_DIR, filename)

        try:
            guid = None
            for line in file_utils.read_file_lines(file_path):
                if line.strip().startswith("guid:"):
                    guid = line.strip().split("guid:")[1].strip()
                    break
        except Exception as exc:
            print(f"  ⚠️  Error reading {filename}: {exc}")
            continue

        if guid:
            base_name = filename.replace(".asset.meta", "")
            output_data[guid] = {
                "file":  base_name,
                "image": f"{base_name}.png",
            }

        if index % step == 0:
            print(f"  🔄 {int((index / total) * 100)}% complete...")

    json_utils.write_json(output_data, _CACHE_FILE, indent=4)
    print(f"✅ {len(output_data)} images written to {_CACHE_FILE}")


if __name__ == "__main__":
    run()
