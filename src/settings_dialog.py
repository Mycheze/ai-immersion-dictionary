import tkinter as tk
from tkinter import ttk

class SettingsDialog(tk.Toplevel):
    """
    Dialog for configuring application settings like text scaling
    """
    
    def __init__(self, parent, user_settings):
        """Initialize settings dialog"""
        super().__init__(parent)
        self.parent = parent
        self.user_settings = user_settings
        
        self.title("Settings")
        self.geometry("400x400")  # Increased height to ensure buttons are visible
        self.transient(parent)  # Set to be on top of the main window
        self.grab_set()  # Make it modal
        
        # Center the dialog on the main window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Initialize UI components
        self.create_widgets()
        
        # Load current settings
        self.load_settings()
        
        # Make the dialog resizable
        self.resizable(True, True)
        
        # Set minimum size
        self.minsize(350, 350)
        
        # Bind keyboard events
        self.bind("<Escape>", self.on_cancel)
        self.bind("<Return>", self.on_save)
        
    def create_widgets(self):
        """Create dialog widgets"""
        # Main frame with padding
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Dialog title
        title_label = ttk.Label(main_frame, text="Application Settings", font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 15))
        
        # Text scaling frame
        text_scale_frame = ttk.LabelFrame(main_frame, text="Text Size", padding=10)
        text_scale_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Text scaling controls
        scale_frame = ttk.Frame(text_scale_frame)
        scale_frame.pack(fill=tk.X, pady=5)
        
        # Sample text to preview scaling
        self.preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding=10)
        self.preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.preview_text = tk.Text(self.preview_frame, height=5, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        self.preview_text.insert(tk.END, "This is a sample text.\nChange the scaling to see how it affects text display.\n\nLorem ipsum dolor sit amet, consectetur adipiscing elit.")
        self.preview_text.config(state=tk.DISABLED)
        
        # Scale factor slider and value display
        scale_label = ttk.Label(scale_frame, text="Text Scale:")
        scale_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.scale_var = tk.DoubleVar(value=1.0)
        self.scale_value_label = ttk.Label(scale_frame, width=4)
        self.scale_value_label.pack(side=tk.RIGHT)
        
        self.scale_slider = ttk.Scale(
            scale_frame,
            from_=0.8,
            to=1.5,
            variable=self.scale_var,
            orient=tk.HORIZONTAL,
            length=200,
            command=self.on_scale_change
        )
        self.scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Button frame for save/cancel
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Buttons
        self.save_button = ttk.Button(button_frame, text="Save", command=self.on_save)
        self.save_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel)
        self.cancel_button.pack(side=tk.RIGHT)
        
        # Configure responsiveness for the scale slider
        scale_frame.columnconfigure(1, weight=1)
        
    def load_settings(self):
        """Load current settings into the dialog"""
        settings = self.user_settings.get_settings()
        
        # Set text scale factor
        scale_factor = settings.get('text_scale_factor', 1.0)
        self.scale_var.set(scale_factor)
        
        # Update scale value label
        self.update_scale_value_label()
        
        # Update preview text font
        self.update_preview_font()
        
    def update_scale_value_label(self):
        """Update the label showing the current scale value"""
        value = self.scale_var.get()
        self.scale_value_label.config(text=f"{value:.2f}x")
        
    def update_preview_font(self):
        """Update preview text font based on scale factor"""
        scale = self.scale_var.get()
        base_size = 10  # Base font size
        new_size = int(base_size * scale)
        
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.tag_configure("scaled", font=("Arial", new_size))
        self.preview_text.tag_add("scaled", "1.0", "end")
        self.preview_text.config(state=tk.DISABLED)
        
    def on_scale_change(self, event=None):
        """Handle scale slider change"""
        self.update_scale_value_label()
        self.update_preview_font()
        
    def on_save(self, event=None):
        """Save settings and close dialog"""
        # Get values from UI components
        text_scale = self.scale_var.get()
        
        # Update settings
        self.user_settings.update_settings({
            'text_scale_factor': text_scale
        })
        
        # Close dialog
        self.destroy()
        
    def on_cancel(self, event=None):
        """Cancel and close dialog"""
        self.destroy()