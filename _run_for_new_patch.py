import subprocess
import os

script_order = [
    "json_tools/item_list.py",
    "json_tools/quest_details.py",
    "json_tools/shop_inventory.py",
    "json_tools/recipes_list.py",
    "json_tools/image_list.py",
    "formatter/item_descriptions.py",
    "formatter/dialogue.py",
    "formatter/recipes.py",
    "formatter/shops.py",
    "formatter/quests.py"
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
