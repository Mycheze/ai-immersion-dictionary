"""
Settings View

This module provides a view for the settings dialog, allowing users to
configure application settings such as text scaling, language preferences,
and other options.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, Callable, List

from .base_view import BaseView

class SettingsView(BaseView):
    """
    View for the settings dialog.
    
    This view provides a user interface for configuring application settings,
    with support for text scaling, language preferences, and other options.
    
    Attributes:
        dialog: The settings dialog window
        user_model: Reference to the user model
        event_bus: Event system for view-related notifications
        current_settings: Dictionary of current settings
        notebook: Tabbed interface for settings categories
    """
    
    def __init__(self, parent, user_model, event_bus=None):
        """
        Initialize the settings view.
        
        Args:
            parent: Parent window for the dialog
            user_model: Reference to the user model
            event_bus: Optional event bus for notifications
        """
        super().__init__(parent, event_bus)
        
        self.dialog = None
        self.user_model = user_model
        self.current_settings = {}
        self.is_shown = False
        
        # UI components
        self.notebook = None
        self.scale_var = None
        self.target_lang_var = None
        self.definition_lang_var = None
        self.preview_text = None
    
    def show(self, parent=None):
        """
        Show the settings dialog.
        
        Args:
            parent: Optional parent window (uses self.root if not provided)
        """
        if self.is_shown:
            # If already shown, just focus the dialog
            if self.dialog:
                self.dialog.focus_set()
            return
            
        # Use provided parent or self.root
        parent_window = parent or self.root
        
        # Get current settings
        self.current_settings = self.user_model.get_settings().copy()
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent_window)
        self.dialog.title("Settings")
        self.dialog.geometry("500x450")
        self.dialog.transient(parent_window)  # Set to be on top of the parent window
        self.dialog.grab_set()  # Make it modal
        
        # Center the dialog on the parent window
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = parent_window.winfo_rootx() + (parent_window.winfo_width() // 2) - (width // 2)
        y = parent_window.winfo_rooty() + (parent_window.winfo_height() // 2) - (height // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Make the dialog resizable
        self.dialog.resizable(True, True)
        
        # Set minimum size
        self.dialog.minsize(400, 400)
        
        # Create the dialog content
        self._create_dialog_content()
        
        # Load current settings into the dialog
        self._load_settings()
        
        # Bind events
        self.dialog.bind("<Escape>", self._on_cancel)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        self.is_shown = True
    
    def _create_dialog_content(self):
        """Create the content of the settings dialog."""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a notebook for tabbed interface
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create tabs
        self._create_general_tab()
        self._create_language_tab()
        
        # Button frame for save/cancel
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Reset button on the left
        self.reset_button = ttk.Button(button_frame, text="Reset to Defaults", command=self._on_reset)
        self.reset_button.pack(side=tk.LEFT)
        
        # Save and Cancel buttons on the right
        self.save_button = ttk.Button(button_frame, text="Save", command=self._on_save)
        self.save_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        self.cancel_button.pack(side=tk.RIGHT)
    
    def _create_general_tab(self):
        """Create the general settings tab."""
        general_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(general_tab, text="General")
        
        # Text scaling section
        text_scale_frame = ttk.LabelFrame(general_tab, text="Text Size", padding=10)
        text_scale_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Text scaling controls
        scale_frame = ttk.Frame(text_scale_frame)
        scale_frame.pack(fill=tk.X, pady=5)
        
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
            command=self._on_scale_change
        )
        self.scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Sample text to preview scaling
        preview_frame = ttk.LabelFrame(general_tab, text="Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.preview_text = tk.Text(preview_frame, height=5, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        self.preview_text.insert(tk.END, "This is a sample text.\nChange the scaling to see how it affects text display.\n\nLorem ipsum dolor sit amet, consectetur adipiscing elit.")
        self.preview_text.config(state=tk.DISABLED)
    
    def _create_language_tab(self):
        """Create the language settings tab."""
        language_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(language_tab, text="Languages")
        
        # Target language section
        target_lang_frame = ttk.LabelFrame(language_tab, text="Target Language (Language you are learning)", padding=10)
        target_lang_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Target language dropdown
        self.target_lang_var = tk.StringVar()
        target_lang_combo = ttk.Combobox(target_lang_frame, textvariable=self.target_lang_var)
        target_lang_combo['values'] = self._get_available_languages()
        target_lang_combo.pack(fill=tk.X, pady=5)
        
        # Definition language section
        def_lang_frame = ttk.LabelFrame(language_tab, text="Definition Language", padding=10)
        def_lang_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Definition language dropdown
        self.definition_lang_var = tk.StringVar()
        def_lang_combo = ttk.Combobox(def_lang_frame, textvariable=self.definition_lang_var)
        def_lang_combo['values'] = self._get_available_languages()
        def_lang_combo.pack(fill=tk.X, pady=5)
        
        # Add custom language section
        custom_lang_frame = ttk.LabelFrame(language_tab, text="Add Custom Language", padding=10)
        custom_lang_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Custom language entry
        custom_lang_frame_inner = ttk.Frame(custom_lang_frame)
        custom_lang_frame_inner.pack(fill=tk.X, pady=5)
        
        custom_lang_label = ttk.Label(custom_lang_frame_inner, text="Language Name:")
        custom_lang_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.custom_lang_var = tk.StringVar()
        custom_lang_entry = ttk.Entry(custom_lang_frame_inner, textvariable=self.custom_lang_var)
        custom_lang_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        add_button = ttk.Button(custom_lang_frame_inner, text="Add", command=self._on_add_custom_language)
        add_button.pack(side=tk.RIGHT)
    
    def _load_settings(self):
        """Load current settings into the dialog."""
        # Set text scale factor
        scale_factor = self.current_settings.get('text_scale_factor', 1.0)
        self.scale_var.set(scale_factor)
        
        # Update scale value label
        self._update_scale_value_label()
        
        # Update preview text font
        self._update_preview_font()
        
        # Set language values
        self.target_lang_var.set(self.current_settings.get('target_language', 'Czech'))
        self.definition_lang_var.set(self.current_settings.get('definition_language', 'English'))
    
    def _update_scale_value_label(self):
        """Update the label showing the current scale value."""
        value = self.scale_var.get()
        self.scale_value_label.config(text=f"{value:.2f}x")
    
    def _update_preview_font(self):
        """Update preview text font based on scale factor."""
        scale = self.scale_var.get()
        base_size = 10  # Base font size
        new_size = int(base_size * scale)
        
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.tag_configure("scaled", font=("Arial", new_size))
        self.preview_text.tag_add("scaled", "1.0", "end")
        self.preview_text.config(state=tk.DISABLED)
    
    def _get_available_languages(self) -> List[str]:
        """
        Get a list of available languages.
        
        Returns:
            List of language names
        """
        # Start with common languages
        languages = ["English", "Czech", "Spanish", "French", "German", "Italian", "Portuguese", "Russian", "Japanese", "Chinese", "Korean"]
        
        # Add custom languages from settings
        custom_languages = self.current_settings.get('custom_languages', [])
        if custom_languages:
            for lang in custom_languages:
                if lang not in languages:
                    languages.append(lang)
        
        return sorted(languages)
    
    def _on_scale_change(self, event=None):
        """Handle scale slider change."""
        self._update_scale_value_label()
        self._update_preview_font()
    
    def _on_add_custom_language(self):
        """Handle adding a custom language."""
        custom_lang = self.custom_lang_var.get().strip()
        if not custom_lang:
            return
        
        # Add to custom languages in settings
        custom_languages = self.current_settings.get('custom_languages', [])
        if custom_lang not in custom_languages:
            custom_languages.append(custom_lang)
            self.current_settings['custom_languages'] = custom_languages
            
            # Update comboboxes
            languages = self._get_available_languages()
            target_combo = self.notebook.nametowidget(self.notebook.select()).nametowidget("!labelframe.!combobox")
            target_combo['values'] = languages
            
            def_combo = self.notebook.nametowidget(self.notebook.select()).nametowidget("!labelframe2.!combobox")
            def_combo['values'] = languages
            
            # Clear the entry
            self.custom_lang_var.set("")
    
    def _on_save(self, event=None):
        """Save settings and close dialog."""
        # Get values from UI components
        text_scale = self.scale_var.get()
        target_lang = self.target_lang_var.get()
        definition_lang = self.definition_lang_var.get()
        
        # Create settings dictionary
        new_settings = {
            'text_scale_factor': text_scale,
            'target_language': target_lang,
            'definition_language': definition_lang
        }
        
        # Add custom languages if any were added
        if 'custom_languages' in self.current_settings:
            new_settings['custom_languages'] = self.current_settings['custom_languages']
        
        # Publish settings update event
        self.publish_event('settings:update_requested', {
            'settings': new_settings
        })
        
        # Close dialog
        self._close_dialog()
    
    def _on_cancel(self, event=None):
        """Cancel and close dialog."""
        # Just close the dialog without saving
        self._close_dialog()
    
    def _on_reset(self):
        """Reset all settings to defaults."""
        # Get default settings from user model
        default_settings = self.user_model.get_default_settings()
        
        # Update UI with default values
        # Text scale
        self.scale_var.set(default_settings.get('text_scale_factor', 1.0))
        self._update_scale_value_label()
        self._update_preview_font()
        
        # Languages
        self.target_lang_var.set(default_settings.get('target_language', 'Czech'))
        self.definition_lang_var.set(default_settings.get('definition_language', 'English'))
    
    def _close_dialog(self):
        """Close the settings dialog."""
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None
            self.is_shown = False
    
    def update_scale(self, scale_factor: float):
        """
        Update UI scale based on given scale factor.
        
        Args:
            scale_factor: The text scale factor to apply
        """
        # Update the slider if it exists
        if self.scale_var:
            self.scale_var.set(scale_factor)
            self._update_scale_value_label()
            self._update_preview_font()