Collection of Parser Items for the Sun Haven wiki found at: https://sunhaven.wiki.gg/ <br>
Putting these into output files, so we can do a compare between patches, and only update pages that need it.
Some scripts to do some comparisons using pywikibot

# Parser Collections
config.py --<br>
This file specifies the input and output directories, so they can be dynamic based on the end user's file structure. <br>
It also holds the mapping for numeric to text conversions of things like stats, seasons, quest types, etc.<br>


## JSON Objects
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

##pyWikiBot
These use the mediawiki api to do various comparisons and page creations directly into the wiki.
