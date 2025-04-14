Collection of Parser Items for the Sun Haven wiki found at: https://sunhaven.wiki.gg/ <br>
Putting these into output files, so we can do a compare between patches, and only update pages that need it.

Some scripts to do some comparisons using the mediawiki api [Pywikibot](https://support.wiki.gg/wiki/Pywikibot) to do various comparisons, page creations, or uploads directly into the wiki.<br>
The user must be in the PWB-Core folder and logged in to PyWikiBot using: python pwb.py login<br>

# Parser Collection
```
Sun Haven Parser/
├── _output/
├── _input/
│
├── config/
│   ├── constants.example.py
│   └── skip_items.py
│
├── utils/
│   ├── file_utils.py     → Utility pulls together functions around read/write with logs or structured text files.
│   ├── guid_utils.py     → Utility pulls together functions around guid extraction.
│   ├── json_utils.py     → Utility pulls together functions around JSON parsing.
│   ├── recipe_utils.py   → Utility pulls together functions around recipe formatting.
│   └── text_utils.py     → Utility pulls together functions around general string clean up.
│
├── formatter/            → Scripts in this directory will format data for wiki consumption.
│   ├── item_page/        → Creates item pages, in their entirety. 
│   │   ├── create_page.py
│   │   ├── infobox_classifications.py
│   │   ├── infobox_item_data.py
│   │   ├── infobox.py
│   │   ├── navbox.py
│   │   ├── recipe.py
│   │   └── summary.py
│   ├── quest_page/           → Creates quest pages, some minor manual formatting will need to be done after. 
│   |   ├── create_page.py
│   |   ├── infobox.py
│   |   └── layout.py        
│   ├── all_recipes.py        → A list of all recipies, formatted in the `Template:Recipie` format. 
│   ├── dialogue.py           → All dialogue; Cycles, One Liners, etc. 
│   ├── item_descriptions.py  → Creates the format for `Module:Description`
│   ├── quests.py             → Formats quest infoboxes [may be able to depreciate with the updates above.]
│   └── shops.py              → Formats shop inventory sections.
│       
├── json_tools/               → These scripts create json objects that most other scripts use to pull their data from.
│   ├── image_list.py         → Creates list of image file names and their GUID mapping. 
│   ├── item_list.py          → Creates list of item details from monobehaviour files. 
│   ├── quest_details.py      → Creates list of quest details.
│   ├── recipes_list.py       → Creates list of recipe details.
│   └── shop_inventory.py     → Creates list of shop inventory details.
|
├── pywikibot_tools/
│   ├── create/
│   │   ├── missing_item_image.py       → Uploads missing item images.
│   │   ├── missing_item_page.py        → Creates missing item pages using `formatter/item_page/create_page.py`.
│   ├── validators/
│   │   ├── missing_item_images.py      → Compares items.json to the wiki to find missing item images.
│   │   ├── missing_item.py             → Lists missing item pages based on the item json file.
│   │   ├── missing_quests.py           → Lists missing quest pages based on the quest json files.
│   |   └── missing_recipe_template.py  → Lists pages missing the recipe template, based on the recipe json file.
│   ├── compare_recipe.py     → (WIP) Compares the `{{recipe}}` page data, to the recipe json data to find recipes that need to be updated.
│   ├── formatting_recipe_template.py   → Standardizes the recipe template, so the compare script can run.
│   ├── images_dlc_pet.py               → Puts specific categories on pet image files.
│   ├── images_dlc_mount.py             → Puts specific categories on mount image files.
│   ├── images_dlc_mount_display.py     → (WIP) 
│   └── redirect_creation.py            → Creates redirect pages to specific base pages.
|
├── _run_for_new_patch.py               → Runs JSON and Formatter scripts in correct order for new patch.
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
    │   ├── TagManager
    │   ├── TextAsset               # This is where the files for the conversations and dialogues are.
    │   ├── Texture2D               # This is where many of the images are.
    │   ├── TimeManager
    │   ├── UnityConnectSettings    
    │   ├── VFXManager
    │   ├────── 
    │   └── A Bunch of other .asset and .meta files    
    ├── Assembilies
    └── Scripts
```
## Using the collection of scripts
4. Rename & update `constants.example.py` where applicable for your paths.
5. Take the necessary file folders from the ripped project and drop them into the parser project input folder.
6. Run all of the JSON scripts first, to generate objects that the rest of the scripts will use to pull their data from. Then run all of the formatter scripts.
  * I recommend comparing the most recent pull of data to the previous pull of data using a comparison application like WinMerge.