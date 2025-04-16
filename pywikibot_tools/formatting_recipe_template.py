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
    field_dict = {key.strip().lower(): value.strip() for key, value in field_matches}

    # Field order (product inserted manually)
    ordered_fields = [
        ("workbench", ""),
        ("ingredients", ""),
        ("time", ""),
        # (product goes here if it exists)
        ("yield", None),  # Defaulted below
        ("recipesource", ""),
        ("id", "")
    ]

    cleaned_lines = ["{{Recipe"]
    already_perfect = True

    for key, default in ordered_fields:
        # Special case for yield
        if key == "yield":
            if "yield" in field_dict:
                current_val = field_dict["yield"]
                if current_val == "":
                    current_val = "1"
                    already_perfect = False
            else:
                current_val = "1"
                already_perfect = False

        # Special insertion of product
        elif key == "time":
            current_val = field_dict.get(key, default)
            if current_val == "" and key not in field_dict:
                already_perfect = False
            cleaned_lines.append(f"|{key} = {current_val}")
            if "product" in field_dict:
                cleaned_lines.append(f"|product = {field_dict['product']}")
                if "product" not in template_text:
                    already_perfect = False
            continue

        else:
            current_val = field_dict.get(key, default)
            if current_val == "" and key not in field_dict:
                already_perfect = False

        if key == "id":
            cleaned_lines.append(f"|{key} = {current_val}  }}}}")
        else:
            cleaned_lines.append(f"|{key} = {current_val}")

    rebuilt = "\n".join(cleaned_lines)

    if already_perfect and template_text.strip() == rebuilt.strip():
        return None

    return rebuilt

# Wrapper to prevent deletion on None
def fix_template_block_safe(match):
    result = fix_template_block(match)
    return result if result else match.group(0)

missing_fields_log = []

# Apply fix
for page in pages:
    text = page.text

    # Track missing required fields
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

    # Perform substitution with safety wrapper
    fixed_text = re.sub(r"{{Recipe[\s\S]+?}}", fix_template_block_safe, text)

    if fixed_text != text:
        print(f"✏️  Fixing formatting on: {page.title()}")
        page.text = fixed_text
        page.save(summary="PyWikiBot formatting: Fixing recipe formatting for other PWB scripts")

# Save debug log if needed
if missing_fields_log:
    debug_path = os.path.join(constants.OUTPUT_DIRECTORY, "Debug", "missing_recipe_fields.txt")
    os.makedirs(os.path.dirname(debug_path), exist_ok=True)
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write("\n".join(missing_fields_log))
    print(f"🛠️ Missing field debug written to: {debug_path}")

print("✅ Formatting fix complete.")