import subprocess
import os

# ---------------------------------------------------------------------------
# Phase 1 — Builders
# Reads raw game files and produces structured JSON caches.
# Run item_builder first; other builders may depend on items_data.json.
# ---------------------------------------------------------------------------
builder_order = [
    "builders/item_builder.py",
    "builders/shop_builder.py",
    "builders/recipe_builder.py",
    "builders/npc_dialogue_builder.py",
    "builders/quest_builder.py",
    "builders/breakable_object_builder.py",
    "builders/image_builder.py",
    "builders/entity_builder.py",           # Requires Scenes folder
    "builders/fish_spawner_builder.py",     # Requires Scenes folder
    "builders/cutscene_builder.py",
]

# ---------------------------------------------------------------------------
# Phase 2 — Exporters
# Reads JSON caches and writes wiki-formatted .txt output files.
# Ordering matters where one exporter reads output from another.
#   all_npc_names  → produces Unique_NPC_Names_For_Patch.txt
#   npc_dialogue   → produces "<NPC> one liners.txt" per NPC
#   npc_cycles     → produces "<NPC> cycles.txt" per NPC
#   npc_walk_schedule → produces "<NPC>_schedule.txt" per NPC
#   create_npc_pages  → consumes all three of the above
# ---------------------------------------------------------------------------
exporter_order = [
    # Item / recipe / shop outputs
    "exporters/all_item_descriptions.py",
    "exporters/all_recipes.py",
    "exporters/all_shops.py",

    # NPC names (must run before create_npc_pages)
    "exporters/all_npc_names.py",

    # NPC dialogue outputs (must run before create_npc_pages)
    "exporters/npc_dialogue.py",
    "exporters/npc_cycles.py",
    "exporters/npc_romance_dialogue_unique_gifts.py",
    "exporters/npc_romance_gift_preferences.py",
    "exporters/npc_walk_schedule.py",
    "exporters/npc_wedding_cutscene.py",

    # NPC page assembly (depends on the four exporters above)
    "exporters/create_npc_pages.py",

    # Enemy / entity outputs (require Scenes folder)
    "exporters/all_monster_drops.py",
    "exporters/all_enemy_infoboxes.py",

    # Fish spawn chances (requires Scenes folder)
    "exporters/fish_spawn_chance.py",

    # Cutscene outputs (requires Scripts folder)
    "exporters/all_cutscenes.py",

    # Quest page assembly
    "exporters/create_quest_pages.py",
]

# ---------------------------------------------------------------------------
# Phase 3 — Pywikibot (commented out — run manually when ready)
# ---------------------------------------------------------------------------
# pwb_scripts = [
#     "login",
#     r"N:\Sun Haven Parser\wiki\validators\missing_item.py",
#     r"N:\Sun Haven Parser\wiki\validators\missing_quests.py",
#     r"N:\Sun Haven Parser\wiki\validators\missing_recipe_template.py",
#     r"N:\Sun Haven Parser\wiki\validators\missing_item_images.py",
# ]

# ---------------------------------------------------------------------------
# Phase 4 — Analysis Scripts
# ---------------------------------------------------------------------------
#analysis_order = [
#    "analysis/compare_patch_item_descriptions.py",
#    "analysis/compare_patch_item_pages.py",
#    "analysis/compare_patch_bb_quests.py",
#    "analysis/compare_patch_npc_names.py",
#]

# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------

def run_scripts(script_list):
    for script in script_list:
        if not os.path.exists(script):
            print(f"⚠ Script not found: {script}")
            break

        print(f"\n▶ Running {script}")
        try:
            process = subprocess.Popen(
                ["python", script],
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            process.wait()
            if process.returncode == 0:
                print(f"✅ {script} completed successfully.\n")
            else:
                print(f"❌ Error running {script} (exit code {process.returncode})")
                break
        except Exception as e:
            print(f"❌ Exception while running {script}: {e}")
            break


# def run_pwb_scripts(pwb_list):
#     for script in pwb_list:
#         print(f"\n▶ Running Pywikibot: {script}")
#         if "login" in script.lower():
#             cmd = ["powershell", ".\\pwb.ps1", "login"]
#         else:
#             cmd = ["powershell", ".\\pwb.ps1", f'"{script}"']
#
#         try:
#             process = subprocess.Popen(
#                 cmd,
#                 universal_newlines=True,
#                 encoding='utf-8',
#                 errors='replace'
#             )
#             process.wait()
#             if process.returncode == 0:
#                 print(f"✅ {script} completed successfully.\n")
#             else:
#                 print(f"❌ Error running {script} (exit code {process.returncode})")
#                 break
#         except Exception as e:
#             print(f"❌ Exception while running Pywikibot script {script}: {e}")
#             break


if __name__ == "__main__":
    run_scripts(builder_order)
    run_scripts(exporter_order)
    # run_pwb_scripts(pwb_scripts)
    # run_scripts(analysis_order)
