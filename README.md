Collection of Parser Items for the Sun Haven wiki found at: https://sunhaven.wiki.gg/ <br>
Putting these into output files, so we can do a compare between patches, and only update pages that need it.

# File Structure
```
Sun Haven Parser/
├── _output/
├── _input/
│
├── analysis/
│   ├── compare_patch_item_descriptions.py
│   └── compare_patch_item_pages.py
│
├── config/
│   ├── constants.example.py
│   └── skip_items.py
│
├── utils/
│   ├── compre_utils.py       → Utility has functions around comparing wiki pages to the raw data.
│   ├── file_utils.py         → Utility pulls together functions around read/write with logs or structured text files.
│   ├── guid_utils.py         → Utility pulls together functions around guid extraction.
│   ├── json_utils.py         → Utility pulls together functions around JSON parsing.
│   ├── recipe_utils.py       → Utility pulls together functions around recipe formatting.
│   ├── text_utils.py         → Utility pulls together functions around general string clean up.
│   └── wiki_utils.py         → Utility has functions around pywikibot and getting items from the wiki.
│
├── pwb/                      → Pywikibot engine
│   ├── pwb.py
│   ├── pywikibot/            → Core library
│   ├── scripts/              → Required for login and maintenance commands
│   ├── families/
│   │   └── sunhaven_family.py
│   └── user-config.py        → Your wiki credentials
│
├── formatter/                    → Scripts in this directory will format data for wiki consumption.
│   ├── page_assembly
│   │   ├── create_item_page.py       → Uses item_infobox, item_recipe, item_summary, navbox scripts to build item pages.
│   │   └── create_quest_page.py
│   ├── page_section
│   │   ├── item_infobox.py           → Creates a formatted item infobox from the json data.
│   │   ├── item_recipe.py            → Creates a formatted recipe template from the json data.
│   │   ├── item_summary.py           → Creates a formatted summary from category data.
│   │   ├── navbox.py                 → Assigns a navbox type based on category data.
│   │   ├── quest_infobox.py          → Creates a formatted quest infobox from the json data.
│   │   ├── quest_sections.py         → Assigns certain quest page sections to different quest types.
│   │   └── quest_summary.py          → Creates a formatted summary from quest type data.
│   ├── all_dialogue.py           → Creates a directory of all dialgoue for all NPCs.
│   ├── all_item_descriptions.py  → Creates the format for `Module:Description`.
│   ├── all_monster_drops.py      → A list of all drops and % to drop item from monsters.
│   ├── all_npc_names.py          → A list of all NPCs that have speaking lines.
│   ├── all_recipes.py            → A list of all recipies, in the `Template:Recipie` format in one output.
│   ├── all_shops.py              → Formats all shop inventory sections.
│   ├── quest_infobox.py          → Creates a formatted quest infobox from the json data.
│   ├── quest_sections.py         → Assigns certain quest page sections to different quest types.
│   └── quest_summary.py          → Creates a formatted summary from quest type data.
│       
├── json_tools/                   → These scripts create json objects that most other scripts use to pull their data from.
│   ├── image_list.py             → Creates list of image file names and their GUID mapping. 
│   ├── item_list.py              → Creates list of item details from monobehaviour files. 
│   ├── quest_list.py             → Creates list of quest details.
│   ├── recipes_list.py           → Creates list of recipe details.
│   └── shop_inventory.py         → Creates list of shop inventory details.
|
├── pywikibot_tools/
│   ├── compare/
│   │   ├── compare_item_infobox.py                 → Compares wiki item infobox template to the items json, logs diffs.
│   │   ├── compare_recipe.py                       → Compares wiki recipe template to the recipe json, logs diffs.
│   ├── core/
│   │   ├── item_infobox_core.py                    → Core item infobox scripts for compare/update/create.
│   │   ├── recipe_core.py                          → Core recipe scripts for compare/update/create.
│   ├── create/
│   │   ├── missing_item_image.py                   → Uploads missing item images.
│   │   ├── missing_item_page.py                    → Creates missing item pages using `formatter/item_page/create_page.py`.
│   │   ├── upload_floor_wallpaper_display.py       → Uploads the display images of wallpaper and flooring. Removes the "missing" category.
│   │   ├── upload_house_customization_display.py   → Uploads the display images of door, window, wall, patios, and roof images of houseing customizations.
│   │   └── upload_mount_display.py                 → Merges and uploads mount display images.
│   ├── delete/
│   │   ├── deduplicate_house_parts.py              → Removes the duplicated house customization images. Sets up proper redirects.
│   |   └── unused_categories.py                    → Removes unused categories that meet a certain criteria.
│   ├── update/
│   │   ├── dlc_mount_image_categories.py           → Puts specific missing categories on mount image files.
│   │   ├── dlc_pet_image_categories.py             → Puts specific missing categories on pet image files.
│   │   ├── update_image_scale_whitespace.py        → Checks for small images, scales and crops them.
│   │   ├── update_item_infobox.py                  → Updates wiki item infobox template to match items json.
│   │   ├── update_recipe.py                        → Updates wiki recipe template to match recipe json.
│   |   └── update_uncategorized_files.py           → Categorizes files from Special:UncategorizedFiles to clean up file metadata.
│   ├── validators/
│   │   ├── missing_item_images.py                  → Compares items.json to the wiki to find missing item images.
│   │   ├── missing_item.py                         → Lists missing item pages based on the item json file.
│   │   ├── missing_quests.py                       → Lists missing quest pages based on the quest json files.
│   |   └── missing_recipe_template.py              → Lists pages missing the recipe template, based on the recipe json file.
│   ├── formatting_recipe_template.py               → Standardizes the recipe template, so the compare script can run.
│   └── redirect_creation.py                        → Creates redirect pages to specific base pages.
|
├── _run_for_new_patch.py               → Runs JSON and Formatter scripts in correct order for new patch.
├── pwb.ps1                             → Recommended launcher script for pywikibot stuff
├── .gitignore
└── README.md
```

