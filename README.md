Collection of Parser Items for the Sun Haven wiki found at: https://sunhaven.wiki.gg/ <br>
Putting these into output files, so we can do a compare between patches, and only update pages that need it.
Some scripts to do some comparisons using pywikibot

# Parser Collections
config/
├── constants.py     → Mapping for numeric to text conversions of things like stats, seasons, quest types, etc.
├── skip_list.py     → List of assets that aren't real items.

utils/
├── file_utils.py     → Utility pulls together functions around read/write with logs or structured text files.
├── guid_utils.py     → Utility pulls together functions around guid extraction.
├── json_utils.py     → Utility pulls together functions around JSON parsing.
└── text_utils.py     → Utility pulls together functions around general string clean up.


## JSON Objects
JSON_item_list.py --<br>
Creates a massive json object based on monobehaviour files located in the input directory. This will pull various information of each item, many of the fields in various infoboxes will use these numbers.<br>

JSON_image_list.py --<br>
Creates a massive json object based on sprite files located in the input directory. This will pull the image name and associated GUID.<br>

JSON_quest_details.py --<br>
Creates a json object based on quest specific monobehaviour files located in the input directory. This will pull various information of each quest, many of the fields in various infoboxes will use these numbers.<br>

JSON_recipes_list.py --<br>
Creates a json object based on recipes for items.<br>

JSON_shop_inventory.py --<br>
Cretes a json object for the inventory of various shops.<br>

## Formatted for Wiki Consumption
Each of these will take the information from the JSON objects, or the asset files in the monobehaviour directory to build text files that have the wiki formatting already in them, so people can copy and paste directly into the wiki and worry less about formatting.<br>
```
├── formatter_dialogue.py 
├── formatter_item_descriptions.py 
├── formatter_quests.py 
├── formatter_recipes.py 
├── formatter_shops.py 
├── formatter_item_page.py
    ├── formatter_item_page_infobox.py 
    │   ├── formatter_item_page_infobox_classifications.py
    |   └── formatter_item_page_infobox_item_data.py
    ├── formatter_item_page_summary.py.py
    └── formatter_item_page_navbox.py

 ```   

## PyWikiBot
These scripts use the mediawiki api [Pywikibot](https://support.wiki.gg/wiki/Pywikibot) to do various comparisons, page creations, or uploads directly into the wiki.<br>
The user must be in the PWB-Core folder and logged in to PyWikiBot using: python pwb.py login<br>

pywikibot_compare_recipe.py -- (WIP) <br>
This python script will compare the `{{recipe}}` template on a page, to the recipe json to find recipes that need to be updated.

pywikibot_missing_item_check.py --<br>
This python module will review the SH wiki to make three lists: Items missing from the JSON file, Items missing from the wiki, Items in both the JSON and the wiki.<br>
It will then do a comparison between items in both the JSON and Wiki, to see what infobox items need to be updated (WIP).

pywikibot_missing_image_check.py --<br>
Reviews the wiki and looks for itemname.png, anything missing itemname.png it puts in a list. The script then looks up the icon GUID to produce the image name. The overall output is a file that has missing images, and what their associated image name in the texture2D file is.

pywikibot_missing_quest_check.py --<br>
Reviews the wiki and compares against the quest json to create a list of missing quests.

pywikibot_create_missing_image.py --<br>
This python script takes the outputs from `pywikibot_missingImageCheck.py` and grabs associated images from the texture2D folder to automatically upload a scaled version to the wiki, with the correct naming convention and copywrite template. It generates a list of files it could not find in the folder, for additional manual work.

pywikibot_create_missing_item_page.py -- <br>
This python script reads a file of missing items, then runs `formatter_item_page.py` against that file to upload the pages to the wiki.

pywikibot_images_dlc_pet.py -- <br>
This python script pulls a list of pages that are both `Pets` and `DLC`, then associates specific cateogories for those file images, so they show up in various DPL queries on the wiki.

pywikibot_images_dlc_mount.py -- <br>
This python script pulls a list of pages that are both `Mounts` and `DLC`, then associates specific cateogories for those file images, so they show up in various DPL queries on the wiki.

pywikibot_images_dlc_mount_display.py -- (WIP) <br>
This python script checks for missing front and side mount images. Since the data has a top and bottom image of the mount, it will put them together, scale it, and upload it to the wiki.

pywikibot_redirect_creation.py -- <br>
This python script will create redirect pages to certain pages. Helpful for redirecting variants of something to the main page.

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