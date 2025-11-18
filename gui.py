import wx
from PIL import Image, ImageEnhance
from json import loads
from os import path
import sys
from main import gen_colors, get_wallpaper, home


class ColorPanel(wx.Panel):
    """Custom panel to display a color with label"""
    def __init__(self, parent, color_name, color_value):
        super().__init__(parent, size=(80, 60))
        self.color_name = color_name
        self.color_value = color_value

        # Set background color
        self.SetBackgroundColour(color_value)

        # Create label
        contrast_color = self.get_contrast_color(color_value)
        self.label = wx.StaticText(self, label=color_name, style=wx.ALIGN_CENTER)
        self.label.SetForegroundColour(contrast_color)
        self.label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))

        # Center the label
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.label, 1, wx.ALIGN_CENTER | wx.ALIGN_CENTER_VERTICAL)
        self.SetSizer(sizer)

    def update_color(self, color_value):
        """Update the panel color"""
        self.color_value = color_value
        self.SetBackgroundColour(color_value)
        contrast_color = self.get_contrast_color(color_value)
        self.label.SetForegroundColour(contrast_color)
        self.Refresh()

    def get_contrast_color(self, hex_color):
        """Get contrasting text color (black or white) for a given background color"""
        try:
            # Remove # if present
            hex_color = hex_color.lstrip('#')
            # Convert to RGB
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            # Calculate luminance
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#000000" if luminance > 0.5 else "#ffffff"
        except:
            return "#ffffff"


class PrismaFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Prisma - Pywal Color Generator", size=(820, 750))

        # State variables
        self.current_image_path = None
        self.light_mode = False
        self.colors = {}
        self.color_panels = {}
        self.saturation = 50  # 0-100, 50 is normal
        self.contrast = 50    # 0-100, 50 is normal

        # Load existing pywal colors if available
        self.load_pywal_colors()

        # Set background color
        bg_color = self.colors.get("background", "#000000")
        self.SetBackgroundColour(bg_color)

        # Create panel and UI
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(bg_color)

        # Create UI
        self.create_widgets()

        # Load current wallpaper
        self.load_current_wallpaper()

        self.Centre()

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

    def create_widgets(self):
        """Create all GUI widgets"""
        bg_color = self.colors.get("background", "#000000")
        fg_color = self.colors.get("foreground", "#ffffff")

        # Main sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Image preview section
        preview_label = wx.StaticText(self.panel, label="Image Preview")
        preview_label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        preview_label.SetForegroundColour(fg_color)
        preview_label.SetBackgroundColour(bg_color)
        main_sizer.Add(preview_label, 0, wx.ALIGN_CENTER | wx.TOP, 10)

        # Image display
        self.image_bitmap = wx.StaticBitmap(self.panel)
        self.image_bitmap.SetBackgroundColour(bg_color)
        main_sizer.Add(self.image_bitmap, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        # Loading text (will be hidden when image loads)
        self.loading_text = wx.StaticText(self.panel, label="Loading...")
        self.loading_text.SetForegroundColour(fg_color)
        self.loading_text.SetBackgroundColour(bg_color)
        main_sizer.Add(self.loading_text, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        # Image adjustment sliders section
        adjustment_sizer = wx.BoxSizer(wx.VERTICAL)

        # Saturation slider
        saturation_box = wx.BoxSizer(wx.HORIZONTAL)
        saturation_label = wx.StaticText(self.panel, label="Saturation:")
        saturation_label.SetForegroundColour(fg_color)
        saturation_label.SetBackgroundColour(bg_color)
        saturation_box.Add(saturation_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.saturation_slider = wx.Slider(self.panel, value=50, minValue=0, maxValue=100,
                                          style=wx.SL_HORIZONTAL | wx.SL_LABELS, size=(300, -1))
        self.saturation_slider.Bind(wx.EVT_SLIDER, self.on_saturation_change)
        saturation_box.Add(self.saturation_slider, 1, wx.EXPAND | wx.RIGHT, 10)

        self.saturation_value = wx.StaticText(self.panel, label="50")
        self.saturation_value.SetForegroundColour(fg_color)
        self.saturation_value.SetBackgroundColour(bg_color)
        saturation_box.Add(self.saturation_value, 0, wx.ALIGN_CENTER_VERTICAL)

        adjustment_sizer.Add(saturation_box, 0, wx.EXPAND | wx.ALL, 5)

        # Contrast slider
        contrast_box = wx.BoxSizer(wx.HORIZONTAL)
        contrast_label = wx.StaticText(self.panel, label="Contrast:")
        contrast_label.SetForegroundColour(fg_color)
        contrast_label.SetBackgroundColour(bg_color)
        contrast_box.Add(contrast_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.contrast_slider = wx.Slider(self.panel, value=50, minValue=0, maxValue=100,
                                        style=wx.SL_HORIZONTAL | wx.SL_LABELS, size=(300, -1))
        self.contrast_slider.Bind(wx.EVT_SLIDER, self.on_contrast_change)
        contrast_box.Add(self.contrast_slider, 1, wx.EXPAND | wx.RIGHT, 10)

        self.contrast_value = wx.StaticText(self.panel, label="50")
        self.contrast_value.SetForegroundColour(fg_color)
        self.contrast_value.SetBackgroundColour(bg_color)
        contrast_box.Add(self.contrast_value, 0, wx.ALIGN_CENTER_VERTICAL)

        adjustment_sizer.Add(contrast_box, 0, wx.EXPAND | wx.ALL, 5)

        main_sizer.Add(adjustment_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        # Color grid section
        color_label = wx.StaticText(self.panel, label="Color Palette")
        color_label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        color_label.SetForegroundColour(fg_color)
        color_label.SetBackgroundColour(bg_color)
        main_sizer.Add(color_label, 0, wx.ALIGN_CENTER | wx.TOP, 10)

        # Create grid for colors (2 rows x 9 columns)
        grid_sizer = wx.GridSizer(rows=2, cols=9, hgap=4, vgap=4)

        # Color pairs for the grid
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

        # Create color panels
        for color1, color2 in color_pairs:
            # First color (top row)
            color1_val = self.colors.get(color1, "#808080")
            panel1 = ColorPanel(self.panel, color1, color1_val)
            grid_sizer.Add(panel1, 0, wx.ALL, 2)
            self.color_panels[color1] = panel1

        for color1, color2 in color_pairs:
            # Second color (bottom row)
            color2_val = self.colors.get(color2, "#808080")
            panel2 = ColorPanel(self.panel, color2, color2_val)
            grid_sizer.Add(panel2, 0, wx.ALL, 2)
            self.color_panels[color2] = panel2

        main_sizer.Add(grid_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        # Controls section
        controls_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Light mode checkbox
        self.light_mode_checkbox = wx.CheckBox(self.panel, label="Light Mode")
        self.light_mode_checkbox.SetValue(self.light_mode)
        self.light_mode_checkbox.SetForegroundColour(fg_color)
        self.light_mode_checkbox.SetBackgroundColour(bg_color)
        self.light_mode_checkbox.Bind(wx.EVT_CHECKBOX, self.on_toggle_light_mode)
        controls_sizer.Add(self.light_mode_checkbox, 0, wx.ALL, 5)

        main_sizer.Add(controls_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        # Buttons section
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Select File button
        self.select_btn = wx.Button(self.panel, label="Select File", size=(150, 40))
        self.select_btn.SetBackgroundColour(self.colors.get("color4", "#4080ff"))
        self.select_btn.SetForegroundColour(fg_color)
        self.select_btn.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.select_btn.Bind(wx.EVT_BUTTON, self.on_select_file)
        button_sizer.Add(self.select_btn, 0, wx.ALL, 10)

        # Generate button
        self.generate_btn = wx.Button(self.panel, label="Generate", size=(150, 40))
        self.generate_btn.SetBackgroundColour(self.colors.get("color2", "#40ff80"))
        self.generate_btn.SetForegroundColour(fg_color)
        self.generate_btn.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.generate_btn.Bind(wx.EVT_BUTTON, self.on_generate)
        button_sizer.Add(self.generate_btn, 0, wx.ALL, 10)

        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        self.panel.SetSizer(main_sizer)

    def load_current_wallpaper(self):
        """Load and display current Windows wallpaper"""
        try:
            wallpaper_path = get_wallpaper()
            if wallpaper_path and path.isfile(wallpaper_path):
                self.current_image_path = wallpaper_path
                self.display_image(wallpaper_path)
            else:
                self.loading_text.SetLabel("No wallpaper found")
        except Exception as e:
            self.loading_text.SetLabel("Could not load wallpaper")
            print(f"Error loading wallpaper: {e}")

    def display_image(self, image_path):
        """Display image in preview area"""
        try:
            # Open and resize image
            img = Image.open(image_path)

            # Calculate aspect ratio and resize
            max_width, max_height = 400, 200
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Convert PIL image to wx.Image
            width, height = img.size
            wx_image = wx.Image(width, height)
            wx_image.SetData(img.convert("RGB").tobytes())

            # Convert to bitmap and display
            bitmap = wx.Bitmap(wx_image)
            self.image_bitmap.SetBitmap(bitmap)

            # Hide loading text
            self.loading_text.SetLabel("")

            # Refresh layout
            self.panel.Layout()

        except Exception as e:
            self.loading_text.SetLabel("Error loading image")
            print(f"Error displaying image: {e}")

    def on_select_file(self, event):
        """Open file dialog to select an image"""
        wildcard = "Image files (*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tiff)|*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tiff|All files (*.*)|*.*"

        with wx.FileDialog(self, "Select an image",
                          wildcard=wildcard,
                          style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as file_dialog:

            if file_dialog.ShowModal() == wx.ID_OK:
                file_path = file_dialog.GetPath()
                self.current_image_path = file_path
                self.display_image(file_path)

    def on_toggle_light_mode(self, event):
        """Toggle between light and dark mode"""
        self.light_mode = self.light_mode_checkbox.GetValue()

    def on_saturation_change(self, event):
        """Handle saturation slider change"""
        self.saturation = self.saturation_slider.GetValue()
        self.saturation_value.SetLabel(str(self.saturation))

    def on_contrast_change(self, event):
        """Handle contrast slider change"""
        self.contrast = self.contrast_slider.GetValue()
        self.contrast_value.SetLabel(str(self.contrast))

    def adjust_and_save_image(self, image_path):
        """Adjust image saturation and contrast, save with special naming convention

        Args:
            image_path: Path to the original image

        Returns:
            Path to the adjusted image
        """
        try:
            # Open the image
            img = Image.open(image_path)

            # Convert saturation and contrast from 0-100 scale to PIL scale
            # 50 = 1.0 (normal), 0 = 0.0, 100 = 2.0
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
            # Return original path if adjustment fails
            return image_path

    def on_generate(self, event):
        """Generate colors from current image"""
        if not self.current_image_path:
            wx.MessageBox("No image selected. Please select an image first.",
                         "Error", wx.OK | wx.ICON_ERROR)
            return

        if not path.isfile(self.current_image_path):
            wx.MessageBox("Selected image file does not exist.",
                         "Error", wx.OK | wx.ICON_ERROR)
            return

        try:
            # Adjust and save image with saturation and contrast
            adjusted_image_path = self.adjust_and_save_image(self.current_image_path)

            # Generate colors using main.py function with adjusted image
            gen_colors(adjusted_image_path, apply_config=False, light_mode=self.light_mode)

            # Reload colors
            self.load_pywal_colors()

            # Update UI
            self.update_colors()

            wx.MessageBox("Colors generated successfully!",
                         "Success", wx.OK | wx.ICON_INFORMATION)

        except Exception as e:
            wx.MessageBox(f"Failed to generate colors: {str(e)}",
                         "Error", wx.OK | wx.ICON_ERROR)
            print(f"Error generating colors: {e}")

    def update_colors(self):
        """Update all color displays in the GUI"""
        bg_color = self.colors.get("background", "#000000")
        fg_color = self.colors.get("foreground", "#ffffff")

        # Update frame and panel background
        self.SetBackgroundColour(bg_color)
        self.panel.SetBackgroundColour(bg_color)

        # Update all color panels
        for color_name, panel in self.color_panels.items():
            color_val = self.colors.get(color_name, "#808080")
            panel.update_color(color_val)

        # Update button colors
        self.select_btn.SetBackgroundColour(self.colors.get("color4", "#4080ff"))
        self.select_btn.SetForegroundColour(fg_color)
        self.generate_btn.SetBackgroundColour(self.colors.get("color2", "#40ff80"))
        self.generate_btn.SetForegroundColour(fg_color)

        # Update checkbox and labels
        self.light_mode_checkbox.SetForegroundColour(fg_color)
        self.light_mode_checkbox.SetBackgroundColour(bg_color)

        for child in self.panel.GetChildren():
            if isinstance(child, wx.StaticText):
                child.SetForegroundColour(fg_color)
                child.SetBackgroundColour(bg_color)

        # Refresh the display
        self.panel.Refresh()
        self.Refresh()


def main():
    app = wx.App()
    frame = PrismaFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
