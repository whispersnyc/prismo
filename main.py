import argparse
from colorsys import rgb_to_hls
from subprocess import Popen, check_output, DEVNULL, CalledProcessError
from json import loads, dumps
import os
from os import path
import sys
import pywal
import pywal.backends.wal
import winreg
from template_parser import apply_template
from config_manager import (
    load_config, home, data_path, config_path,
    template_path, licenses_path
)

# Global config - will be loaded in main()
config = {}

# get current Windows wallpaper path
def get_wallpaper():
    """Get current Windows wallpaper path from registry"""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_READ) as key:
        value, reg_type = winreg.QueryValueEx(key, "WallPaper")
        return value

# convert path to Linux format for WSL (handles both forward and backslashes)
convert = lambda i: "/mnt/" + i[0].lower() + i[2:].replace("\\", "/")


def fatal(msg, parser=None):
    """Prints message then ends program"""
    print(msg+'\n')
    if parser: # print parser help message
        parser.print_help()
    sys.exit(2)


class Parser(argparse.ArgumentParser):
    """Show help menu on argparse error"""
    def error(self, message):
        fatal("error: "+message, self)


def gen_colors(img, apply_config=True, light_mode=False, templates=None, wsl=None, config_dict=None):
    """Generates color scheme from image and applies to templates.

    Parameters:
        img (string): path leading to input image
        apply_config (bool): whether to apply templates and WSL config
        light_mode (bool): generate light mode color scheme
        templates (set): specific templates to apply (None = all from config)
        wsl (bool): whether to apply WSL (None = use config)
        config_dict (dict): config dictionary to use (None = use global config)

    Returns:
        dict: Results with template application status
            {
                "succeeded": [template_name1, template_name2, ...],
                "failed": [{"name": template_name, "error": error_msg}, ...]
            }
    """

    # Use provided config or fall back to global config
    active_config = config_dict if config_dict is not None else config

    # Track template application results
    results = {"succeeded": [], "failed": []}

    # get/create color scheme
    wal = pywal.colors.colors_to_dict(
            pywal.colors.saturate_colors(
                pywal.backends.wal.get(img, light_mode),
                ""), img)
    print("Generated pywal colors" + (" (light mode)" if light_mode else ""))

    # write formatted JSON file
    json_path = home + "\\.cache\\wal\\colors.json"
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
        return results

    # WSL / wpgtk
    apply_wsl = wsl if wsl is not None else active_config.get("wsl")
    if apply_wsl: # wpgtk
        wsl_distro = apply_wsl if isinstance(apply_wsl, str) else active_config.get("wsl")
        if wsl_distro:
            wsl_cmd = "wsl -d " + wsl_distro
            wsl_img = convert(img)
            Popen(wsl_cmd + " -- wpg -s \"%s\"" % wsl_img, shell=True)
            img_name = wsl_img.replace("/", "_").replace(" ", "\\ ")
            Popen(wsl_cmd + " -- rm ~/.config/wpg/schemes/" + img_name[:img_name.rfind('.')] + '*', shell=True)
            print("Applied WSL wpgtk theme")

    # apply templates
    templates_to_apply = templates if templates is not None else active_config.get("templates", {}).keys()
    for base_name in templates_to_apply:
        output = active_config.get("templates", {}).get(base_name)
        if not output:
            error_msg = "Not found in config"
            print("Skipped %s template (%s)" % (base_name, error_msg))
            results["failed"].append({"name": base_name, "error": error_msg})
            continue

        # Automatically append .prismo extension if not present
        template_file = base_name if base_name.endswith('.prismo') else base_name + '.prismo'
        template = template_path + '\\' + template_file

        if not path.exists(template):
            error_msg = "Template file is missing: %s" % template_file
            print("Skipped %s template (%s)" % (base_name, error_msg))
            results["failed"].append({"name": base_name, "error": error_msg})
            continue

        # Use new .prismo template parser - continue on failure
        try:
            output_resolved = os.path.expandvars(os.path.expanduser(output))
            apply_template(template, wal, output_resolved)
            print("Applied %s template to %s" % (base_name, output_resolved))
            results["succeeded"].append(base_name)
        except Exception as e:
            error_msg = str(e)
            print("Error applying %s template: %s" % (base_name, error_msg))
            results["failed"].append({"name": base_name, "error": error_msg})

    return results



