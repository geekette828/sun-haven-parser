
This project includes a full, vendored version of Pywikibot inside the pwb/ folder. 
There’s no need to install it separately or use it as a submodule.

    💡 All Pywikibot commands should be run through the included pwb.ps1 launcher to ensure the correct environment is used.

Update `pwb\user-config.py.sample` to `pwb\user-config.py`
Replace `YourUsernameHere` with your wiki.gg username.

Update `pwb\user-password.py.sample` to `pwb\user-password.py`
Replace `YourUserNameHere` with your wiki.gg username.
Replace `YourBotNameHere` with the name you gave it in the `Special:ApplicationPasswords` page
Replace `YourBotPasswordHere` with the long unique hash for that specific bot name, that the wiki gave you. 

    🚨🔐 DO NOT SHARE THIS PASSWORD WITH ANYONE. 🔐🚨

Login to pywikibot useing the command:
`.\pwb.ps1 login`

This means running any of the pywikibot parser scripts needs to have the full path.
`.\pwb.ps1 "U:\R-PATH\Sun Haven Parser\pywikibot_tools\compare_recipe.py"`