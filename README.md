Collection of Parser scripts for the Sun Haven wiki found at: https://sunhaven.wiki.gg/ <br>
Reads raw game asset files, produces structured JSON caches, formats them into wiki-ready output, and uses Pywikibot to compare and update live wiki pages.

# Pipeline Overview

The project runs as a four-layer pipeline:

```
builders/  →  formatters/  →  exporters/  →  wiki/
  (JSON)       (wikitext)      (txt files)   (pywikibot)
```

1. **builders/** — Parse raw game asset files and write structured JSON caches.
2. **formatters/** — Pure functions that convert structured data into wikitext strings. No file I/O.
3. **exporters/** — Read JSON caches, call formatters, and write `.txt` output files grouped for wiki use.
4. **wiki/** — Pywikibot scripts that compare/update/create live wiki pages using the exporter output and JSON caches.

Run `_run_for_new_patch.py` to execute builders and exporters in the correct order.

---

# File Structure

```
Sun Haven Parser/
│
├── _run_for_new_patch.py         → Runs builders and exporters in the correct order for a new patch.
│
├── builders/                     → Layer 1: Parse raw game files → structured JSON caches.
│   ├── item_data.py              → ItemData dataclass and sub-dataclasses (StatEntry, ItemClassification, etc.)
│   ├── item_builder.py           → Parses MonoBehaviour item files → items_data.json
│   ├── recipe_builder.py         → Parses RecipeList asset files → recipes_data.json
│   ├── shop_builder.py           → Parses shop inventory assets → shops_data.json
│   ├── npc_dialogue_builder.py   → Parses NPC dialogue files → npc_dialogue_data.json
│   ├── quest_builder.py          → Parses quest assets → quests_data.json
│   ├── entity_builder.py         → Parses enemy/entity data from Scenes → entities_data.json
│   ├── fish_spawner_builder.py   → Parses fish spawn data from Scenes → fish_spawner_data.json
│   ├── image_builder.py          → Maps Sprite GUIDs to image filenames → images_data.json
│   ├── breakable_object_builder.py → Parses breakable object data
│   └── cutscene_builder.py       → Parses cutscene .cs script files → cutscenes_data.json
│
├── formatters/                   → Layer 2: Pure wikitext generators (no file I/O).
│   ├── item/
│   │   ├── item_infobox.py       → Generates item infobox wikitext from ItemData.
│   │   ├── item_recipe.py        → Generates {{Recipe}} wikitext; owns format_recipe() and normalize_workbench().
│   │   ├── item_summary.py       → Generates item summary section.
│   │   └── item_navbox.py        → Selects the correct navbox template for an item.
│   ├── quest/
│   │   ├── quest_infobox.py      → Generates quest infobox wikitext.
│   │   ├── quest_sections.py     → Generates quest page section blocks.
│   │   ├── quest_summary.py      → Generates quest summary section.
│   │   └── quest_context.py      → Extracts a normalised context dict from a raw quest record.
│   └── pages/
│       ├── item_page.py          → Assembles a complete item wiki page.
│       ├── npc_page.py           → Assembles a complete NPC wiki page.
│       └── quest_page.py         → Assembles a complete quest wiki page.
│
├── exporters/                    → Layer 3: Read JSON caches, call formatters, write output .txt files.
│   ├── images/
│   │   ├── item_infobox.py       → Composites individual house part sprites into a single exterior image per style per tier.
│   ├── all_item_descriptions.py  → Writes Module:Description formatted output.
│   ├── all_recipes.py            → Writes all {{Recipe}} templates grouped alphabetically.
│   ├── all_shops.py              → Writes all shop inventory sections.
│   ├── all_monster_drops.py      → Writes all monster drop tables.
│   ├── all_enemy_infoboxes.py    → Writes all enemy infobox templates.
│   ├── all_cutscenes.py          → Writes all cutscene dialogue.
│   ├── all_dialogue.py           → Writes all NPC one-liner dialogue files.
│   ├── all_npc_names.py          → Writes the unique NPC names list for patch comparison.
│   ├── npc_dialogue.py           → Writes per-NPC one-liner files.
│   ├── npc_cycles.py             → Writes per-NPC conversation cycle files.
│   ├── npc_walk_schedule.py      → Writes per-NPC schedule files.
│   ├── npc_romance_dialogue_unique_gifts.py
│   ├── npc_romance_gift_preferences.py
│   ├── npc_wedding_cutscene.py
│   ├── fish_spawn_chance.py      → Writes fish spawn chance tables.
│   ├── create_item_pages.py      → Assembles and writes full item page text files.
│   ├── create_npc_pages.py       → Assembles and writes full NPC page text files.
│   └── create_quest_pages.py     → Assembles and writes full quest page text files.
│
├── mappings/                     → Reference data only. Update these when new game content is added.
│   ├── item_classification.py    → Classification rules (item type / subtype / category). Update for new item types.
│   ├── location_mapping.py       → LOCATION_LINKS and PERSONAL_TERMS dicts. Update for new locations / NPCs.
│   └── workbench_aliases.py      → WORKBENCH_ALIASES dict + normalize_workbench(). Update for new workbenches.
│
├── wiki/                         → Layer 4: Pywikibot scripts for live wiki operations.
│   ├── shared/
│   │   ├── item_infobox_core.py  → Shared logic for item infobox compare/update/create operations.
│   │   └── recipe_core.py        → Shared logic for recipe compare/update/create operations.
│   ├── compare/
│   │   ├── compare_item_infobox.py → Compares live wiki item infoboxes against items_data.json; logs diffs.
│   │   ├── compare_recipe.py       → Compares live wiki Recipe templates against recipes_data.json; logs diffs.
│   │   ├── infobox_fields.py       → FIELD_MAP and FIELD_COMPUTATIONS tables used by compare/update tools.
│   │   └── recipe_fields.py        → RECIPE_FIELD_MAP, RECIPE_COMPUTE_MAP, RECIPE_EXTRA_FIELDS tables.
│   ├── create/
│   │   ├── missing_item_page.py    → Creates missing item pages from the item builder cache.
│   │   ├── missing_npc_page.py     → Creates missing NPC pages and uploads associated NPC images.
│   │   ├── missing_item_image.py   → Uploads missing item images.
│   │   ├── upload_floor_wallpaper_display.py
│   │   ├── upload_house_customization_display.py
│   │   ├── upload_house_exteriors.py    → Uploads composited house exterior images to the wiki
│   │   ├── upload_mount_display.py
│   │   └── upload_wanted_item_images.py
│   ├── update/
│   │   ├── update_item_infobox.py       → Updates live wiki item infoboxes to match items_data.json.
│   │   ├── update_recipe.py             → Updates live wiki Recipe templates to match recipes_data.json.
│   │   ├── top_shelf_rare_finds.py      → Updates topShelf / rareFinds flags on item pages.
│   │   ├── dlc_mount_image_categories.py
│   │   ├── dlc_pet_image_categories.py
│   │   ├── update_house_part_pages.py   → Updates house customisation wiki pages with a full-set media gallery.
│   │   ├── update_image_scale_whitespace.py
│   │   └── update_rnpc_bust_filenames.py
│   ├── delete/
│   │   ├── deduplicate_house_parts.py   → Removes duplicate house customization images; creates redirects.
│   │   └── unused_categories.py         → Removes unused categories matching a set of criteria.
│   ├── validators/
│   │   ├── missing_item.py              → Lists item pages missing from the wiki based on items_data.json.
│   │   ├── missing_item_images.py       → Lists item images missing from the wiki.
│   │   ├── missing_quests.py            → Lists quest pages missing from the wiki.
│   │   └── missing_recipe_template.py   → Lists pages missing a {{Recipe}} template.
│   ├── formatting_recipe_template.py    → Standardises Recipe template formatting before compare runs.
│   ├── nulledit.py                      → Performs null edits to refresh cached page data.
│   └── redirect_creation.py             → Creates redirect pages to specific base pages.
│
├── config/
│   ├── constants.example.py      → Template — copy to constants.py and fill in your local paths.
│   └── skip_items.py             → Items and patterns to exclude from wiki operations.
│
├── utils/
│   ├── compare_utils.py          → Generic field-level diff logic for wiki compare tools.
│   ├── file_utils.py             → Read/write helpers for structured text files and debug logs.
│   ├── guid_utils.py             → GUID extraction and lookup helpers.
│   ├── history_utils.py          → Generates {{History}} template entries.
│   ├── image_utils.py            → Image processing helpers (scale, crop, etc.).
│   ├── json_utils.py             → JSON load/write wrappers.
│   ├── recipe_utils.py           → Recipe formatting and time-parsing helpers.
│   ├── text_utils.py             → General string clean-up (apostrophe normalisation, whitespace, etc.).
│   └── wiki_utils.py             → Pywikibot helpers (page fetch, template parsing, etc.).
│
├── analysis/                     → One-off comparison scripts for patch-to-patch diffs.
│   ├── compare_patch_item_descriptions.py
│   ├── compare_patch_item_pages.py
│   ├── compare_patch_bb_quests.py
│   ├── compare_patch_npc_names.py
│   └── compare_builder_output.py
│
├── pwb/                          → Vendored Pywikibot engine (no separate install needed).
│   ├── pwb.py
│   ├── pywikibot/                → Core Pywikibot library.
│   ├── scripts/                  → Required for login and maintenance commands.
│   ├── families/
│   │   └── sunhaven_family.py
│   └── user-config.py            → Your wiki credentials (not committed).
│
├── pwb.ps1                       → Recommended launcher for all Pywikibot commands.
├── .gitignore
└── README.md
```

---

# Using the Parser

## Getting the Assets
1. Download an application that allows you to look at the assets. I use [AssetRipper](https://github.com/AssetRipper/AssetRipper).
2. In the preferred asset manager, load the `Sun Haven_Data` folder. For most people it will be located in something like this:
   * Windows: `C:/Program Files (x86)/Steam/steamapps/common/Sun Haven/Sun Haven_Data`
   * Linux: `${HOME}/.steam/steam/steamapps/common/Sun Haven/Sun Haven_Data`
3. Export the folder to an area of your choosing. Choose export type: `Unity Project`. This is the structure you will get:

### Asset Directory Structure
```
Unity Project Export
└── ExportedProject
    ├── Assets
    │   ├── GameObject              # Entity information [Monster/NPC/Resource stats and drop info]
    │   ├── MonoBehaviour           # The majority of item, recipe, shop, and quest data.
    │   ├── Sprite                  # PNG filenames and GUID mappings.
    │   ├── SunHaven
    │   │     └── Scenes            # Fishing spawn data and entity/enemy data.
    │   ├── TextAsset               # Conversation and dialogue files.
    │   ├── Texture2D               # Image files.
    │   ├── English.PREFAB          # In-game item names and dialogue strings.
    │   └── English.prefab.META     # Required for GUID mapping.
    ├── Assemblies
    └── Scripts
```

4. Export the same package a second time as export type: `Primary Content`. This provides the C# script files used to parse cutscene dialogue. Take the `Scripts/` folder from this export and place it in the parser's input folder.

```
Primary Content Export
├── Assemblies
├── Assets
└── Scripts
    └── (cutscene .cs files)
```

## Running the Parser
5. Copy `config/constants.example.py` to `config/constants.py` and fill in your local paths.
6. Drop the required asset folders into the parser's input directory.
7. Run `_run_for_new_patch.py` to execute all builders then all exporters in the correct order. Output files land in the directory configured in `constants.py`.
   * Use a diff tool like WinMerge to compare the new output against the previous patch's output to identify what changed.

## Using Pywikibot
Scripts in `wiki/` use the MediaWiki API via [Pywikibot](https://support.wiki.gg/wiki/Pywikibot) to perform wiki operations such as page creation, comparison, and image uploads. A full vendored copy of Pywikibot is included in `pwb/` — no separate install needed.

    💡 All Pywikibot commands should be run through the included pwb.ps1 launcher to ensure the correct environment is used.

### First Time Setup
1. Copy `pwb/user-config.py.sample` to `pwb/user-config.py` and `pwb/user-password.py.sample` to `pwb/user-password.py`.
2. Open `pwb/user-config.py` and set your wiki username.
3. Add your login credentials to `pwb/user-password.py`.