def main(test_args=None, test_config=None, custom_config_path=None):
    """Process flags and read current wallpaper."""

    # Load configuration first (initializes data directory if needed)
    global config
    if not test_config:
        config = load_config(custom_config_path=custom_config_path)
    else:
        config = test_config

    # Launch GUI if no arguments provided (unless --headless is specified)
    if test_args is None and len(sys.argv) == 1:
        # No arguments, launch GUI
        try:
            from gui import main as gui_main
            gui_main()
            return
        except Exception as e:
            print(f"Error launching GUI: {e}")
            print("Falling back to CLI mode...\n")

    # check if imagemagick installed to path
    try:
        check_output(["where", "magick"])
    except CalledProcessError:
        try:
            check_output(["where", "montage"])
        except CalledProcessError:
            fatal("Imagemagick isn't installed to system path. Check README.")

    # parse arguments
    parser = Parser()
    parser.description = "Reads current Windows wallpaper, generates pywal color scheme, " \
        "and applies to templates."
    parser.add_argument("-hl", "--headless", action="store_true",
            help="run in headless/CLI mode (default behavior when arguments are provided)")
    parser.add_argument("-c", "--config", type=str, default=None,
            help="path to custom config folder containing config.yaml and templates/ (default: %%LOCALAPPDATA%%\\Prismo)")
    parser.add_argument("-co", "--colors-only", action="store_true",
            help="generate colors and format JSON only, skip config-based templates and WSL")
    parser.add_argument("-lm", "--light-mode", action="store_true",
            help="generate light mode color scheme instead of dark mode")
    parser.add_argument("-t", "--templates", nargs="?", const="__list__", default=None,
            help="apply specific templates (comma-separated list, e.g., 'discord,obsidian'). "
                 "If no list provided, prints available templates and config path, then exits")
    parser.add_argument("-w", "--wsl", nargs="?", const="__config__", default=None,
            help="apply WSL/wpgtk theme. Optionally specify WSL distro name. "
                 "If no name provided, uses config value")
    parser.add_argument("filepath", nargs="?", default=None,
            help="optional path to image file (if not provided, uses current wallpaper)")
    args = parser.parse_args(test_args)

    # Handle custom config path
    if args.config:
        if not test_config:  # Only apply if not in test mode
            config = load_config(custom_config_path=args.config)

    # Handle --templates flag without list (print available templates)
    if args.templates == "__list__":
        print("Available templates in config:")
        templates = config.get("templates", {})
        if templates:
            for template_name, output_path in templates.items():
                # Display name is the config key (without extension)
                display_name = template_name.replace('.prismo', '').upper()
                # Actual file has .prismo extension
                template_file = template_name if template_name.endswith('.prismo') else template_name + '.prismo'
                print(f"  - {display_name}: {template_file} -> {output_path}")
        else:
            print("  (no templates configured)")
        print(f"\nConfig file location: {config_path}")
        sys.exit(0)

    # Handle --wsl flag
    if args.wsl is not None:
        if args.wsl == "__config__":
            # Use config WSL value
            if not config.get("wsl", "").strip():
                fatal("WSL distro not specified and no WSL configured in config file.\n"
                      "Either provide a distro name with -w/--wsl or configure it in: " + config_path)
        # else: args.wsl contains the distro name

    # If only --headless flag was provided, process normally (will generate from current wallpaper)
    # Otherwise continue with normal CLI behavior

    # determine light mode: flag takes priority over config, default to False
    light_mode = args.light_mode if args.light_mode else config.get("light_mode", False)

    # use provided filepath or get current wallpaper
    if args.filepath:
        current_wal = args.filepath
        if not path.isfile(current_wal):
            fatal("Provided image file does not exist: " + current_wal)
        print("Using provided image: " + current_wal)
    else:
        # get current wallpaper
        try:
            current_wal = get_wallpaper()
            print("Current wallpaper: " + current_wal)
        except Exception as e:
            # fallback to TranscodedWallpaper if binary fails
            current_wal = home + "\\AppData\\Roaming\\Microsoft\\Windows\\Themes\\TranscodedWallpaper"
            print("Using fallback wallpaper path: " + current_wal)

            # check if fallback file exists
            if not path.isfile(current_wal):
                fatal("Could not detect wallpaper and fallback file doesn't exist.\n"
                      "Please set a wallpaper in Windows settings first.")

    # generate colors and apply config
    try:
        # Determine which templates to apply
        templates_to_apply = None
        if args.templates and args.templates != "__list__":
            # Parse comma-separated template list
            templates_to_apply = set(t.strip() for t in args.templates.split(","))
            # Validate templates exist in config
            for template in templates_to_apply:
                if template not in config.get("templates", {}):
                    print(f"Warning: template '{template}' not found in config, skipping")
            templates_to_apply = templates_to_apply & set(config.get("templates", {}).keys())

        # Determine WSL setting
        wsl_setting = None
        if args.wsl is not None:
            if args.wsl == "__config__":
                wsl_setting = config.get("wsl", "")
            else:
                wsl_setting = args.wsl

        # Determine if we should apply config
        apply_config = not args.colors_only or args.templates or args.wsl

        gen_colors(
            current_wal,
            apply_config=apply_config,
            light_mode=light_mode,
            templates=templates_to_apply,
            wsl=wsl_setting
        )
    except Exception as e:
        fatal("Error generating colors from wallpaper: " + str(e) + "\n"
              "The wallpaper file may be corrupted or in an unsupported format.")

    print("\nDone.")
    exit()

if __name__ == "__main__":
    main()