# Using the Parser
## Getting the Assets
1. Download an application that allows you to look at the assets. I use [AssetRipper](https://github.com/AssetRipper/AssetRipper).
2. In the preferred asset manager, load the `Sun Haven_Data` folder. For most people it will be located in something like this:
  * Windows: `C:/Program Files (x86)/Steam/steamapps/common/Sun Haven/Sun Haven_Data`
  * Linux: `${HOME}/.steam/steam/steamapps/common/Sun Haven/Sun Haven_Data`
3. Export the folder to an area of your choosing. You will want to choose the export type: `Unity Project`. This is how it will export:
### Asset Directory Structure
```
Unity Project Export
└── ExportedProject
    ├── Assets
    │   ├── AssetBundle
    │   ├── AudioClip
    │   ├── AudioManager
    │   ├── BuildSettings
    │   ├── CustomRenderTexture
    │   ├── DelayedCallManager
    │   ├── EditorBuildSettings
    │   ├── EditorSettings
    │   ├── Font
    │   ├── GraphicsSettings
    │   ├── GameObject              # Entity information [Monster/NPC/Resource stats and drop info] 
    │   ├── InputManager
    │   ├── LightingSettings
    │   ├── Mesh
    │   ├── MonoBehaviour           # This is where the majority of the item data is.
    │   ├── MonoManager
    │   ├── NavMeshProjectSettings
    │   ├── Physics2DSettings
    │   ├── PhysicsManager
    │   ├── PhysicsMaterial2D
    │   ├── PlayerSettings
    │   ├── PrefabHierarchyObject
    │   ├── QualitySettings
    │   ├── RenderTexture
    │   ├── ResourceManager
    │   ├── Resources
    │   ├── RuntimeInitializeOnLoadManager
    │   ├── SceneHierarchyObject
    │   ├── Shader
    │   ├── ShaderNameRegistry
    │   ├── Sprite                  # This is where the png filename and GUID information is.
    │   ├── SpriteAtlas
    │   ├── StreamingManager
    │   ├── SunHaven
    │   │     └── Scenes            # This is fishing chance data        
    │   ├── TagManager
    │   ├── TextAsset               # This is where the files for the conversations and dialogues are.
    │   ├── Texture2D               # This is where many of the images are.
    │   ├── TimeManager
    │   ├── UnityConnectSettings    
    │   ├── VFXManager
    │   ├──────────────
    │   ├── English.PREFAB          # This holds the actual in-game names of items, along with dialogue
    │   ├── English.prefab.META     # This is required for mapping purposes
    │   └── A Bunch of other .asset and .meta files    
    ├── Assembilies
    └── Scripts
```
4. After that export is done, export the same package as export type: `Primary Content`. This is how we will get the scripts for the cutscene dialogue, allowing us to know who is talking. <br>
You will take the scripts folder IN THIS FORMAT (not the scripts folder of the other format) and put it into the input folder of the parser.
```
Primary Content Export
├── Assemblies
├── Assets
└── Scripts
    └── A Bunch of file folders that hold cutscene.cs files
```

## Using the collection of scripts
4. Rename & update `constants.example.py` where applicable for your paths.
5. Take the necessary file folders from the ripped project and drop them into the parser project input folder.
6. Run all of the JSON scripts first, to generate objects that the rest of the scripts will use to pull their data from. Then run all of the formatter scripts.
  * I recommend comparing the most recent pull of data to the previous pull of data using a comparison application like WinMerge.

## Using Pywikibot
Some scripts in this project use the mediawiki api [Pywikibot](https://support.wiki.gg/wiki/Pywikibot) to perform wiki operations such as page creation, comparison, or image uploads. This project includes a full, vendored version of Pywikibot inside the pwb/ folder. There’s no need to install it separately or use it as a submodule.

    💡 All Pywikibot commands should be run through the included pwb.ps1 launcher to ensure the correct environment is used.

### First Time Setup
1. Copy the provided `pwb/user-config.py.sample` to `pwb/user-config.py` and `pwb/user-password.py.sample` to `pwb/user-password.py`
2. Open `pwb/user-config.py` and change the username.
3. Update user-password.py is created in the same folder and contains your login credentials.