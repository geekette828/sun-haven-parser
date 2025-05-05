import subprocess
import os

# Phase 1 - JSON and Formatter Scripts
script_order = [
    "json_tools/item_list.py",
    "json_tools/quest_list.py",
    "json_tools/shop_inventory.py",
    "json_tools/recipes_list.py",
    "json_tools/image_list.py",
    "formatter/all_item_descriptions.py",
    "formatter/all_dialogue.py",
    "formatter/all_recipes.py",
    "formatter/all_shops.py",
    "formatter/all_npc_names.py",
]

# Phase 2 - Pywikibot Scripts
pwb_scripts = [
    "login",
    r"N:\Sun Haven Parser\pywikibot_tools\validators\missing_item.py",
    r"N:\Sun Haven Parser\pywikibot_tools\validators\missing_quests.py",
    r"N:\Sun Haven Parser\pywikibot_tools\validators\missing_recipe_template.py",
    r"N:\Sun Haven Parser\pywikibot_tools\validators\missing_item_images.py",
]

def run_scripts(script_list):
    for script in script_list:
        if os.path.exists(script):
            print(f"▶ Running {script}")
            result = subprocess.run(["python", script], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {script} completed successfully.\n")
            else:
                print(f"❌ Error running {script}:\n{result.stderr}")
                break
        else:
            print(f"⚠ Script not found: {script}")
            break

if __name__ == "__main__":
    run_scripts(script_order)
def run_pwb_scripts(pwb_list):
    for script in pwb_list:
        print(f"\n▶ Running Pywikibot: {script}")
        if "login" in script.lower():
            cmd = ["powershell", ".\\pwb.ps1", "login"]
        else:
            cmd = ["powershell", ".\\pwb.ps1", f'"{script}"']  # wrap path in quotes

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        for line in process.stdout:
            print(line, end="")
        process.wait()
        if process.returncode == 0:
            print(f"✅ {script} completed successfully.\n")
        else:
            print(f"❌ Error occurred while running {script}. Exit code {process.returncode}")
            break

if __name__ == "__main__":
    run_scripts(script_order)
    run_pwb_scripts(pwb_scripts)
