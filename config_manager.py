"""
Config Manager for Prismo
Centralized configuration loading and initialization
"""

import os
from os import path, mkdir
import yaml
import sys


# Path constants
home = path.expanduser("~")
data_path = home + "\\AppData\\Local\\Prismo"
default_config_path = data_path + "\\config.yaml"
config_path = default_config_path  # Can be overridden by set_config_path()
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
    Each component (licenses, templates, config.yaml) is checked and created individually.

    Returns:
        bool: True if initialization was needed, False if already existed
    """
    from shutil import copy2
    needed_initialization = False

    # Create main data folder if it doesn't exist
    if not path.isdir(data_path):
        mkdir(data_path)
        needed_initialization = True
        print(f"Created data directory: {data_path}")

    # Create templates folder if it doesn't exist
    if not path.isdir(template_path):
        mkdir(template_path)
        needed_initialization = True
        print(f"Created templates directory: {template_path}")

    # Check and copy individual template files if missing
    try:
        import glob
        source_templates = glob.glob(resource("templates") + "\\*.prismo")
        for source_template in source_templates:
            template_name = path.basename(source_template)
            dest_template = path.join(template_path, template_name)
            if not path.isfile(dest_template):
                try:
                    copy2(source_template, dest_template)
                    needed_initialization = True
                    print(f"Copied template: {template_name}")
                except Exception as e:
                    print(f"Warning: Could not copy {template_name}: {e}")
    except Exception as e:
        print(f"Warning: Could not check template files: {e}")

    # Create licenses folder if it doesn't exist
    if not path.isdir(licenses_path):
        mkdir(licenses_path)
        needed_initialization = True
        print(f"Created licenses directory: {licenses_path}")

    # Check and copy individual license files if missing
    try:
        import glob
        source_licenses = glob.glob(resource("licenses") + "\\*")
        for source_license in source_licenses:
            if path.isfile(source_license):  # Only copy files, not directories
                license_name = path.basename(source_license)
                dest_license = path.join(licenses_path, license_name)
                if not path.isfile(dest_license):
                    try:
                        copy2(source_license, dest_license)
                        needed_initialization = True
                        print(f"Copied license: {license_name}")
                    except Exception as e:
                        print(f"Warning: Could not copy {license_name}: {e}")
    except Exception as e:
        print(f"Warning: Could not check license files: {e}")

    # Create config file if it doesn't exist
    if not path.isfile(config_path):
        try:
            with open(resource("config.yaml")) as c:
                config_content = c.read()
            with open(config_path, "w") as c:
                c.write(config_content)
            needed_initialization = True
            print(f"Created config file: {config_path}")
        except Exception as e:
            print(f"Warning: Could not create config file: {e}")

    return needed_initialization


def set_config_path(custom_folder):
    """
    Override the default config folder with a custom folder.
    This updates all related paths (config.yaml, templates/, licenses/).

    Args:
        custom_folder (str): Custom path to config folder (not the .yaml file itself)

    Returns:
        str: The resolved absolute config folder path
    """
    global config_path, data_path, template_path, licenses_path
    # Expand environment variables and user home directory
    resolved_folder = path.abspath(path.expandvars(path.expanduser(custom_folder)))

    # Update all paths to use the custom folder
    data_path = resolved_folder
    config_path = path.join(resolved_folder, "config.yaml")
    template_path = path.join(resolved_folder, "templates")
    licenses_path = path.join(resolved_folder, "licenses")

    return resolved_folder


def load_config(force_reload=False, custom_config_path=None):
    """
    Load configuration from config.yaml.
    Automatically initializes data directory if it doesn't exist.

    Args:
        force_reload (bool): If True, reload config even if already loaded
        custom_config_path (str): Optional custom path to config folder (containing config.yaml and templates/)

    Returns:
        dict: Configuration dictionary
    """
    # Set custom config folder if provided
    if custom_config_path:
        set_config_path(custom_config_path)

    # Always ensure data directory exists first (only for default config location)
    if config_path == default_config_path:
        was_created = initialize_data_directory()
        # If we just created the config, prompt user to edit it
        if was_created and path.isfile(config_path):
            print("\nConfig file created. You may want to edit it to configure templates.")
            print(f"Config location: {config_path}\n")

    # Load the config file
    try:
        if path.isfile(config_path):
            with open(config_path) as c:
                config = yaml.safe_load(c)
                return config if config else {}
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
        "wsl_enabled": bool(config.get("wsl", [])),
        "wsl_distros": config.get("wsl", []),
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
    'set_config_path',
    'initialize_data_directory',
    'get_config_info',
    'home',
    'data_path',
    'config_path',
    'default_config_path',
    'template_path',
    'licenses_path',
    'resource'
]
