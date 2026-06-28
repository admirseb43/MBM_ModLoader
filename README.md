# MBM ModLoader
A mod loader to enhanced your **Monster Black Market (MBM)** (Mature rating game) from [Team-Apple Pie](https://ci-en.dlsite.com/creator/8791) experience. It allows you to manage your mod updates, making it a single click. UI handles 4 languages at the moment : chineese, english, french, russian.

# Credits
Country flags used came from lipis and his [flag-icons](https://github.com/lipis/flag-icons) repo.

# How to use (V1.0)
Download the latest version of the .exe file from release.
Execute it ideally you can palce it on his own folder (it will create a folder with your modlists and a folder for logs).
Pick your language at the bottom left (UI handles 4 languages at the moment : chineese, english, french, russian). Language are saved inside profile and will be remerbered after closing the game.
Set the path where you've placed your game (the root of the game where the "MonsterBlackMarket.exe" is).
Choose mods you want to update (you can choose a specific version of the mod if you know what you're doing)
After updating, the modlist will be saved as a profile that will be used (you can have several profile)

NB : Only works with mods that belongs to the "Mods" folder without altering game assets. That's the reason why not all mod are referenced at the moment. New version will manage this.
NB : if you uncheck a mod, it is not updated (not disabled or removed)

# What's left to do (TODO list)
- Add a description popup to explain what the does (showing a short description or showing the readme from repos ?)
- Handle more complex mod has Tits Mod from Krongorka or MBM.ModLoader from Tsygan_m249
- Handle profile as a real modlist (manage the mod and game folder)
- Handle languages of the mods (instead of installing all languages)
- Create a different project to store the mod database (for now it's a .json file)