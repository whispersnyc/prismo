import webview
from PIL import Image as PILImage, ImageEnhance
from json import loads, dumps
from os import path, remove
import base64
import io
from main import gen_colors, get_wallpaper, home


class PrismaAPI:
    """Backend API for the pywebview GUI"""

    def __init__(self):
        self.current_image_path = None
        self.light_mode = False
        self.colors = {}
        self.saturation = 50
        self.contrast = 50
        self.original_image = None
        self.adjusted_image_path = None

        # Load initial colors
        self.load_pywal_colors()

    def load_pywal_colors(self):
        """Load colors from pywal cache if it exists"""
        colors_path = home + "/.cache/wal/colors.json"
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
            return self.get_image_base64(file_path)
        return None

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

            # Generate colors
            gen_colors(adjusted_image_path, apply_config=False, light_mode=self.light_mode)

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
            overflow-y: auto;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }

        .panel {
            background: #000000;
            border: 1px solid #808080;
            padding: 20px;
            margin-bottom: 20px;
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
            background: #5588dd;
            cursor: pointer;
            border-radius: 50%;
        }

        input[type="range"]::-moz-range-thumb {
            width: 16px;
            height: 16px;
            background: #5588dd;
            cursor: pointer;
            border-radius: 50%;
            border: none;
        }

        .color-grid {
            display: grid;
            grid-template-columns: repeat(9, 1fr);
            gap: 6px;
        }

        .color-box {
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 9px;
            font-weight: 500;
            cursor: default;
        }

        .controls {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .checkbox-group input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }

        .checkbox-group label {
            font-size: 14px;
            cursor: pointer;
            user-select: none;
        }

        .button-group {
            display: flex;
            gap: 15px;
            justify-content: center;
        }

        button {
            padding: 12px 32px;
            font-size: 14px;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: opacity 0.2s;
            letter-spacing: 0.5px;
        }

        button:hover {
            opacity: 0.8;
        }

        button:active {
            opacity: 0.6;
        }

        .btn-secondary {
            background: #333333;
            color: #ffffff;
        }

        .btn-primary {
            background: #5588dd;
            color: #ffffff;
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
    <div class="container">
        <!-- Image Preview -->
        <div class="panel">
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

        <!-- Color Palette -->
        <div class="panel">
            <div class="color-grid" id="colorGrid"></div>
        </div>

        <!-- Controls -->
        <div class="panel">
            <div class="controls">
                <div class="checkbox-group">
                    <input type="checkbox" id="lightModeCheckbox">
                    <label for="lightModeCheckbox">Light Mode Color Scheme</label>
                </div>

                <div class="button-group">
                    <button class="btn-secondary" onclick="selectImage()">SELECT IMAGE</button>
                    <button class="btn-primary" onclick="generateColors()">GENERATE COLORS</button>
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
        let lightModeCheckbox = document.getElementById('lightModeCheckbox');

        // Initialize
        window.onload = async function() {
            await loadColors();
            await loadWallpaper();
        };

        // Load colors from backend
        async function loadColors() {
            try {
                console.log('Loading colors from backend...');
                const colors = await pywebview.api.get_colors();
                console.log('Colors loaded:', colors);
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

        // Update color grid
        function updateColorGrid(colors) {
            const colorNames = [
                'background', 'foreground',
                'color0', 'color1', 'color2', 'color3',
                'color4', 'color5', 'color6', 'color7',
                'color8', 'color9', 'color10', 'color11',
                'color12', 'color13', 'color14', 'color15'
            ];

            colorGrid.innerHTML = '';
            colorNames.forEach(name => {
                const color = colors[name] || '#808080';
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

                colorGrid.appendChild(box);
            });
        }

        // Update theme colors
        function updateTheme(colors) {
            const bg = colors.background || '#000000';
            const fg = colors.foreground || '#808080';
            const accent = colors.color4 || '#5588dd';

            document.body.style.backgroundColor = bg;
            document.body.style.color = fg;

            document.querySelectorAll('.panel').forEach(panel => {
                panel.style.backgroundColor = bg;
                panel.style.borderColor = fg;
            });

            document.querySelectorAll('.slider-label, .checkbox-group label').forEach(el => {
                el.style.color = fg;
            });

            document.querySelectorAll('.image-preview').forEach(el => {
                el.style.backgroundColor = bg;
            });

            document.querySelectorAll('input[type="range"]::-webkit-slider-thumb').forEach(el => {
                el.style.background = accent;
            });

            // Update button primary color
            document.querySelector('.btn-primary').style.backgroundColor = accent;
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

        // Light mode checkbox
        lightModeCheckbox.addEventListener('change', function() {
            pywebview.api.toggle_light_mode(this.checked);
        });

        // Select image
        async function selectImage() {
            try {
                const imageData = await pywebview.api.select_image();
                if (imageData) {
                    imagePreview.innerHTML = '<img src="' + imageData + '">';
                }
            } catch (e) {
                console.error('Error selecting image:', e);
            }
        }

        // Generate colors
        async function generateColors() {
            try {
                const result = await pywebview.api.generate_colors();
                if (result.success) {
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
