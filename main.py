import argparse
from colorsys import rgb_to_hls
from subprocess import Popen, check_output, DEVNULL, CalledProcessError
from json import loads, dumps
from os import path, mkdir
import sys
import pywal
import pywal.backends.wal
from shutil import copytree
import winreg

home = path.expanduser("~").replace("\\", "/")
data_path = home+"/AppData/Local/prisma"
config_path = data_path+"/config.json"
template_path = data_path+"/templates"
licenses_path = data_path+"/licenses"
config = {}

# get current Windows wallpaper path
def get_wallpaper():
    """Get current Windows wallpaper path from registry"""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_READ) as key:
        value, reg_type = winreg.QueryValueEx(key, "WallPaper")
        return value

# convert path to Linux format for WSL
convert = lambda i: "/mnt/"+i[0].lower()+i[2:].replace("\\", "/")


def fatal(msg, parser=None):
    """Prints message then ends program"""
    print(msg+'\n')
    if parser: # print parser help message
        parser.print_help()
    sys.exit(2)


def resource(relative_path):
    """Get absolute path to resource for dev/PyInstaller"""
    try: # PyInstaller temp folder
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = path.abspath(".")
    return "/".join([base_path, "resources", relative_path])


class Parser(argparse.ArgumentParser):
    """Show help menu on argparse error"""
    def error(self, message):
        fatal("error: "+message, self)


def gen_colors(img, apply_config=True, light_mode=False):
    """Generates color scheme from image and applies to templates.

    Parameters:
        img (string): path leading to input image
        apply_config (bool): whether to apply templates and WSL config
        light_mode (bool): generate light mode color scheme
    """

    # get/create color scheme
    wal = pywal.colors.colors_to_dict(
            pywal.colors.saturate_colors(
                pywal.backends.wal.get(img, light_mode),
                ""), img)
    print("Generated pywal colors" + (" (light mode)" if light_mode else ""))

    # write formatted JSON file
    json_path = home+"/.cache/wal/colors.json"
    with open(json_path, "w") as cj:
        cj.write(dumps(wal, indent=4))
    print("Updated colors.json with formatted output: " + json_path)

    # pywalfox update
    try:
        Popen(["python", "-m", "pywalfox", "update"])
        print("Pywalfox updated")
    except Exception:
        print("Pywalfox not updated")

    # process color scheme
    wal["colors"].update(wal["special"])
    wal = wal["colors"]
    print("Processed color scheme")
    print("\n\tBackground: %s\n\tForeground: %s\n" % (wal["background"], wal["foreground"]))

    # apply config options if specified
    if not apply_config:
        return

    # WSL / wpgtk
    if config.get("wsl"): # wpgtk
        wsl = "wsl -d " + config["wsl"]
        wsl_img = convert(img)
        Popen(wsl + " -- wpg -s \"%s\"" % wsl_img, shell=True)
        img_name = wsl_img.replace("/", "_").replace(" ", "\\ ")
        Popen(wsl + " -- rm ~/.config/wpg/schemes/" + img_name[:img_name.rfind('.')] + '*', shell=True)
        print("Applied WSL wpgtk theme")

    # apply templates
    for (base_name,output) in config.get("templates", {}).items():
        if not path.exists(template := (template_path+'/'+base_name)):
            print("Skipped %s template (either template file or output folder is missing)" % base_name)
            continue
        with open(template, encoding='cp850') as base:
            base = base.read()
            for k in wal.keys():
                # process replacement of base, ex. {color0}
                base = base.replace("{%s}"%k, wal[k])
                if '{'+k+'.' in base:
                    # process replacement of component, ex. {color0.r}/{color0.h}
                    rgb = tuple(int(wal[k].strip("#")[i:i+2], 16) for i in (0, 2, 4))
                    hls = rgb_to_hls(*[j/255.0 for j in rgb])
                    hls = [str(hls[i]*100)+"%" if i > 0 else hls[i]*360 for i in range(3)]
                    for c in range(3):
                        base = base.replace("{%s.%s}" % (k, "rgb"[c]), str(rgb[c]))
                        base = base.replace("{%s.%s}" % (k, "hls"[c]), str(hls[c]))
            with open(output, "w", encoding='cp850') as output:
                output.write(base)
        print("Applied %s template" % base_name)



def main(test_args=None, test_config=None):
    """Process flags and read current wallpaper."""

    # check if imagemagick installed to path
    try:
        check_output(["where", "magick"])
    except CalledProcessError:
        try:
            check_output(["where", "montage"])
        except CalledProcessError:
            fatal("Imagemagick isn't installed to system path. Check README.")

    global config
    if not test_config:
        # make data folder and config if not exist
        if not path.isdir(data_path):
            mkdir(data_path)
        if not path.isdir(template_path):
            copytree(resource("templates"), template_path)
        if not path.isdir(licenses_path):
            copytree(resource("licenses"), licenses_path)
        if not path.isfile(config_path):
            with open(resource("config_template.json")) as c:
                config_content = c.read().replace("HOME", home)
            with open(config_path, "w") as c:
                c.write(config_content)
            print("Config file created in %s.\n"
                  "Edit if desired then run this tool again.\n" % config_path)
            input("Press Enter to exit.")
        else:
            with open(config_path) as c:
                config_content = c.read()
        config = loads(config_content)
    else:
        config = test_config

    # parse arguments
    parser = Parser()
    parser.description = "Reads current Windows wallpaper, generates pywal color scheme, " \
        "and applies to templates."
    parser.add_argument("-co", "--colors-only", action="store_true",
            help="generate colors and format JSON only, skip config-based templates and WSL")
    parser.add_argument("-lm", "--light-mode", action="store_true",
            help="generate light mode color scheme instead of dark mode")
    args = parser.parse_args(test_args)

    # determine light mode: flag takes priority over config, default to False
    light_mode = args.light_mode if args.light_mode else config.get("light_mode", False)

    # get current wallpaper
    try:
        current_wal = get_wallpaper()
        print("Current wallpaper: " + current_wal)
    except Exception as e:
        # fallback to TranscodedWallpaper if binary fails
        current_wal = home+"/AppData/Roaming/Microsoft/Windows/Themes/TranscodedWallpaper"
        print("Using fallback wallpaper path: " + current_wal)

        # check if fallback file exists
        if not path.isfile(current_wal):
            fatal("Could not detect wallpaper and fallback file doesn't exist.\n"
                  "Please set a wallpaper in Windows settings first.")

    # generate colors and apply config
    try:
        gen_colors(current_wal, apply_config=not args.colors_only, light_mode=light_mode)
    except Exception as e:
        fatal("Error generating colors from wallpaper: " + str(e) + "\n"
              "The wallpaper file may be corrupted or in an unsupported format.")

    print("\nDone.")
    exit()

if __name__ == "__main__":
    main()