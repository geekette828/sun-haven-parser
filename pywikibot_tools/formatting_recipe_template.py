'''
This python script fixes the recipe template in the wiki so `pywikibot_compare_recipie.py` can run correctly. 
Each field needs to be on its own line, in the wiki for it to work properly.
This script also updates the spacing to make it more uniform.
'''

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config.constants as constants
import pywikibot
import re

# Setup PWB
import sys
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
pywikibot.config.throttle = constants.PWB_SETTINGS["throttle"]
pywikibot.config.max_retries = constants.PWB_SETTINGS["max_retries"]
pywikibot.config.retry_wait = constants.PWB_SETTINGS["retry_wait"]
pywikibot.config.user_agent = constants.PWB_SETTINGS["user_agent"]
site = pywikibot.Site("en", "sunhaven")

# Target pages using Template:Recipe
template = pywikibot.Page(site, "Template:Recipe")
pages = list(template.embeddedin(total=10000))
print(f"🔍 Scanning {len(pages)} pages using Template:Recipe...")

def fix_template_block(match):
    template_text = match.group(0)

    # Extract all |key = value pairs
    field_matches = re.findall(r"\|([^=|{}]+?)\s*=\s*([^|{}]*?)\s*(?=\||}})", template_text)

    cleaned_lines = ["{{Recipe"]
    id_line = None

    for key, value in field_matches:
        key = key.strip()
        value = value.strip()
        if key.lower() == "id":
            id_line = f"|id = {value}  }}"  # We’ll add the second } in the next line
        else:
            cleaned_lines.append(f"|{key} = {value}")

    if id_line:
        cleaned_lines.append(id_line + "}")  # Make sure to double-close
    else:
        cleaned_lines.append("}}")

    return "\n".join(cleaned_lines)

missing_fields_log = []

# Apply fix to all Recipe templates
for page in pages:
    text = page.text
    # Track missing required fields for debug
    for match in re.finditer(r"{{Recipe[\s\S]+?}}", text):
        block = match.group(0)
        missing = []
        if not re.search(r"\|ingredients\s*=", block):
            missing.append("Ingredients")
        if not re.search(r"\|workbench\s*=", block):
            missing.append("Workbench")
        if not re.search(r"\|time\s*=", block):
            missing.append("Time")
        if not re.search(r"\|yield\s*=", block):
            missing.append("Yield")
        if missing:
            missing_fields_log.append(f"{page.title()}: Missing {', '.join(missing)}")

    original_text = text

    fixed_text = re.sub(r"{{Recipe[\s\S]+?}}", fix_template_block, text)

    if fixed_text != original_text:
        print(f"✏️  Fixing formatting on: {page.title()}")
        page.text = fixed_text
        page.save(summary="Fixing recipe formatting for pywikibot scripts")

if missing_fields_log:
    debug_path = os.path.join(constants.OUTPUT_DIRECTORY, "Debug", "missing_recipe_fields.txt")
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write("\n".join(missing_fields_log))
    print(f"🛠️ Missing field debug written to: {debug_path}")

print("✅ Formatting fix complete.")

