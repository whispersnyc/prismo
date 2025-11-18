# Prisma

Prisma uses [pywal](https://github.com/dylanaraps/pywal/) to generate color schemes from your current Windows wallpaper and apply them to Firefox (including websites), Discord, Obsidian, Alacritty, VS Code, WSL GTK/QT, etc.

This tool was inspired by wpgtk which provides similar functionality in Linux. In it's current state, using Prisma requires basic terminal skill.
  
Prisma is released under the [GNU General Public License v3.0](COPYING).
  - The author is not responsible for any damage, loss, or issues arising from the use or misuse of this GPL3 licensed software.  
The summary below is from [tl;drLegal](https://www.tldrlegal.com/license/gnu-general-public-license-v3-gpl-3).
  - You may copy, distribute and modify the software as long as you track changes/dates in source files.
  - Any modifications to or software including (via compiler) GPL-licensed code must also be made available under the GPL along with build & install instructions.
  
  
## Installation  
 
1. Install [ImageMagick](https://imagemagick.org/script/download.php#windows) while making sure "Add application directory to your system path" is enabled then restart your PC.
2. Click "prisma.exe" under Assets in the [Latest Release](https://github.com/rakinishraq/prisma/releases/latest) page to download.  
3. Run the exe once and wait a few seconds to extract resources and templates. Press Enter to exit.  
4. Run the exe again to generate a theme with your current Windows wallpaper.
5. Install any Integrations from the [Integrations section](https://github.com/rakinishraq/prisma#Integrations) right below.  

To make changes to the generated config file, like to enable animated wallpapers or some of the integrations below, use the following [Configuration section](https://github.com/rakinishraq/prisma#configuration).

This is optional if you just want to generate colors for Discord from your static Windows wallpaper. However, Prisma is overkill for this use case so check out my fork of [pywal-discord](https://github.com/rakinishraq/pywal-discord).
  
  
## Integrations

- **Visual Studio Code:** Install the [extension](https://marketplace.visualstudio.com/items?itemName=dlasagno.wal-theme) and enable the theme in the Settings menu.
- **Websites:** Install the Dark Reader extension from the [Chrome Web Store](https://chrome.google.com/webstore/detail/dark-reader/eimadpbcbfnmbkopoojfekhnkhdbieeh) or [Firefox add-ons](https://addons.mozilla.org/en-US/firefox/addon/darkreader/). You can set the background and foreground colors in `See more options > Colors` section.
  - Get the colors for these fields as detailed in the "And More!" integration below.
  - An automation like Pywalfox's native messenger is in progress.
- **Firefox/Thunderbird:** Install the Pywalfox [extension](https://addons.mozilla.org/en-US/firefox/addon/pywalfox/) and [application](https://github.com/Frewacom/pywalfox). The process for the latter may be complex for those new to Python/Pip. Tested with Librewolf.
- **Chrome:** Use [wal-to-crx](https://github.com/mike-u/wal-to-crx) to generate a theme file. Unfortunately, this process is not seamless like Pywalfox and untested.
- **Obsidian:** Edit the entry of your Vault's location in the config file under "obsidian" like the [example config file](https://github.com/rakinishraq/prisma#Configuration) below. For unsupported themes, edit the BG/FG colors using the Style Settings plugin usually (details in the "And More!" integration below).
- **Disclaimer:** _Usage of BetterDiscord to apply themes is subject to user discretion and risk. It's important to note that custom clients are not permitted under Discord's Terms of Service and may result in user penalties, including account bans. As a developer, I bear no responsibility for any repercussions from using BetterDiscord or any other custom client. Please adhere to Discord's Terms of Service._
- **Discord:** If you agree to the above, install [BetterDiscord](https://betterdiscord.app/) and enable the theme in the Settings menu.
  - Standalone installer and alternate theme available [here](https://github.com/rakinishraq/pywal-discord).
- **Neovim:** Use this [Neovim theme](https://github.com/AlphaTechnolog/pywal.nvim) for pywal support in WSL and potentially native Windows as well.
- **Windows 10/11 Theme:** The color scheme of Windows can be set to automatically adapt in `Settings > Colors > Accent color (set to Automatic)`.
- **Alacritty:** An Alacritty configuration file is included but enabling it means you must make all edits in the templates file and run the tool to update. A line-replacing update method is in progress to prevent this.
- **WSL GTK/QT:** Set the WSL variable as the name of your WSL OS name if you want [wpgtk](https://github.com/deviantfero/wpgtk) compatibility (more readable terminal color scheme as well as GTK/QT and other Linux GUI app theming). All Pywal supported apps should update automatically, too. If WSL is not installed, leave it empty.
  - **Zathura:** Install and run [this script](https://github.com/GideonWolfe/Zathura-Pywal) within WSL to generate a new themed zathurarc file.
  - There's probably a similar process for many other Linux apps that sync with Linux's pywal theme files, which wpgtk generates. This was tested with GWSL on feh and zathura.
  - wpgtk depends on the imagemagick package
- **And More!** The background and foreground colors are shown in the command line output and the full color scheme is available in `C:/Users/USER/.cache/wal/colors.json` to manually input in any app.
  
  
## Configuration

Edit the new C:/Users/USER/AppData/Local/prisma/config.json file with any text editor. Example:

```
{
    "templates":
    {
        "alacritty.txt": "C:/Users/USER/AppData/Roaming/alacritty/alacritty.yml",
        "discord.txt": "C:/Users/USER/AppData/Roaming/BetterDiscord/themes/pywal-discord-default.theme.css",
        "obsidian.txt": "C:/Users/USER/Documents/Notes/.obsidian/themes/pywal.css"
    },

    "wsl": "Manjaro"
}
```

### Formatting
- Paths must use "/", not the usual Windows "\\".
- Each line in the templates section is formatted with the template filename on the left and the target file to replace on the right.
- Every line except the last one must end with a comma, including within curly brackets.

### Custom Templates
- The default templates (Alacritty, Discord and Obsidian) are located in the "templates" folder next to this config file.
- In the template files, {colorname} is replaced with the hex code for a color or a HSL/RGB component like {colorname.r} for Red.
- The available color names are color0, color1...color15, background, foreground and cursor. The available components are Hue (0-360), Saturation (0%-100%), Lightness (0%-100%), Red (0-255), Green (0-255) and Blue (0-255).

### WSL
- Set the WSL variable to the name of your WSL distribution if you want wpgtk integration. If WSL is not installed, leave it empty ("").  
  
  
  
## CLI Usage

```
Reads current Windows wallpaper, generates pywal color scheme, and applies to templates.

options:
  -h, --help            show this help message and exit
  -co, --colors-only    generate colors and format JSON only, skip config-based templates and WSL
```


## Common Uses

- `.\prisma.exe` reads your current Windows wallpaper, generates a pywal color scheme from it, and applies all configured templates and WSL integration.
- `.\prisma.exe -co` reads your current Windows wallpaper and generates a pywal color scheme, but skips applying templates and WSL integration. This is useful if you only want to generate the colors.json file for use with other tools.

  

## Build Instructions

This is an optional section for those who want to modify the code and execute using a virtual environment:
1. Clone the repo then open a terminal session in the folder or use `cd <path-to-Prisma>/Prisma`
   - For the former, shift-right click in an empty area in the folder, click Open Powershell window here 
2. Execute `python -m venv .venv` to create a virtual environment
3. Install all the required modules with `./.venv/Scripts/pip.exe install -r requirements.txt`
4. To run from source: Execute `./LAUNCH.ps1 <arguments>` or `./.venv/Scripts/python.exe main.py <ARGUMENTS>`
5. To build into .exe: Execute `./COMPILE.ps1` or `./.venv/Scripts/pyinstaller --noconfirm --onefile --console --name "Prisma" --clean --add-data "./resources;resources/" "./main.py"`
  
  
## Credits

The respective licenses are in the [repo resources folder](https://github.com/rakinishraq/prisma/tree/main/resources/licenses) and copied into the Local Appdata folder.

- Discord template from [pywal-discord](https://github.com/FilipLitwora/pywal-discord) d12972d by FilipLitwora (GNU General Public License v3.0)
  - changes: colors of theme subsituted in theme css file
- Obsidian template from [pywal-obsidianmd](https://github.com/poach3r/pywal-obsidianmd) by poach3r (unlicensed)
  - changed formatting and some background colors
- wallpaper detection binary from [win-wallpaper](https://github.com/sindresorhus/win-wallpaper) by sindresorhus (MIT License)
- Alacritty template from [alacritty](https://github.com/alacritty/alacritty) by The Alacritty Project (Apache License, Version 2.0)
  - changes: colors of tomorrow night theme subsituted in default config file
- color scheme file generation from [pywal](https://github.com/dylanaraps/pywal) module by Dylan Araps