import webview
from PIL import Image as PILImage, ImageEnhance
from json import loads, dumps
from os import path, remove
import base64
import io
from main import gen_colors, get_wallpaper
from config_manager import load_config, home, config_path


class PrismoAPI:
    """Backend API for the pywebview GUI"""

    def __init__(self):
        self.current_image_path = None
        self.default_wallpaper_path = None  # Track default wallpaper for reset
        self.custom_image_loaded = False  # Track if custom image was loaded
        self.light_mode = False
        self.colors = {}
        self.saturation = 50
        self.contrast = 50
        self.original_image = None
        self.adjusted_image_path = None
        self.config = {}
        self.active_templates = set()  # Track which templates are active
        self.wsl_distros = []  # Track WSL distros to apply

        # Load config
        self.load_config()

        # Load initial colors
        self.load_pywal_colors()

    def load_config(self):
        """Load config from file using centralized config manager"""
        try:
            # Use centralized config loading (initializes data directory if needed)
            self.config = load_config()
            # Initialize all templates as active by default
            self.active_templates = set(self.config.get("templates", {}).keys())
            # Initialize WSL distros from config
            self.wsl_distros = self.config.get("wsl", [])
            # Initialize light mode from config
            self.light_mode = self.config.get("light_mode", False)
            print(f"Loaded config with {len(self.active_templates)} templates")
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config = {}

    def reload_config(self):
        """Reload config from disk (for runtime config file changes)"""
        print("Reloading configuration...")
        self.load_config()
        return {
            "success": True,
            "template_count": len(self.config.get("templates", {})),
            "templates": list(self.config.get("templates", {}).keys())
        }

    def get_config_info(self):
        """Get config information for UI"""
        templates = {}

        # Add enabled templates
        for template_file in self.config.get("templates", {}).keys():
            # Convert filename to display name (e.g., "discord.prismo" -> "DISCORD", "example.prismo" -> "EXAMPLE")
            name = template_file.replace(".prismo", "").upper()
            templates[template_file] = {
                "name": name,
                "active": template_file in self.active_templates,
                "enabled": True
            }

        # Add disabled templates
        for template_file in self.config.get("disabled", {}).keys():
            # Convert filename to display name
            name = template_file.replace(".prismo", "").upper()
            templates[template_file] = {
                "name": name,
                "active": False,  # Disabled items are never active
                "enabled": False
            }

        # Always return WSL info (even if empty)
        wsl_info = {
            "distros": self.wsl_distros,
            "active": len(self.wsl_distros) > 0
        }

        return {
            "templates": templates,
            "wsl": wsl_info,
            "light_mode": self.light_mode
        }

    def toggle_template(self, template_file):
        """Toggle a template between enabled/disabled and persist to config"""
        import yaml

        # Check if template is currently in enabled section
        if template_file in self.config.get("templates", {}):
            # Move from templates to disabled
            output_path = self.config["templates"].pop(template_file)
            if "disabled" not in self.config:
                self.config["disabled"] = {}
            self.config["disabled"][template_file] = output_path
            self.active_templates.discard(template_file)
            is_enabled = False
        elif template_file in self.config.get("disabled", {}):
            # Move from disabled to templates
            output_path = self.config["disabled"].pop(template_file)
            if "templates" not in self.config:
                self.config["templates"] = {}
            self.config["templates"][template_file] = output_path
            self.active_templates.add(template_file)
            is_enabled = True
        else:
            # Template not found in config
            return False

        # Save config to file
        try:
            with open(config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            print(f"Updated config: moved {template_file} to {'templates' if is_enabled else 'disabled'}")
        except Exception as e:
            print(f"Error saving config: {e}")
            # Revert changes on error
            self.load_config()

        return is_enabled

    def get_wsl_distros(self):
        """Get current WSL distros list"""
        return self.wsl_distros

    def set_wsl_distros(self, distros):
        """Set WSL distros and persist to config"""
        import yaml

        self.wsl_distros = distros if isinstance(distros, list) else []
        self.config["wsl"] = self.wsl_distros

        # Save config to file
        try:
            with open(config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            print(f"Updated config: wsl = {self.wsl_distros}")
        except Exception as e:
            print(f"Error saving config: {e}")
            # Revert changes on error
            self.load_config()

        return self.wsl_distros

    def open_config_in_editor(self):
        """Open config file in default editor"""
        import subprocess
        import sys
        try:
            if sys.platform == 'win32':
                # Windows: use explorer.exe to open with default app or show "Open With" dialog
                # Ensure backslashes for Windows (support both slash types)
                windows_path = config_path.replace('/', '\\')
                subprocess.run(['explorer.exe', windows_path])
            elif sys.platform == 'darwin':
                # macOS: use open command
                subprocess.run(['open', config_path])
            else:
                # Linux: try xdg-open
                subprocess.run(['xdg-open', config_path])
            return {"success": True}
        except Exception as e:
            print(f"Error opening config: {e}")
            return {"success": False, "error": str(e)}

    def load_pywal_colors(self):
        """Load colors from pywal cache if it exists"""
        colors_path = home + "\\.cache\\wal\\colors.json"
        print(f"Looking for pywal colors at: {colors_path}")

        if path.isfile(colors_path):
            try:
                with open(colors_path, "r") as f:
                    data = loads(f.read())
                    self.colors = data.get("colors", {})
                    self.colors.update(data.get("special", {}))
                    print(f"Successfully loaded {len(self.colors)} colors from pywal cache")
            except Exception as e:
                print(f"Could not load colors from {colors_path}: {e}")
                self.colors = {}
        else:
            print(f"Pywal colors file not found at: {colors_path}")

        # Use gray defaults if no colors loaded
        if not self.colors:
            print("Using default gray colors")
            self.colors = {
                "background": "#000000",
                "foreground": "#808080",
                **{f"color{i}": "#808080" for i in range(16)}
            }

        return self.colors

    def get_colors(self):
        """Get current color palette"""
        return self.colors

    def load_current_wallpaper(self):
        """Load and return current Windows wallpaper as base64"""
        try:
            wallpaper_path = get_wallpaper()
            print(f"Registry wallpaper path: {wallpaper_path}")

            if wallpaper_path:
                if path.isfile(wallpaper_path):
                    print(f"Wallpaper file found, loading: {wallpaper_path}")
                    self.current_image_path = wallpaper_path
                    self.default_wallpaper_path = wallpaper_path  # Store default for reset
                    self.custom_image_loaded = False
                    return self.get_image_base64(wallpaper_path)
                else:
                    print(f"Wallpaper file not found at: {wallpaper_path}")
                    return None
            else:
                print("No wallpaper path returned from registry")
                return None
        except Exception as e:
            print(f"Error loading wallpaper: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_image_base64(self, image_path, max_width=850, max_height=300):
        """Convert image to base64 for display"""
        try:
            print(f"Converting image to base64: {image_path}")
            img = PILImage.open(image_path)
            print(f"Image opened successfully, size: {img.size}")

            # Calculate aspect ratio and resize
            img.thumbnail((max_width, max_height), PILImage.Resampling.LANCZOS)
            print(f"Image resized to: {img.size}")

            # Store original for adjustments
            self.original_image = PILImage.open(image_path)

            # Apply current adjustments
            img = self.apply_adjustments(img)

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()

            print(f"Image converted to base64 successfully ({len(img_str)} chars)")
            return f"data:image/png;base64,{img_str}"
        except Exception as e:
            print(f"Error converting image to base64: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def apply_adjustments(self, img):
        """Apply saturation and contrast adjustments to image"""
        saturation_factor = self.saturation / 50.0
        contrast_factor = self.contrast / 50.0

        # Apply saturation
        if saturation_factor != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(saturation_factor)

        # Apply contrast
        if contrast_factor != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast_factor)

        return img

    def select_image(self):
        """Open file dialog to select an image"""
        file_types = ('Image Files (*.png;*.jpg;*.jpeg;*.bmp;*.gif)', 'All files (*.*)')
        result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)

        if result and len(result) > 0:
            file_path = result[0]
            self.current_image_path = file_path
            self.custom_image_loaded = True  # Mark that custom image was loaded
            return self.get_image_base64(file_path)
        return None

    def reset_image(self):
        """Reset to default wallpaper"""
        if self.default_wallpaper_path and path.isfile(self.default_wallpaper_path):
            self.current_image_path = self.default_wallpaper_path
            self.custom_image_loaded = False
            return self.get_image_base64(self.default_wallpaper_path)
        return None

    def has_default_wallpaper(self):
        """Check if default wallpaper was loaded"""
        return self.default_wallpaper_path is not None and path.isfile(self.default_wallpaper_path)

    def is_custom_image_loaded(self):
        """Check if custom image is loaded"""
        return self.custom_image_loaded

    def update_saturation(self, value):
        """Update saturation value"""
        self.saturation = int(value)
        if self.current_image_path:
            return self.get_image_base64(self.current_image_path)
        return None

    def update_contrast(self, value):
        """Update contrast value"""
        self.contrast = int(value)
        if self.current_image_path:
            return self.get_image_base64(self.current_image_path)
        return None

    def toggle_light_mode(self, active):
        """Toggle light mode and persist to config"""
        import yaml

        self.light_mode = active
        self.config["light_mode"] = active

        # Save config to file
        try:
            with open(config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            print(f"Updated config: light_mode = {active}")
        except Exception as e:
            print(f"Error saving config: {e}")
            # Revert changes on error
            self.load_config()

        return active

    def adjust_and_save_image(self, image_path):
        """Adjust and save image with saturation and contrast"""
        try:
            img = PILImage.open(image_path)

            # Apply adjustments
            img = self.apply_adjustments(img)

            # Create output filename
            base_dir = path.dirname(image_path)
            base_name = path.basename(image_path)
            name_without_ext, ext = path.splitext(base_name)

            adjusted_filename = f"{name_without_ext}-s{self.saturation}c{self.contrast}{ext}"
            adjusted_path = path.join(base_dir, adjusted_filename)

            # Save adjusted image
            img.save(adjusted_path)

            return adjusted_path
        except Exception as e:
            print(f"Error adjusting image: {e}")
            return image_path

    def generate_colors(self):
        """Generate colors from current image"""
        if not self.current_image_path:
            return {"success": False, "error": "No image selected"}

        if not path.isfile(self.current_image_path):
            return {"success": False, "error": "Image file does not exist"}

        is_adjusted = (self.saturation != 50 or self.contrast != 50)

        try:
            # Adjust and save image
            adjusted_image_path = self.adjust_and_save_image(self.current_image_path)
            self.adjusted_image_path = adjusted_image_path if is_adjusted else None

            # Generate colors with selected templates and WSL
            apply_config = len(self.active_templates) > 0 or len(self.wsl_distros) > 0
            wsl_setting = self.wsl_distros if len(self.wsl_distros) > 0 else None
            template_results = gen_colors(
                adjusted_image_path,
                apply_config=apply_config,
                light_mode=self.light_mode,
                templates=self.active_templates if apply_config else None,
                wsl=wsl_setting if apply_config else None,
                config_dict=self.config
            )

            # Reload colors
            self.load_pywal_colors()

            # Clean up temporary file
            if is_adjusted and self.adjusted_image_path and path.isfile(self.adjusted_image_path):
                try:
                    remove(self.adjusted_image_path)
                    print(f"Cleaned up temporary file: {self.adjusted_image_path}")
                except Exception as e:
                    print(f"Warning: Could not delete temporary file: {e}")

            return {
                "success": True,
                "colors": self.colors,
                "template_results": template_results
            }
        except Exception as e:
            print(f"Error generating colors: {e}")
            return {"success": False, "error": str(e)}


HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #000000;
            color: #808080;
            overflow: hidden;
            height: 100vh;
        }

        .main-container {
            display: flex;
            height: 100vh;
            gap: 20px;
            padding: 20px;
        }

        /* Left side - Color Palette */
        .left-section {
            flex-shrink: 0;
            width: 280px;
        }

        .palette-panel {
            background: #000000;
            border: 1px solid #808080;
            padding: 20px;
            height: 100%;
        }

        .color-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            height: 100%;
        }

        .color-box {
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: 500;
            cursor: default;
            border: 1px solid rgba(128, 128, 128, 0.3);
        }

        /* Right side - Scrollable panels */
        .right-section {
            flex: 1;
            overflow-y: auto;
            overflow-x: hidden;
        }

        .panel {
            background: #000000;
            border: 1px solid #808080;
            padding: 20px;
            margin-bottom: 20px;
        }

        /* Image Preview Panel */
        .image-panel {
            position: relative;
        }

        .image-panel .btn-icon {
            position: absolute;
            top: 20px;
            right: 20px;
            z-index: 10;
        }

        .image-preview {
            width: 100%;
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            background: #000000;
        }

        .image-preview img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }

        .image-preview .placeholder {
            color: #808080;
            font-size: 14px;
        }

        .image-button {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 40px;
            height: 40px;
            background: rgba(51, 51, 51, 0.8);
            border: 1px solid #808080;
            color: #ffffff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            backdrop-filter: blur(4px);
        }

        .image-button:hover {
            background: rgba(85, 136, 221, 0.8);
            transform: scale(1.05);
        }

        .image-button:active {
            transform: scale(0.95);
        }

        /* Sliders */
        .slider-group {
            margin-bottom: 20px;
        }

        .slider-group:last-child {
            margin-bottom: 0;
        }

        .slider-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 14px;
            color: #808080;
        }

        .slider-value {
            font-weight: 600;
            font-family: 'Courier New', monospace;
        }

        input[type="range"] {
            width: 100%;
            height: 4px;
            background: #333333;
            outline: none;
            -webkit-appearance: none;
        }

        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 16px;
            height: 16px;
            background: #808080;
            cursor: pointer;
            border-radius: 50%;
        }

        input[type="range"]::-moz-range-thumb {
            width: 16px;
            height: 16px;
            background: #808080;
            cursor: pointer;
            border-radius: 50%;
            border: none;
        }

        /* Template Selection Panel */
        .template-panel {
            overflow-x: auto;
            overflow-y: hidden;
            white-space: nowrap;
            padding: 10px 20px;
        }

        .template-buttons {
            display: inline-flex;
            gap: 10px;
        }

        .btn-template {
            padding: 10px 20px;
            font-size: 12px;
            font-weight: 600;
            background: #1a1a1a;
            color: #808080;
            border: 1px solid #808080;
            cursor: pointer;
            transition: all 0.2s;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }

        .btn-template.active {
            background: #333333;
            color: #ffffff;
            border-color: #5588dd;
        }

        .btn-template.disabled {
            opacity: 0.5;
            font-style: italic;
        }

        .btn-template:hover {
            opacity: 0.8;
        }

        .btn-template:active {
            opacity: 0.6;
        }

        /* Controls */
        .controls {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .button-group {
            display: flex;
            gap: 15px;
            justify-content: center;
        }

        .btn-icon {
            padding: 12px 16px;
            font-size: 16px;
            background: #1a1a1a;
            color: #808080;
            border: 1px solid #808080;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .btn-icon:hover {
            opacity: 0.8;
            transform: translateY(-1px);
        }

        .btn-icon .icon {
            width: 16px;
            height: 16px;
            display: block;
            fill: currentColor;
        }

        .image-button .icon {
            width: 20px;
            height: 20px;
            display: block;
            fill: currentColor;
            pointer-events: none;
        }

        .image-button svg {
            width: 20px;
            height: 20px;
        }

        button {
            padding: 12px 32px;
            font-size: 14px;
            font-weight: 600;
            border: 1px solid #808080;
            cursor: pointer;
            transition: all 0.2s;
            letter-spacing: 0.5px;
        }

        button:hover {
            opacity: 0.8;
            transform: translateY(-1px);
        }

        button:active {
            opacity: 0.6;
            transform: translateY(0);
        }

        .btn-toggle {
            background: #1a1a1a;
            color: #808080;
            position: relative;
        }

        .btn-toggle.active {
            background: #333333;
            color: #ffffff;
            border-color: #5588dd;
        }

        .btn-toggle::before {
            content: '○';
            margin-right: 8px;
            font-size: 16px;
        }

        .btn-toggle.active::before {
            content: '●';
        }

        .btn-primary {
            background: #5588dd;
            color: #ffffff;
            border-color: #5588dd;
        }

        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .btn-primary.loading {
            position: relative;
            color: transparent;
        }

        .btn-primary.loading::after {
            content: '';
            position: absolute;
            width: 16px;
            height: 16px;
            top: 50%;
            left: 50%;
            margin-left: -8px;
            margin-top: -8px;
            border: 2px solid #ffffff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spinner 0.6s linear infinite;
        }

        @keyframes spinner {
            to { transform: rotate(360deg); }
        }

        .message {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 4px;
            font-size: 14px;
            z-index: 1000;
            display: none;
        }

        .message.success {
            background: #4CAF50;
            color: white;
        }

        .message.error {
            background: #f44336;
            color: white;
        }

        /* Results Popup */
        .results-popup {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #1a1a1a;
            border: 1px solid #333333;
            border-radius: 8px;
            padding: 20px;
            min-width: 400px;
            max-width: 600px;
            max-height: 70vh;
            overflow-y: auto;
            z-index: 2000;
            display: none;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        }

        .results-popup.show {
            display: block;
        }

        .results-popup-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1999;
            display: none;
        }

        .results-popup-overlay.show {
            display: block;
        }

        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #333333;
        }

        .results-title {
            font-size: 18px;
            font-weight: bold;
            color: #e0e0e0;
        }

        .results-close {
            background: none;
            border: none;
            color: #e0e0e0;
            font-size: 24px;
            cursor: pointer;
            padding: 0;
            width: 30px;
            height: 30px;
            line-height: 1;
            opacity: 0.7;
        }

        .results-close:hover {
            opacity: 1;
        }

        .results-category-header {
            font-size: 16px;
            font-weight: bold;
            color: #e0e0e0;
            margin-top: 15px;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 1px solid #444444;
        }

        .results-category-header:first-child {
            margin-top: 0;
        }

        .results-section {
            margin-bottom: 15px;
        }

        .results-section-title {
            font-weight: bold;
            margin-bottom: 8px;
            color: #e0e0e0;
            font-size: 14px;
        }

        .results-section-title.success {
            color: #4CAF50;
        }

        .results-section-title.error {
            color: #f44336;
        }

        .results-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .results-item {
            padding: 8px 12px;
            margin-bottom: 4px;
            border-radius: 4px;
            background: rgba(255, 255, 255, 0.05);
            font-size: 13px;
        }

        .results-item.success {
            border-left: 3px solid #4CAF50;
        }

        .results-item.failed {
            border-left: 3px solid #f44336;
        }

        .results-item-name {
            font-weight: bold;
            color: #e0e0e0;
        }

        .results-item-error {
            color: #999999;
            font-size: 12px;
            margin-top: 4px;
        }

        .results-summary {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #333333;
            font-size: 13px;
            color: #999999;
        }

        /* WSL Modal */
        .wsl-modal {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #1a1a1a;
            border: 1px solid #333333;
            border-radius: 8px;
            padding: 0;
            min-width: 500px;
            max-width: 600px;
            max-height: 70vh;
            overflow: hidden;
            z-index: 2000;
            display: none;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        }

        .wsl-modal.show {
            display: flex;
            flex-direction: column;
        }

        .wsl-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            border-bottom: 1px solid #333333;
            flex-shrink: 0;
        }

        .wsl-modal-title {
            font-size: 18px;
            font-weight: bold;
            color: #e0e0e0;
        }

        .wsl-modal-body {
            padding: 20px;
            overflow-y: auto;
            flex: 1;
        }

        .wsl-modal-description {
            margin-bottom: 15px;
            color: #999999;
            font-size: 14px;
        }

        .wsl-distro-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 15px;
        }

        .wsl-distro-row {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .wsl-distro-input {
            flex: 1;
            padding: 10px;
            background: #0a0a0a;
            border: 1px solid #333333;
            color: #e0e0e0;
            font-size: 14px;
            outline: none;
        }

        .wsl-distro-input:focus {
            border-color: #5588dd;
        }

        .wsl-delete-btn {
            width: 36px;
            height: 36px;
            background: #333333;
            border: 1px solid #555555;
            color: #e0e0e0;
            font-size: 24px;
            line-height: 1;
            cursor: pointer;
            padding: 0;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .wsl-delete-btn:hover {
            background: #f44336;
            border-color: #f44336;
            color: #ffffff;
        }

        .wsl-add-btn {
            width: 100%;
            padding: 10px;
            background: #333333;
            border: 1px solid #555555;
            color: #e0e0e0;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .wsl-add-btn:hover {
            background: #444444;
        }

        .wsl-modal-footer {
            display: flex;
            gap: 10px;
            padding: 20px;
            border-top: 1px solid #333333;
            justify-content: flex-end;
            flex-shrink: 0;
        }

        .btn-cancel {
            padding: 10px 24px;
            background: #333333;
            border: 1px solid #555555;
            color: #e0e0e0;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-cancel:hover {
            background: #444444;
        }

        .btn-confirm {
            padding: 10px 24px;
            background: #5588dd;
            border: 1px solid #5588dd;
            color: #ffffff;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-confirm:hover {
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <!-- SVG Icon Definitions -->
    <svg style="display: none;" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
        <defs>
            <!-- Settings/Cog Icon -->
            <symbol id="icon-cog" viewBox="0 0 512 512">
                <path fill="currentColor" d="M495.9 166.6c3.2 8.7 .5 18.4-6.4 24.6l-43.3 39.4c1.1 8.3 1.7 16.8 1.7 25.4s-.6 17.1-1.7 25.4l43.3 39.4c6.9 6.2 9.6 15.9 6.4 24.6c-4.4 11.9-9.7 23.3-15.8 34.3l-4.7 8.1c-6.6 11-14 21.4-22.1 31.2c-5.9 7.2-15.7 9.6-24.5 6.8l-55.7-17.7c-13.4 10.3-28.2 18.9-44 25.4l-12.5 57.1c-2 9.1-9 16.3-18.2 17.8c-13.8 2.3-28 3.5-42.5 3.5s-28.7-1.2-42.5-3.5c-9.2-1.5-16.2-8.7-18.2-17.8l-12.5-57.1c-15.8-6.5-30.6-15.1-44-25.4L83.1 425.9c-8.8 2.8-18.6 .3-24.5-6.8c-8.1-9.8-15.5-20.2-22.1-31.2l-4.7-8.1c-6.1-11-11.4-22.4-15.8-34.3c-3.2-8.7-.5-18.4 6.4-24.6l43.3-39.4C64.6 273.1 64 264.6 64 256s.6-17.1 1.7-25.4L22.4 191.2c-6.9-6.2-9.6-15.9-6.4-24.6c4.4-11.9 9.7-23.3 15.8-34.3l4.7-8.1c6.6-11 14-21.4 22.1-31.2c5.9-7.2 15.7-9.6 24.5-6.8l55.7 17.7c13.4-10.3 28.2-18.9 44-25.4l12.5-57.1c2-9.1 9-16.3 18.2-17.8C227.3 1.2 241.5 0 256 0s28.7 1.2 42.5 3.5c9.2 1.5 16.2 8.7 18.2 17.8l12.5 57.1c15.8 6.5 30.6 15.1 44 25.4l55.7-17.7c8.8-2.8 18.6-.3 24.5 6.8c8.1 9.8 15.5 20.2 22.1 31.2l4.7 8.1c6.1 11 11.4 22.4 15.8 34.3zM256 336a80 80 0 1 0 0-160 80 80 0 1 0 0 160z"/>
            </symbol>
            <!-- Image Icon -->
            <symbol id="icon-image" viewBox="0 0 512 512">
                <path fill="currentColor" d="M0 96C0 60.7 28.7 32 64 32H448c35.3 0 64 28.7 64 64V416c0 35.3-28.7 64-64 64H64c-35.3 0-64-28.7-64-64V96zM323.8 202.5c-4.5-6.6-11.9-10.5-19.8-10.5s-15.4 3.9-19.8 10.5l-87 127.6L170.7 297c-4.6-5.7-11.5-9-18.7-9s-14.2 3.3-18.7 9l-64 80c-5.8 7.2-6.9 17.1-2.9 25.4s12.4 13.6 21.6 13.6h96 32H424c8.9 0 17.1-4.9 21.2-12.8s3.6-17.4-1.4-24.7l-120-176zM112 192a48 48 0 1 0 0-96 48 48 0 1 0 0 96z"/>
            </symbol>
            <!-- Undo Icon -->
            <symbol id="icon-undo" viewBox="0 0 512 512">
                <path fill="currentColor" d="M48.5 224H40c-13.3 0-24-10.7-24-24V72c0-9.7 5.8-18.5 14.8-22.2s19.3-1.7 26.2 5.2L98.6 96.6c87.6-86.5 228.7-86.2 315.8 1c87.5 87.5 87.5 229.3 0 316.8s-229.3 87.5-316.8 0c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0c62.5 62.5 163.8 62.5 226.3 0s62.5-163.8 0-226.3c-62.2-62.2-162.7-62.5-225.3-1L185 183c6.9 6.9 8.9 17.2 5.2 26.2s-12.5 14.8-22.2 14.8H48.5z"/>
            </symbol>
        </defs>
    </svg>

    <div class="main-container">
        <!-- Left Section - Color Palette -->
        <div class="left-section">
            <div class="palette-panel">
                <div class="color-grid" id="colorGrid"></div>
            </div>
        </div>

        <!-- Right Section - Scrollable Panels -->
        <div class="right-section">
            <!-- Image Preview -->
            <div class="panel image-panel">
                <button class="btn-icon" id="imageButton" onclick="handleImageButton()" title="Select Image">
                    <svg class="icon"><use xlink:href="#icon-image" href="#icon-image"/></svg>
                </button>
                <div class="image-preview" id="imagePreview">
                    <div class="placeholder">Loading...</div>
                </div>
            </div>

            <!-- Adjustments -->
            <div class="panel">
                <div class="slider-group">
                    <div class="slider-label">
                        <span>Saturation</span>
                        <span class="slider-value" id="saturationValue">50</span>
                    </div>
                    <input type="range" id="saturationSlider" min="0" max="100" value="50" step="1">
                </div>

                <div class="slider-group">
                    <div class="slider-label">
                        <span>Contrast</span>
                        <span class="slider-value" id="contrastValue">50</span>
                    </div>
                    <input type="range" id="contrastSlider" min="0" max="100" value="50" step="1">
                </div>
            </div>

            <!-- Template Selection -->
            <div class="panel template-panel">
                <div class="template-buttons" id="templateButtons">
                    <!-- Template buttons will be dynamically added here -->
                </div>
            </div>

            <!-- Controls -->
            <div class="panel">
                <div class="controls">
                    <div class="button-group">
                        <button class="btn-icon" onclick="openSettings()" title="Settings">
                            <svg class="icon"><use xlink:href="#icon-cog" href="#icon-cog"/></svg>
                        </button>
                        <button class="btn-toggle" id="lightModeButton" onclick="toggleLightMode()">LIGHT MODE</button>
                        <button class="btn-primary" id="generateBtn" onclick="generateColors()">GENERATE COLORS</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="message" id="message"></div>

    <!-- Results Popup -->
    <div class="results-popup-overlay" id="resultsOverlay" onclick="closeResultsPopup()"></div>
    <div class="results-popup" id="resultsPopup">
        <div class="results-header">
            <div class="results-title">Template Application Results</div>
            <button class="results-close" onclick="closeResultsPopup()">&times;</button>
        </div>
        <div id="resultsContent"></div>
    </div>

    <!-- WSL Modal -->
    <div class="results-popup-overlay" id="wslOverlay" onclick="closeWSLModal()"></div>
    <div class="wsl-modal" id="wslModal">
        <div class="wsl-modal-header">
            <div class="wsl-modal-title">Configure WSL Distros</div>
            <button class="results-close" onclick="closeWSLModal()">&times;</button>
        </div>
        <div class="wsl-modal-body">
            <p class="wsl-modal-description">Add the WSL distributions you want to theme:</p>
            <div id="wslDistroList" class="wsl-distro-list">
                <!-- Distro rows will be added here dynamically -->
            </div>
            <button class="wsl-add-btn" onclick="addWSLDistroRow('')">+ Add Distro</button>
        </div>
        <div class="wsl-modal-footer">
            <button class="btn-cancel" onclick="closeWSLModal()">Cancel</button>
            <button class="btn-confirm" onclick="saveWSLDistros()">Confirm</button>
        </div>
    </div>

    <script>
        let saturationSlider = document.getElementById('saturationSlider');
        let contrastSlider = document.getElementById('contrastSlider');
        let saturationValue = document.getElementById('saturationValue');
        let contrastValue = document.getElementById('contrastValue');
        let imagePreview = document.getElementById('imagePreview');
        let colorGrid = document.getElementById('colorGrid');
        let lightModeButton = document.getElementById('lightModeButton');
        let imageButton = document.getElementById('imageButton');
        let isLightMode = false;
        let currentColors = {};

        // Initialize - wait for pywebview to be ready
        window.addEventListener('pywebviewready', async function() {
            console.log('pywebview is ready, initializing...');
            await loadColors();
            await loadWallpaper();
            await updateImageButton();
            await loadTemplateButtons();
        });

        // Load colors from backend
        async function loadColors() {
            try {
                console.log('Loading colors from backend...');
                const colors = await pywebview.api.get_colors();
                console.log('Colors loaded:', colors);
                currentColors = colors;
                updateColorGrid(colors);
                updateTheme(colors);
            } catch (e) {
                console.error('Error loading colors:', e);
            }
        }

        // Load current wallpaper
        async function loadWallpaper() {
            try {
                console.log('Loading wallpaper from backend...');
                const imageData = await pywebview.api.load_current_wallpaper();
                console.log('Wallpaper loaded, data length:', imageData ? imageData.length : 'null');
                if (imageData) {
                    imagePreview.innerHTML = '<img src="' + imageData + '">';
                } else {
                    console.log('No wallpaper data returned');
                    imagePreview.innerHTML = '<div class="placeholder">No wallpaper found</div>';
                }
            } catch (e) {
                console.error('Error loading wallpaper:', e);
                imagePreview.innerHTML = '<div class="placeholder">Error loading wallpaper: ' + e.message + '</div>';
            }
        }

        // Update color grid with 2-column layout
        function updateColorGrid(colors) {
            // Column 1: background, color0, color2, color4, color6, color8, color10, color12, color14
            // Column 2: foreground, color1, color3, color5, color7, color9, color11, color13, color15
            const column1 = ['background', 'color0', 'color2', 'color4', 'color6', 'color8', 'color10', 'color12', 'color14'];
            const column2 = ['foreground', 'color1', 'color3', 'color5', 'color7', 'color9', 'color11', 'color13', 'color15'];

            colorGrid.innerHTML = '';

            // Interleave columns for grid layout
            const maxLength = Math.max(column1.length, column2.length);
            for (let i = 0; i < maxLength; i++) {
                // Add column 1 item
                if (i < column1.length) {
                    const name = column1[i];
                    const color = colors[name] || '#808080';
                    colorGrid.appendChild(createColorBox(name, color));
                }

                // Add column 2 item
                if (i < column2.length) {
                    const name = column2[i];
                    const color = colors[name] || '#808080';
                    colorGrid.appendChild(createColorBox(name, color));
                }
            }
        }

        function createColorBox(name, color) {
            const box = document.createElement('div');
            box.className = 'color-box';
            box.style.backgroundColor = color;
            box.textContent = name;

            // Calculate contrast color for text
            const rgb = parseInt(color.slice(1), 16);
            const r = (rgb >> 16) & 0xff;
            const g = (rgb >> 8) & 0xff;
            const b = rgb & 0xff;
            const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
            box.style.color = luminance > 0.5 ? '#000000' : '#ffffff';

            return box;
        }

        // Update theme colors
        function updateTheme(colors) {
            const bg = colors.background || '#000000';
            const fg = colors.foreground || '#808080';
            const accent = colors.color1 || '#5588dd';

            document.body.style.backgroundColor = bg;
            document.body.style.color = fg;

            // Update panels
            document.querySelectorAll('.panel, .palette-panel').forEach(panel => {
                panel.style.backgroundColor = bg;
                panel.style.borderColor = fg;
            });

            document.querySelectorAll('.slider-label').forEach(el => {
                el.style.color = fg;
            });

            document.querySelectorAll('.image-preview').forEach(el => {
                el.style.backgroundColor = bg;
            });

            // Update slider thumbs to use foreground color
            updateSliderThumbColor(fg);

            // Update slider track background
            document.querySelectorAll('input[type="range"]').forEach(slider => {
                slider.style.background = accent;
            });

            // Update button primary color
            document.querySelector('.btn-primary').style.backgroundColor = accent;
            document.querySelector('.btn-primary').style.borderColor = accent;

            // Update file picker button (image button)
            const imageButton = document.getElementById('imageButton');
            if (imageButton) {
                imageButton.style.backgroundColor = accent;
                imageButton.style.borderColor = accent;
                imageButton.style.color = fg;
            }

            // Update settings button
            const settingsButtons = document.querySelectorAll('.btn-icon');
            settingsButtons.forEach(btn => {
                btn.style.backgroundColor = accent;
                btn.style.borderColor = accent;
                btn.style.color = fg;
            });

            // Update light mode toggle button
            const lightModeButton = document.getElementById('lightModeButton');
            if (lightModeButton) {
                lightModeButton.style.backgroundColor = accent;
                lightModeButton.style.borderColor = accent;
                lightModeButton.style.color = '#ffffff';
            }

            // Update template toggle buttons (active and inactive)
            const templateButtons = document.querySelectorAll('.btn-template');
            templateButtons.forEach(btn => {
                if (btn.classList.contains('active')) {
                    btn.style.backgroundColor = accent;
                    btn.style.borderColor = accent;
                    btn.style.color = '#ffffff';
                } else {
                    btn.style.backgroundColor = bg;
                    btn.style.borderColor = fg;
                    btn.style.color = fg;
                }
            });

            // Update results popup theme
            const popup = document.getElementById('resultsPopup');
            if (popup) {
                popup.style.backgroundColor = bg;
                popup.style.borderColor = fg;

                // Update popup text colors
                const title = popup.querySelector('.results-title');
                const closeBtn = popup.querySelector('.results-close');
                if (title) title.style.color = fg;
                if (closeBtn) closeBtn.style.color = fg;

                popup.querySelectorAll('.results-section-title:not(.success):not(.error)').forEach(el => {
                    el.style.color = fg;
                });

                popup.querySelectorAll('.results-item-name').forEach(el => {
                    el.style.color = fg;
                });

                popup.querySelectorAll('.results-header, .results-summary').forEach(el => {
                    el.style.borderColor = fg;
                });
            }

            // Update WSL modal theme
            const wslModal = document.getElementById('wslModal');
            if (wslModal) {
                wslModal.style.backgroundColor = bg;
                wslModal.style.borderColor = fg;

                // Update modal header
                const modalTitle = wslModal.querySelector('.wsl-modal-title');
                const modalClose = wslModal.querySelector('.results-close');
                if (modalTitle) modalTitle.style.color = fg;
                if (modalClose) modalClose.style.color = fg;

                wslModal.querySelectorAll('.wsl-modal-header, .wsl-modal-footer').forEach(el => {
                    el.style.borderColor = fg;
                });

                // Update description text
                wslModal.querySelectorAll('.wsl-modal-description').forEach(el => {
                    el.style.color = fg;
                });

                // Update inputs
                wslModal.querySelectorAll('.wsl-distro-input').forEach(input => {
                    input.style.backgroundColor = bg;
                    input.style.borderColor = fg;
                    input.style.color = fg;
                });

                // Update confirm button
                const confirmBtn = wslModal.querySelector('.btn-confirm');
                if (confirmBtn) {
                    confirmBtn.style.backgroundColor = accent;
                    confirmBtn.style.borderColor = accent;
                }
            }
        }

        // Update slider thumb color dynamically
        function updateSliderThumbColor(color) {
            // Create or update style element for slider thumbs
            let styleId = 'slider-thumb-style';
            let styleEl = document.getElementById(styleId);

            if (!styleEl) {
                styleEl = document.createElement('style');
                styleEl.id = styleId;
                document.head.appendChild(styleEl);
            }

            styleEl.textContent = `
                input[type="range"]::-webkit-slider-thumb {
                    background: ${color} !important;
                }
                input[type="range"]::-moz-range-thumb {
                    background: ${color} !important;
                }
            `;
        }

        // Update image button based on state
        async function updateImageButton() {
            try {
                const hasDefault = await pywebview.api.has_default_wallpaper();
                const isCustom = await pywebview.api.is_custom_image_loaded();

                if (isCustom && hasDefault) {
                    // Show reset icon
                    imageButton.innerHTML = '<svg class="icon"><use xlink:href="#icon-undo" href="#icon-undo"/></svg>';
                    imageButton.title = 'Reset to Default Wallpaper';
                } else {
                    // Show file selector icon
                    imageButton.innerHTML = '<svg class="icon"><use xlink:href="#icon-image" href="#icon-image"/></svg>';
                    imageButton.title = 'Select Image';
                }
            } catch (e) {
                console.error('Error updating image button:', e);
            }
        }

        // Handle image button click
        async function handleImageButton() {
            try {
                const isCustom = await pywebview.api.is_custom_image_loaded();
                const hasDefault = await pywebview.api.has_default_wallpaper();

                if (isCustom && hasDefault) {
                    // Reset to default
                    const imageData = await pywebview.api.reset_image();
                    if (imageData) {
                        imagePreview.innerHTML = '<img src="' + imageData + '">';
                        await updateImageButton();
                    }
                } else {
                    // Select new image
                    const imageData = await pywebview.api.select_image();
                    if (imageData) {
                        imagePreview.innerHTML = '<img src="' + imageData + '">';
                        await updateImageButton();
                    }
                }
            } catch (e) {
                console.error('Error handling image button:', e);
            }
        }

        // Load template buttons
        async function loadTemplateButtons() {
            try {
                const configInfo = await pywebview.api.get_config_info();
                const templateButtons = document.getElementById('templateButtons');
                templateButtons.innerHTML = '';

                // Add template buttons
                for (const [templateFile, templateInfo] of Object.entries(configInfo.templates)) {
                    const button = document.createElement('button');
                    let className = 'btn-template';

                    // Add active class if enabled and active
                    if (templateInfo.enabled && templateInfo.active) {
                        className += ' active';
                    }

                    // Add disabled class if not enabled
                    if (!templateInfo.enabled) {
                        className += ' disabled';
                    }

                    button.className = className;
                    button.textContent = templateInfo.name;
                    button.onclick = () => toggleTemplate(templateFile, button, templateInfo.enabled);
                    templateButtons.appendChild(button);
                }

                // Always add WSL button
                if (configInfo.wsl) {
                    const button = document.createElement('button');
                    button.className = 'btn-template' + (configInfo.wsl.active ? ' active' : '');
                    const distroCount = configInfo.wsl.distros.length;
                    button.textContent = distroCount > 0
                        ? `WSL (${distroCount} ${distroCount === 1 ? 'DISTRO' : 'DISTROS'})`
                        : 'WSL (NONE)';
                    button.onclick = () => openWSLModal();
                    templateButtons.appendChild(button);
                }

                // Initialize light mode state from config
                isLightMode = configInfo.light_mode || false;
                if (isLightMode) {
                    lightModeButton.classList.add('active');
                } else {
                    lightModeButton.classList.remove('active');
                }

                // Apply theme to newly loaded buttons
                if (currentColors) {
                    updateTheme(currentColors);
                }
            } catch (e) {
                console.error('Error loading template buttons:', e);
            }
        }

        // Toggle template
        async function toggleTemplate(templateFile, button, wasEnabled) {
            try {
                const isNowEnabled = await pywebview.api.toggle_template(templateFile);

                // Reload all buttons to reflect new state from config
                await loadTemplateButtons();

                // Show feedback message
                if (isNowEnabled) {
                    showMessage(`${templateFile.replace('.prismo', '').toUpperCase()} enabled`, 'success');
                } else {
                    showMessage(`${templateFile.replace('.prismo', '').toUpperCase()} disabled`, 'success');
                }
            } catch (e) {
                console.error('Error toggling template:', e);
                showMessage('Error toggling template', 'error');
            }
        }

        // Open WSL modal
        async function openWSLModal() {
            try {
                const distros = await pywebview.api.get_wsl_distros();
                const modal = document.getElementById('wslModal');
                const overlay = document.getElementById('wslOverlay');
                const distroList = document.getElementById('wslDistroList');

                // Clear existing rows
                distroList.innerHTML = '';

                // Add rows for existing distros
                if (distros && distros.length > 0) {
                    distros.forEach(distro => {
                        addWSLDistroRow(distro);
                    });
                } else {
                    // Add one empty row to start
                    addWSLDistroRow('');
                }

                // Show modal
                modal.classList.add('show');
                overlay.classList.add('show');

                // Focus first input
                const firstInput = distroList.querySelector('input');
                if (firstInput) firstInput.focus();
            } catch (e) {
                console.error('Error opening WSL modal:', e);
            }
        }

        // Close WSL modal
        function closeWSLModal() {
            const modal = document.getElementById('wslModal');
            const overlay = document.getElementById('wslOverlay');
            modal.classList.remove('show');
            overlay.classList.remove('show');
        }

        // Add distro row
        function addWSLDistroRow(value = '') {
            const distroList = document.getElementById('wslDistroList');
            const row = document.createElement('div');
            row.className = 'wsl-distro-row';

            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'wsl-distro-input';
            input.placeholder = 'Distro name (e.g., Ubuntu)';
            input.value = value;

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'wsl-delete-btn';
            deleteBtn.textContent = '×';
            deleteBtn.onclick = () => {
                row.remove();
                // If no rows left, add an empty one
                if (distroList.children.length === 0) {
                    addWSLDistroRow('');
                }
            };

            row.appendChild(input);
            row.appendChild(deleteBtn);
            distroList.appendChild(row);
        }

        // Save WSL distros
        async function saveWSLDistros() {
            try {
                const distroList = document.getElementById('wslDistroList');
                const inputs = distroList.querySelectorAll('.wsl-distro-input');
                const distros = [];

                // Collect non-empty distro names
                inputs.forEach(input => {
                    const value = input.value.trim();
                    if (value) {
                        distros.push(value);
                    }
                });

                // Save to backend
                await pywebview.api.set_wsl_distros(distros);

                // Reload template buttons to reflect changes
                await loadTemplateButtons();

                // Close modal
                closeWSLModal();

                // Show success message
                showMessage(`WSL distros updated: ${distros.length > 0 ? distros.join(', ') : 'none'}`, 'success');
            } catch (e) {
                console.error('Error saving WSL distros:', e);
                showMessage('Error saving WSL distros', 'error');
            }
        }

        // Toggle light mode
        async function toggleLightMode() {
            isLightMode = !isLightMode;

            try {
                await pywebview.api.toggle_light_mode(isLightMode);

                if (isLightMode) {
                    lightModeButton.classList.add('active');
                    showMessage('Light mode enabled', 'success');
                } else {
                    lightModeButton.classList.remove('active');
                    showMessage('Light mode disabled', 'success');
                }
            } catch (e) {
                console.error('Error toggling light mode:', e);
                showMessage('Error toggling light mode', 'error');
                // Revert on error
                isLightMode = !isLightMode;
            }
        }

        // Open settings
        async function openSettings() {
            try {
                const result = await pywebview.api.open_config_in_editor();
                if (result.success) {
                    showMessage('Opening config file in editor...', 'success');
                } else {
                    showMessage('Error opening config: ' + result.error, 'error');
                }
            } catch (e) {
                console.error('Error opening settings:', e);
                showMessage('Error opening config file', 'error');
            }
        }

        // Saturation slider
        saturationSlider.addEventListener('input', async function() {
            saturationValue.textContent = this.value;
            const imageData = await pywebview.api.update_saturation(this.value);
            if (imageData) {
                imagePreview.innerHTML = '<img src="' + imageData + '">';
            }
        });

        // Contrast slider
        contrastSlider.addEventListener('input', async function() {
            contrastValue.textContent = this.value;
            const imageData = await pywebview.api.update_contrast(this.value);
            if (imageData) {
                imagePreview.innerHTML = '<img src="' + imageData + '">';
            }
        });

        // Generate colors
        async function generateColors() {
            const generateBtn = document.getElementById('generateBtn');

            try {
                // Set loading state
                generateBtn.classList.add('loading');
                generateBtn.disabled = true;

                const result = await pywebview.api.generate_colors();

                // Clear loading state
                generateBtn.classList.remove('loading');
                generateBtn.disabled = false;

                if (result.success) {
                    currentColors = result.colors;
                    updateColorGrid(result.colors);
                    updateTheme(result.colors);

                    // Show results popup if templates or WSL were applied
                    const hasTemplateResults = result.template_results &&
                        (result.template_results.succeeded.length > 0 || result.template_results.failed.length > 0);
                    const hasWSLResults = result.template_results &&
                        (result.template_results.wsl_succeeded.length > 0 || result.template_results.wsl_failed.length > 0);

                    if (hasTemplateResults || hasWSLResults) {
                        showResultsPopup(result.template_results);
                    } else {
                        showMessage('Colors generated successfully!', 'success');
                    }
                } else {
                    showMessage(result.error || 'Failed to generate colors', 'error');
                }
            } catch (e) {
                console.error('Error generating colors:', e);
                showMessage('Error generating colors', 'error');

                // Clear loading state on error
                generateBtn.classList.remove('loading');
                generateBtn.disabled = false;
            }
        }

        // Show results popup
        function showResultsPopup(results) {
            const popup = document.getElementById('resultsPopup');
            const overlay = document.getElementById('resultsOverlay');
            const content = document.getElementById('resultsContent');

            let html = '';

            // Templates section header
            const hasTemplateResults = (results.succeeded && results.succeeded.length > 0) || (results.failed && results.failed.length > 0);
            if (hasTemplateResults) {
                html += '<div class="results-category-header">Templates</div>';
            }

            // Template success section
            if (results.succeeded && results.succeeded.length > 0) {
                html += '<div class="results-section">';
                html += '<div class="results-section-title success">✓ Successfully Applied (' + results.succeeded.length + ')</div>';
                html += '<ul class="results-list">';
                results.succeeded.forEach(template => {
                    html += '<li class="results-item success">';
                    html += '<div class="results-item-name">' + template + '</div>';
                    html += '</li>';
                });
                html += '</ul>';
                html += '</div>';
            }

            // Template failed section
            if (results.failed && results.failed.length > 0) {
                html += '<div class="results-section">';
                html += '<div class="results-section-title error">✗ Failed (' + results.failed.length + ')</div>';
                html += '<ul class="results-list">';
                results.failed.forEach(item => {
                    html += '<li class="results-item failed">';
                    html += '<div class="results-item-name">' + item.name + '</div>';
                    html += '<div class="results-item-error">' + item.error + '</div>';
                    html += '</li>';
                });
                html += '</ul>';
                html += '</div>';
            }

            // WSL section header
            const hasWSLResults = (results.wsl_succeeded && results.wsl_succeeded.length > 0) || (results.wsl_failed && results.wsl_failed.length > 0);
            if (hasWSLResults) {
                html += '<div class="results-category-header">WSL Distros</div>';
            }

            // WSL success section
            if (results.wsl_succeeded && results.wsl_succeeded.length > 0) {
                html += '<div class="results-section">';
                html += '<div class="results-section-title success">✓ Successfully Applied (' + results.wsl_succeeded.length + ')</div>';
                html += '<ul class="results-list">';
                results.wsl_succeeded.forEach(distro => {
                    html += '<li class="results-item success">';
                    html += '<div class="results-item-name">' + distro + '</div>';
                    html += '</li>';
                });
                html += '</ul>';
                html += '</div>';
            }

            // WSL failed section
            if (results.wsl_failed && results.wsl_failed.length > 0) {
                html += '<div class="results-section">';
                html += '<div class="results-section-title error">✗ Failed (' + results.wsl_failed.length + ')</div>';
                html += '<ul class="results-list">';
                results.wsl_failed.forEach(item => {
                    html += '<li class="results-item failed">';
                    html += '<div class="results-item-name">' + item.name + '</div>';
                    html += '<div class="results-item-error">' + item.error + '</div>';
                    html += '</li>';
                });
                html += '</ul>';
                html += '</div>';
            }

            // Summary
            const templateTotal = (results.succeeded ? results.succeeded.length : 0) + (results.failed ? results.failed.length : 0);
            const templateSuccess = results.succeeded ? results.succeeded.length : 0;
            const wslTotal = (results.wsl_succeeded ? results.wsl_succeeded.length : 0) + (results.wsl_failed ? results.wsl_failed.length : 0);
            const wslSuccess = results.wsl_succeeded ? results.wsl_succeeded.length : 0;

            html += '<div class="results-summary">';
            if (hasTemplateResults) {
                html += 'Templates: ' + templateSuccess + ' of ' + templateTotal + ' applied successfully';
            }
            if (hasTemplateResults && hasWSLResults) {
                html += '<br>';
            }
            if (hasWSLResults) {
                html += 'WSL Distros: ' + wslSuccess + ' of ' + wslTotal + ' applied successfully';
            }
            html += '</div>';

            content.innerHTML = html;
            popup.classList.add('show');
            overlay.classList.add('show');
        }

        // Close results popup
        function closeResultsPopup() {
            const popup = document.getElementById('resultsPopup');
            const overlay = document.getElementById('resultsOverlay');
            popup.classList.remove('show');
            overlay.classList.remove('show');
        }

        // Show message
        function showMessage(text, type) {
            const message = document.getElementById('message');
            message.textContent = text;
            message.className = 'message ' + type;
            message.style.display = 'block';

            setTimeout(() => {
                message.style.display = 'none';
            }, 3000);
        }
    </script>
</body>
</html>
"""


def main():
    api = PrismoAPI()
    window = webview.create_window(
        'Prismo - Pywal Color Generator',
        html=HTML,
        js_api=api,
        width=900,
        height=900,
        resizable=True
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
