import sys
import config.constants as constants
import pywikibot

# Set up necessary configurations before other imports
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
site = pywikibot.Site()

def to_title_case(name):
    """Convert a string to title case while preserving apostrophes correctly."""
    return ' '.join([
        word.capitalize() if "'" not in word else word[0].upper() + word[1:]
        for word in name.split()
    ])

def main():
    site = pywikibot.Site()
    
    redirect_map = {
        "Cape": [
            "Black Cape", "Blue Cape", "Brown Cape", "Gray Cape", "Green Cape", "Orange Cape", "Pink Cape", "Purple Cape", "Red Cape", "White Cape", "Yellow Cape"
        ]
       # "Yeti Mount Whistle": [
        #    "Blue Snow Yeti Mount Whistle", "Pink Snow Yeti Mount Whistle"
       # ]
    }

    for target, variants in redirect_map.items():
        for variant in variants:
            redirect_title = to_title_case(variant)
            page = pywikibot.Page(site, redirect_title)

            if page.exists():
                print(f"Skipping '{redirect_title}': Page already exists.")
                continue

            page.text = f"#REDIRECT [[{target}]]"
            page.save(summary=f"Creating redirect to [[{target}]]")

if __name__ == "__main__":
    main()
