from kivy.lang import Builder
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import ListProperty
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.slider import MDSlider
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.dialog import MDDialog
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from PIL import Image as PILImage, ImageEnhance
from json import loads
from os import path, remove
import sys
from main import gen_colors, get_wallpaper, home


KV = '''
<BorderCard@MDCard>:
    radius: [0, 0, 0, 0]
    canvas.before:
        Color:
            rgba: app.border_color
        Line:
            rectangle: self.x, self.y, self.width, self.height
            width: 1

MDScreen:
    md_bg_color: app.bg_color

    MDScrollView:
        do_scroll_x: False
        bar_width: 0

        MDBoxLayout:
            orientation: 'vertical'
            spacing: dp(15)
            adaptive_height: True
            padding: dp(20)

            # Image Preview Section
            BorderCard:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(225)
                padding: dp(15)
                elevation: 0
                md_bg_color: app.bg_color

                FloatLayout:
                    size_hint_y: None
                    height: dp(195)

                    Image:
                        id: image_preview
                        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
                        size_hint: None, None
                        allow_stretch: True
                        keep_ratio: True

                    MDLabel:
                        id: loading_text
                        text: "Loading..."
                        halign: "center"
                        valign: "middle"
                        theme_text_color: "Custom"
                        text_color: 0.5, 0.5, 0.5, 1

            # Image Adjustments Section
            BorderCard:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(120)
                padding: dp(15)
                elevation: 0
                md_bg_color: app.bg_color

                MDBoxLayout:
                    orientation: 'vertical'
                    spacing: dp(15)

                    # Saturation Slider
                    MDBoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(40)
                        spacing: dp(10)

                        MDLabel:
                            text: "Saturation"
                            size_hint_x: None
                            width: dp(100)
                            theme_text_color: "Custom"
                            text_color: app.fg_color

                        MDSlider:
                            id: saturation_slider
                            min: 0
                            max: 100
                            value: 50
                            step: 1
                            hint: True
                            color: app.accent_color
                            on_value: app.on_saturation_change(self.value)

                        MDLabel:
                            text: str(int(saturation_slider.value))
                            size_hint_x: None
                            width: dp(40)
                            theme_text_color: "Custom"
                            text_color: app.accent_color
                            font_name: "RobotoMono-Regular"

                    # Contrast Slider
                    MDBoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(40)
                        spacing: dp(10)

                        MDLabel:
                            text: "Contrast"
                            size_hint_x: None
                            width: dp(100)
                            theme_text_color: "Custom"
                            text_color: app.fg_color

                        MDSlider:
                            id: contrast_slider
                            min: 0
                            max: 100
                            value: 50
                            step: 1
                            hint: True
                            color: app.accent_color
                            on_value: app.on_contrast_change(self.value)

                        MDLabel:
                            text: str(int(contrast_slider.value))
                            size_hint_x: None
                            width: dp(40)
                            theme_text_color: "Custom"
                            text_color: app.accent_color
                            font_name: "RobotoMono-Regular"

            # Color Palette Section
            BorderCard:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(170)
                padding: dp(15)
                elevation: 0
                md_bg_color: app.bg_color

                MDGridLayout:
                    id: color_grid
                    cols: 9
                    rows: 2
                    spacing: dp(6)

            # Controls Section
            BorderCard:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(130)
                padding: dp(15)
                elevation: 0
                md_bg_color: app.bg_color

                MDBoxLayout:
                    orientation: 'vertical'
                    spacing: dp(15)

                    MDBoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(40)

                        Widget:

                        MDCheckbox:
                            id: light_mode_checkbox
                            size_hint: None, None
                            size: dp(40), dp(40)
                            on_active: app.on_light_mode_toggle(self.active)

                        MDLabel:
                            text: "Light Mode Color Scheme"
                            theme_text_color: "Custom"
                            text_color: app.fg_color
                            size_hint_y: None
                            height: dp(40)

                        Widget:

                    MDBoxLayout:
                        orientation: 'horizontal'
                        spacing: dp(15)
                        size_hint_y: None
                        height: dp(50)

                        Widget:

                        MDRaisedButton:
                            text: "SELECT IMAGE"
                            md_bg_color: 0.2, 0.2, 0.2, 1
                            on_release: app.select_image()
                            size_hint_x: None
                            width: dp(180)
                            radius: [0, 0, 0, 0]

                        MDRaisedButton:
                            text: "GENERATE COLORS"
                            md_bg_color: app.accent_color
                            on_release: app.generate_colors()
                            size_hint_x: None
                            width: dp(180)
                            radius: [0, 0, 0, 0]

                        Widget:
'''


