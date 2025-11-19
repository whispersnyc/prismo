"""
Config Manager for Prisma
Centralized configuration loading and initialization
"""

import os
from os import path, mkdir
from json import loads
from shutil import copytree
import sys


# Path constants
home = path.expanduser("~")
data_path = home + "\\AppData\\Local\\prisma"
config_path = data_path + "\\config.json"
template_path = data_path + "\\templates"
licenses_path = data_path + "\\licenses"


def resource(relative_path):
    """Get absolute path to resource for dev/PyInstaller"""
    try:
        # PyInstaller temp folder
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = path.abspath(".")
    return "\\".join([base_path, "resources", relative_path])


def initialize_data_directory():
    """
    Initialize data directory structure and copy resources if needed.
    This ensures all required folders and files exist.

    Returns:
        bool: True if initialization was needed, False if already existed
    """
    needed_initialization = False

    # Create main data folder if it doesn't exist
    if not path.isdir(data_path):
        mkdir(data_path)
        needed_initialization = True
        print(f"Created data directory: {data_path}")

    # Create/copy templates folder if it doesn't exist
    if not path.isdir(template_path):
        try:
            copytree(resource("templates"), template_path)
            needed_initialization = True
            print(f"Copied templates to: {template_path}")
        except Exception as e:
            print(f"Warning: Could not copy templates: {e}")

    # Create/copy licenses folder if it doesn't exist
    if not path.isdir(licenses_path):
        try:
            copytree(resource("licenses"), licenses_path)
            needed_initialization = True
            print(f"Copied licenses to: {licenses_path}")
        except Exception as e:
            print(f"Warning: Could not copy licenses: {e}")

    # Create config file if it doesn't exist
    if not path.isfile(config_path):
        try:
            with open(resource("config.json")) as c:
                config_content = c.read().replace("HOME", home)
            with open(config_path, "w") as c:
                c.write(config_content)
            needed_initialization = True
            print(f"Created config file: {config_path}")
        except Exception as e:
            print(f"Warning: Could not create config file: {e}")

    return needed_initialization


def load_config(force_reload=False):
    """
    Load configuration from config.json.
    Automatically initializes data directory if it doesn't exist.

    Args:
        force_reload (bool): If True, reload config even if already loaded

    Returns:
        dict: Configuration dictionary
    """
    # Always ensure data directory exists first
    was_created = initialize_data_directory()

    # If we just created the config, prompt user to edit it
    if was_created and path.isfile(config_path):
        print("\nConfig file created. You may want to edit it to configure templates.")
        print(f"Config location: {config_path}\n")

    # Load the config file
    try:
        if path.isfile(config_path):
            with open(config_path) as c:
                config_content = c.read()
                config = loads(config_content)
                return config
        else:
            print(f"Warning: Config file not found at {config_path}")
            return {}
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def get_config_info():
    """
    Get information about the current configuration.
    Useful for debugging and displaying to users.

    Returns:
        dict: Config information including paths and template count
    """
    config = load_config()

    return {
        "config_path": config_path,
        "data_path": data_path,
        "template_path": template_path,
        "template_count": len(config.get("templates", {})),
        "templates": list(config.get("templates", {}).keys()),
        "wsl_enabled": bool(config.get("wsl", "").strip()),
        "wsl_distro": config.get("wsl", ""),
        "light_mode": config.get("light_mode", False)
    }


def reload_config():
    """
    Reload configuration from disk.
    Use this when config file changes are detected.

    Returns:
        dict: Reloaded configuration dictionary
    """
    return load_config(force_reload=True)


# Export commonly used paths
__all__ = [
    'load_config',
    'reload_config',
    'initialize_data_directory',
    'get_config_info',
    'home',
    'data_path',
    'config_path',
    'template_path',
    'licenses_path',
    'resource'
]
