import webview
from PIL import Image as PILImage, ImageEnhance
from json import loads, dumps
from os import path, remove
import base64
import io
from main import gen_colors, get_wallpaper, home, config_path


class PrismaAPI:
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
        self.wsl_enabled = False  # Track if WSL is enabled

        # Load config
        self.load_config()

        # Load initial colors
        self.load_pywal_colors()

    def load_config(self):
        """Load config from file"""
        try:
            if path.isfile(config_path):
                with open(config_path, "r") as f:
                    self.config = loads(f.read())
                    # Initialize all templates as active by default
                    self.active_templates = set(self.config.get("templates", {}).keys())
                    # Initialize WSL as enabled if defined
                    self.wsl_enabled = bool(self.config.get("wsl", "").strip())
                print(f"Loaded config with {len(self.active_templates)} templates")
            else:
                print(f"Config file not found at {config_path}")
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config = {}

    def get_config_info(self):
        """Get config information for UI"""
        templates = {}
        for template_file in self.config.get("templates", {}).keys():
            # Convert filename to display name (e.g., "discord.txt" -> "DISCORD")
            name = template_file.replace(".txt", "").upper()
            templates[template_file] = {
                "name": name,
                "active": template_file in self.active_templates
            }

        wsl_info = None
        if self.config.get("wsl", "").strip():
            wsl_info = {
                "name": self.config["wsl"],
                "active": self.wsl_enabled
            }

        return {
            "templates": templates,
            "wsl": wsl_info
        }

    def toggle_template(self, template_file):
        """Toggle a template on/off"""
        if template_file in self.active_templates:
            self.active_templates.remove(template_file)
        else:
            self.active_templates.add(template_file)
        return template_file in self.active_templates

    def toggle_wsl(self):
        """Toggle WSL on/off"""
        self.wsl_enabled = not self.wsl_enabled
        return self.wsl_enabled

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
        """Toggle light mode"""
        self.light_mode = active

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
            apply_config = len(self.active_templates) > 0 or self.wsl_enabled
            wsl_setting = self.config.get("wsl") if self.wsl_enabled else False
            gen_colors(
                adjusted_image_path,
                apply_config=apply_config,
                light_mode=self.light_mode,
                templates=self.active_templates if apply_config else None,
                wsl=wsl_setting if apply_config else False
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

            return {"success": True, "colors": self.colors}
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
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
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
    </style>
</head>
<body>
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
                <button class="image-button" id="imageButton" onclick="handleImageButton()" title="Select Image">📁</button>
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
                        <button class="btn-icon" onclick="openSettings()" title="Settings">⚙️</button>
                        <button class="btn-toggle" id="lightModeButton" onclick="toggleLightMode()">LIGHT MODE</button>
                        <button class="btn-primary" onclick="generateColors()">GENERATE COLORS</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="message" id="message"></div>

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
            const accent = colors.color4 || '#5588dd';

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

            // Update button primary color
            document.querySelector('.btn-primary').style.backgroundColor = accent;
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
                    imageButton.textContent = '↺';
                    imageButton.title = 'Reset to Default Wallpaper';
                } else {
                    // Show file selector icon
                    imageButton.textContent = '📁';
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
                    button.className = 'btn-template' + (templateInfo.active ? ' active' : '');
                    button.textContent = templateInfo.name;
                    button.onclick = () => toggleTemplate(templateFile, button);
                    templateButtons.appendChild(button);
                }

                // Add WSL button if configured
                if (configInfo.wsl) {
                    const button = document.createElement('button');
                    button.className = 'btn-template' + (configInfo.wsl.active ? ' active' : '');
                    button.textContent = 'WSL (' + configInfo.wsl.name.toUpperCase() + ')';
                    button.onclick = () => toggleWSL(button);
                    templateButtons.appendChild(button);
                }
            } catch (e) {
                console.error('Error loading template buttons:', e);
            }
        }

        // Toggle template
        async function toggleTemplate(templateFile, button) {
            try {
                const isActive = await pywebview.api.toggle_template(templateFile);
                if (isActive) {
                    button.classList.add('active');
                } else {
                    button.classList.remove('active');
                }
            } catch (e) {
                console.error('Error toggling template:', e);
            }
        }

        // Toggle WSL
        async function toggleWSL(button) {
            try {
                const isActive = await pywebview.api.toggle_wsl();
                if (isActive) {
                    button.classList.add('active');
                } else {
                    button.classList.remove('active');
                }
            } catch (e) {
                console.error('Error toggling WSL:', e);
            }
        }

        // Toggle light mode
        function toggleLightMode() {
            isLightMode = !isLightMode;
            pywebview.api.toggle_light_mode(isLightMode);

            if (isLightMode) {
                lightModeButton.classList.add('active');
            } else {
                lightModeButton.classList.remove('active');
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
            try {
                const result = await pywebview.api.generate_colors();
                if (result.success) {
                    currentColors = result.colors;
                    updateColorGrid(result.colors);
                    updateTheme(result.colors);
                    showMessage('Colors generated successfully!', 'success');
                } else {
                    showMessage(result.error || 'Failed to generate colors', 'error');
                }
            } catch (e) {
                console.error('Error generating colors:', e);
                showMessage('Error generating colors', 'error');
            }
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
    api = PrismaAPI()
    window = webview.create_window(
        'Prisma - Pywal Color Generator',
        html=HTML,
        js_api=api,
        width=900,
        height=900,
        resizable=True
    )
    webview.start()


if __name__ == "__main__":
    main()