class ColorBox(MDCard):
    """Custom widget for displaying a single color"""
    def __init__(self, color_name, color_value, **kwargs):
        super().__init__(**kwargs)
        self.color_name = color_name
        self.color_value = color_value
        self.size_hint = (1, None)
        self.height = 60
        self.md_bg_color = self.hex_to_rgb(color_value)
        self.elevation = 0
        self.radius = [0, 0, 0, 0]

        # Add label
        label = MDLabel(
            text=color_name,
            halign="center",
            theme_text_color="Custom",
            text_color=self.get_contrast_color(color_value),
            font_size="9sp"
        )
        self.add_widget(label)

    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGBA tuple for Kivy"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (r/255, g/255, b/255, 1)

    def get_contrast_color(self, hex_color):
        """Get contrasting text color (black or white)"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            if luminance > 0.5:
                return (0, 0, 0, 1)
            return (1, 1, 1, 1)
        except:
            return (1, 1, 1, 1)

    def update_color(self, color_value):
        """Update the box color"""
        self.color_value = color_value
        self.md_bg_color = self.hex_to_rgb(color_value)
        # Update label color
        if self.children:
            self.children[0].text_color = self.get_contrast_color(color_value)


class PrismaApp(MDApp):
    # Color properties
    bg_color = ListProperty([0, 0, 0, 1])
    border_color = ListProperty([0.5, 0.5, 0.5, 1])
    fg_color = ListProperty([0.88, 0.88, 0.88, 1])
    accent_color = ListProperty([0.33, 0.53, 0.87, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Prisma - Pywal Color Generator"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"

        # State variables
        self.current_image_path = None
        self.light_mode = False
        self.colors = {}
        self.color_boxes = {}
        self.saturation = 50
        self.contrast = 50
        self.original_image = None
        self.adjusted_image_path = None

        # File manager
        self.file_manager = None
        self.dialog = None

        # Load colors
        self.load_pywal_colors()
        self.update_theme_colors()

    def build(self):
        Window.size = (900, 800)
        self.screen = Builder.load_string(KV)
        Clock.schedule_once(self.load_current_wallpaper, 0.5)
        Clock.schedule_once(self.create_color_palette, 0.5)
        return self.screen

    def hex_to_kivy_color(self, hex_color):
        """Convert hex color to Kivy RGBA tuple"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return [r/255, g/255, b/255, 1]

    def update_theme_colors(self):
        """Update app colors from pywal palette"""
        self.bg_color = self.hex_to_kivy_color(self.colors.get("background", "#000000"))
        self.border_color = self.hex_to_kivy_color(self.colors.get("foreground", "#808080"))
        self.fg_color = self.hex_to_kivy_color(self.colors.get("foreground", "#808080"))
        self.accent_color = self.hex_to_kivy_color(self.colors.get("color4", "#5588dd"))

    def load_pywal_colors(self):
        """Load colors from pywal cache if it exists"""
        colors_path = home + "/.cache/wal/colors.json"
        if path.isfile(colors_path):
            try:
                with open(colors_path, "r") as f:
                    data = loads(f.read())
                    self.colors = data.get("colors", {})
                    self.colors.update(data.get("special", {}))
            except Exception as e:
                print(f"Could not load colors: {e}")
                self.colors = {}

        # Use gray defaults if no colors loaded
        if not self.colors:
            self.colors = {
                "background": "#000000",
                "foreground": "#808080",
                **{f"color{i}": "#808080" for i in range(16)}
            }

    def create_color_palette(self, dt):
        """Create the color palette grid"""
        grid = self.screen.ids.color_grid

        color_pairs = [
            ("background", "foreground"),
            ("color0", "color1"),
            ("color2", "color3"),
            ("color4", "color5"),
            ("color6", "color7"),
            ("color8", "color9"),
            ("color10", "color11"),
            ("color12", "color13"),
            ("color14", "color15")
        ]

        # Add top row
        for color1, color2 in color_pairs:
            color1_val = self.colors.get(color1, "#808080")
            box = ColorBox(color1, color1_val)
            grid.add_widget(box)
            self.color_boxes[color1] = box

        # Add bottom row
        for color1, color2 in color_pairs:
            color2_val = self.colors.get(color2, "#808080")
            box = ColorBox(color2, color2_val)
            grid.add_widget(box)
            self.color_boxes[color2] = box

    def load_current_wallpaper(self, dt):
        """Load and display current Windows wallpaper"""
        try:
            wallpaper_path = get_wallpaper()
            if wallpaper_path and path.isfile(wallpaper_path):
                self.current_image_path = wallpaper_path
                self.display_image(wallpaper_path)
            else:
                self.screen.ids.loading_text.text = "No wallpaper found"
        except Exception as e:
            self.screen.ids.loading_text.text = "Could not load wallpaper"
            print(f"Error loading wallpaper: {e}")

    def display_image(self, image_path):
        """Display image in preview area"""
        try:
            # Open and resize image
            img = PILImage.open(image_path)

            # Calculate aspect ratio and resize to fill preview area
            max_width, max_height = 850, 195
            img.thumbnail((max_width, max_height), PILImage.Resampling.LANCZOS)

            # Store original image for later adjustments
            self.original_image = img.copy()

            # Display the image with current adjustments
            self.update_preview()

            # Hide loading text
            self.screen.ids.loading_text.text = ""

        except Exception as e:
            self.screen.ids.loading_text.text = "Error loading image"
            print(f"Error displaying image: {e}")

    def update_preview(self):
        """Update preview with current saturation and contrast adjustments"""
        if self.original_image is None:
            return

        try:
            # Start with a copy of the original image
            img = self.original_image.copy()

            # Convert saturation and contrast from 0-100 scale to PIL scale
            saturation_factor = self.saturation / 50.0
            contrast_factor = self.contrast / 50.0

            # Apply saturation adjustment
            if saturation_factor != 1.0:
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(saturation_factor)

            # Apply contrast adjustment
            if contrast_factor != 1.0:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(contrast_factor)

            # Convert PIL image to Kivy texture
            img_rgb = img.convert('RGB')
            data = img_rgb.tobytes()
            texture = Texture.create(size=img_rgb.size, colorfmt='rgb')
            texture.blit_buffer(data, colorfmt='rgb', bufferfmt='ubyte')
            texture.flip_vertical()

            # Update image widget and size to fill container
            image_widget = self.screen.ids.image_preview
            image_widget.texture = texture

            # Calculate size to fill the container (850x195 with padding)
            container_width = 850
            container_height = 195
            img_width, img_height = img.size

            # Calculate scale to fill container
            scale_w = container_width / img_width
            scale_h = container_height / img_height
            scale = max(scale_w, scale_h)  # Use max to fill

            # Set image size
            image_widget.size = (img_width * scale, img_height * scale)

        except Exception as e:
            print(f"Error updating preview: {e}")

    def select_image(self):
        """Open file manager to select an image"""
        if not self.file_manager:
            self.file_manager = MDFileManager(
                exit_manager=self.exit_file_manager,
                select_path=self.on_file_selected,
            )

        self.file_manager.show(path.expanduser("~"))

    def on_file_selected(self, file_path):
        """Handle file selection"""
        self.exit_file_manager()

        # Check if it's an image file
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')
        if file_path.lower().endswith(valid_extensions):
            self.current_image_path = file_path
            self.display_image(file_path)

    def exit_file_manager(self, *args):
        """Close file manager"""
        if self.file_manager:
            self.file_manager.close()

    def on_saturation_change(self, value):
        """Handle saturation slider change"""
        self.saturation = int(value)
        self.update_preview()

    def on_contrast_change(self, value):
        """Handle contrast slider change"""
        self.contrast = int(value)
        self.update_preview()

    def on_light_mode_toggle(self, active):
        """Toggle between light and dark mode"""
        self.light_mode = active

    def adjust_and_save_image(self, image_path):
        """Adjust image saturation and contrast, save with special naming convention"""
        try:
            # Open the image
            img = PILImage.open(image_path)

            # Convert saturation and contrast from 0-100 scale to PIL scale
            saturation_factor = self.saturation / 50.0
            contrast_factor = self.contrast / 50.0

            # Apply saturation adjustment
            if saturation_factor != 1.0:
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(saturation_factor)

            # Apply contrast adjustment
            if contrast_factor != 1.0:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(contrast_factor)

            # Create output filename with saturation and contrast values
            base_dir = path.dirname(image_path)
            base_name = path.basename(image_path)
            name_without_ext, ext = path.splitext(base_name)

            # Create new filename: original_name-s50c50.ext
            adjusted_filename = f"{name_without_ext}-s{self.saturation}c{self.contrast}{ext}"
            adjusted_path = path.join(base_dir, adjusted_filename)

            # Save the adjusted image
            img.save(adjusted_path)

            return adjusted_path

        except Exception as e:
            print(f"Error adjusting image: {e}")
            return image_path

    def generate_colors(self):
        """Generate colors from current image"""
        if not self.current_image_path:
            self.show_dialog("Error", "No image selected. Please select an image first.")
            return

        if not path.isfile(self.current_image_path):
            self.show_dialog("Error", "Selected image file does not exist.")
            return

        # Check if adjustments were made
        is_adjusted = (self.saturation != 50 or self.contrast != 50)

        try:
            # Adjust and save image with saturation and contrast
            adjusted_image_path = self.adjust_and_save_image(self.current_image_path)

            # Store the path for potential cleanup
            self.adjusted_image_path = adjusted_image_path if is_adjusted else None

            # Generate colors using main.py function with adjusted image
            gen_colors(adjusted_image_path, apply_config=False, light_mode=self.light_mode)

            # Reload colors
            self.load_pywal_colors()

            # Update theme colors
            self.update_theme_colors()

            # Update UI
            self.update_color_palette()

            # Clean up temporary adjusted image file if it was created
            if is_adjusted and self.adjusted_image_path and path.isfile(self.adjusted_image_path):
                try:
                    remove(self.adjusted_image_path)
                    print(f"Cleaned up temporary file: {self.adjusted_image_path}")
                except Exception as cleanup_error:
                    print(f"Warning: Could not delete temporary file: {cleanup_error}")

            self.show_dialog("Success", "Colors generated successfully!")

        except Exception as e:
            self.show_dialog("Error", f"Failed to generate colors: {str(e)}")
            print(f"Error generating colors: {e}")

    def update_color_palette(self):
        """Update all color boxes with new colors"""
        for color_name, box in self.color_boxes.items():
            color_val = self.colors.get(color_name, "#808080")
            box.update_color(color_val)

    def show_dialog(self, title, text):
        """Show a simple dialog"""
        if self.dialog:
            self.dialog.dismiss()

        self.dialog = MDDialog(
            title=title,
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: self.dialog.dismiss()
                ),
            ],
        )
        self.dialog.open()


def main():
    PrismaApp().run()


if __name__ == "__main__":
    main()
