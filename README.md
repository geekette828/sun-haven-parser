Collection of Parser Items for the Sun Haven wiki found at: https://sunhaven.wiki.gg/ <br>
Putting these into output files, so we can do a compare between patches, and only update pages that need it.
Some scripts to do some comparisons using pywikibot

# Parser Collections
config.py --<br>
This file specifies the input and output directories, so they can be dynamic based on the end user's file structure. <br>
It also holds the mapping for numeric to text conversions of things like stats, seasons, quest types, etc.<br>


## JSON Objects
JSON_imageList.py --<br>
Creates a massive json object based on sprite files located in the input directory. This will pull the image name and associated GUID.<br>

JSON_itemList.py --<br>
Creates a massive json object based on monobehaviour files located in the input directory. This will pull various information of each item, many of the fields in various infoboxes will use these numbers.<br>

JSON_questDetails.py --<br>
Creates a json object based on quest specific monobehaviour files located in the input directory. This will pull various information of each quest, many of the fields in various infoboxes will use these numbers.<br>

JSON_recipesList.py --<br>
Creates a json object based on recipes for items.<br>

JSON_shopInventory.py --<br>
Cretes a json object for the inventory of various shops.<br>

## Formatted for Wiki Consumption
Each of these will take the information from the JSON objects, or the asset files in the monobehaviour directory to build text files that have the wiki formatting already in them, so people can copy and paste directly into the wiki and worry less about formatting.<br>

formatter_dialogue.py --<br>
formatter_itemDescriptions.py --<br>
formatter_quests.py --<br>
formatter_recipes.py --<br>
formatter_shops.py --<br>

## pyWikiBot
These use the mediawiki api to do various comparisons and page creations directly into the wiki.<br>
The user must be in the PWB-Core folder and logged in to PyWikiBot using: python pwb.py login<br>

pywikibot_MissingDataCheck.py --<br>
This python module will review the SH wiki to make three lists: Items missing from the JSON file, Items missing from the wiki, Items in both the JSON and the wiki.<br>
It will then do a comparison between items in both the JSON and Wiki, to see what infobox items need to be updated (WIP).

pywikibot_ImageUploader.py --<br>
(WIP) Reviews the `comparison_summary.txt` file for the items not in the wiki. Then creates a file of items and their associated images.<br>
Image names get updated, then using pillow we scale up the images, then using pywikibot we upload them to the wiki.<br>

# Using the Parser
## Getting the Assets
1. Download an application that allows you to look at the assets. I use [AssetRipper](https://github.com/AssetRipper/AssetRipper).
2. In the preferred asset manager, load the `Sun Haven_Data` folder. For most people it will be located in something like this:
  * Windows: `C:/Program Files (x86)/Steam/steamapps/common/Sun Haven/Sun Haven_Data`
  * Linux: `${HOME}/.steam/steam/steamapps/common/Sun Haven/Sun Haven_Data`
3. Export the folder to an area of your choosing. You will want to choose the export type: `Unity Project`. This is how it will export:
### Directory Structure
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
4. Rename & update `config.example.py` where applicable for your paths.
5. Take the necessary file folders from the ripped project and drop them into the parser project input folder.
6. Run all of the JSON scripts first, to generate objects that the rest of the scripts will use to pull their data from. Then run all of the formatter scripts.
  * I recommend comparing the most recent pull of data to the previous pull of data using a comparison application like WinMerge.