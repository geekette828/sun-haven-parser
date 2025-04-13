import subprocess
import os

script_order = [
    "JSON_item_list.py",
    "JSON_quest_details.py",
    "JSON_shop_inventory.py",
    "JSON_image_list.py",
    "formatter_item_descriptions.py",
    "formatter_dialogue.py",
    "formatter_recipes.py",
    "formatter_shops.py",
    "formatter_quests.py"
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
