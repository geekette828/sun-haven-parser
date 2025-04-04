import sys
import config.constants as constants
import pywikibot

# Set up necessary configurations before other imports
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
site = pywikibot.Site()

def main():
    site = pywikibot.Site()
    
    redirect_map = {
        "Kitty (pet)": [
            "Black Kitty", "Grey Kitty", "Tuxedo Kitty", "Orange Kitty", "Calico Kitty"
        ],
        "Buppy": [
            "White Buppy", "Black Buppy", "Spotted Buppy", "Brown Buppy"
        ],
        "Kit": [
            "Red Kit", "Orange Kit", "Yellow Kit", "Green Kit", "Purple Kit", "Pink Kit", "Black Kit"
        ],
        "Unicorn": [
            "Black Unicorn", "Red Unicorn", "Orange Unicorn", "Yellow Unicorn", "Green Unicorn",
            "Blue Unicorn", "Purple Unicorn", "Pink Unicorn", "Flaming Unicorn"
        ],
        "Smolder": [
            "Yellow Smolder", "Purple Smolder", "Black Smolder", "White Smolder", "Blue Smolder", "Green Smolder"
        ],
        "Bubbles": [
            "Teal Bubbles", "Blue Bubbles", "Pink Bubbles", "Flame Bubbles"
        ],
        "Mister Slither": [
            "Striped Mister Slither", "Red Mister Slither", "Orange Mister Slither", "Yellow Mister Slither",
            "Blue Mister Slither", "Purple Mister Slither"
        ],
        "Percy": [
            "Orange Percy", "Green Percy", "Blue Percy", "Purple Percy", "Pink Percy", "Black Percy"
        ],
        "Shiver": [
            "Red Shiver", "Orange Shiver", "Yellow Shiver", "Green Shiver", "Blue Shiver",
            "Purple Shiver", "Pink Shiver", "Octavius"
        ],
        "Sprinkles": [
            "Blueberry Sprinkles", "Chocolate Sprinkles", "Mint Sprinkles", "Strawberry Sprinkles",
            "Vanilla Sprinkles", "Matcha Sprinkles", "Sprinkles Plushie"
        ],
        "Bat Mount Whistle": [
            "Black Bat Mount Whistle", "Brown Bat Mount Whistle", "Candy Corn Bat Mount Whistle",
            "Lavender Bat Mount Whistle", "Pink Bat Mount Whistle", "Teal Bat Mount Whistle",
            "Yellow Bat Mount Whistle"
        ],
        "Lion Mount Whistle": [
            "Black Lion Mount Whistle", "Blue Lion Mount Whistle", "Pink Lion Mount Whistle",
            "Rainbow Lion Mount Whistle"
        ],
        "Fox Mount Whistle": [
            "Black Fox Mount Whistle", "Black and White Fox Mount Whistle", "Blue Fox Mount Whistle",
            "Green Fox Mount Whistle", "Pink Fox Mount Whistle"
        ],
        "Choo Choo Train Mount Whistle": [
            "Blue Choo Choo Train Mount Whistle", "Grey Choo Choo Train Mount Whistle",
            "Orange Choo Choo Train Mount Whistle", "Purple Choo Choo Train Mount Whistle",
            "Rainbow Choo Choo Train Mount Whistle", "Red Choo Choo Train Mount Whistle"
        ]
       # "Yeti Mount Whistle": [
        #    "Blue Snow Yeti Mount Whistle", "Pink Snow Yeti Mount Whistle"
       # ]
    }

    for target, redirects in redirect_map.items():
        for redirect_title in redirects:
            page = pywikibot.Page(site, redirect_title)
            if page.exists():
                print(f"Skipping '{redirect_title}': Page already exists.")
                continue
            page.text = f"#REDIRECT [[{target}]]"
            page.save(summary=f"Creating redirect to [[{target}]]")

if __name__ == "__main__":
    main()
