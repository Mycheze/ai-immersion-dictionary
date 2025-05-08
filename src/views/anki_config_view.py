"""
Anki Configuration View

This module provides a view for configuring Anki integration settings, including
connection settings, deck selection, note type selection, and field mapping.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from typing import Dict, List, Any, Optional, Callable

from .base_view import BaseView

class AnkiConfigView(BaseView):
    """
    View for configuring Anki integration settings.
    
    This view provides a user interface for configuring all aspects of Anki
    integration, including connection settings, deck selection, note type
    selection, and field mapping.
    
    Attributes:
        dialog: The configuration dialog window
        anki_model: Reference to the Anki model
        anki_service: Reference to the Anki service
        user_model: Reference to the user model
        settings: Dictionary of current settings
        event_bus: Event system for view-related notifications
    """
    
    def __init__(self, parent, anki_model, anki_service, user_model, event_bus=None):
        """
        Initialize the Anki configuration view.
        
        Args:
            parent: Parent window for the dialog
            anki_model: Reference to the Anki model
            anki_service: Reference to the Anki service
            user_model: Reference to the user model
            event_bus: Optional event bus for notifications
        """
        super().__init__(parent, event_bus)
        
        self.dialog = None
        self.anki_model = anki_model
        self.anki_service = anki_service
        self.user_model = user_model
        self.settings = self.user_model.get_settings().copy()
        
        # Initialize empty values
        self.decks = []
        self.note_types = []
        self.field_mappings = {}
        self.field_handling = {}
        self.fields = []
        self.is_shown = False
    
    def show(self, parent=None):
        """
        Show the Anki configuration dialog.
        
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
        self.settings = self.user_model.get_settings().copy()
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent_window)
        self.dialog.title("Anki Integration Configuration")
        self.dialog.geometry("800x800")
        self.dialog.transient(parent_window)  # Set to be on top of the parent window
        self.dialog.grab_set()  # Make it modal
        
        # Set minimum size
        self.dialog.minsize(750, 750)
        
        # Center the dialog on the parent window
        self.dialog.update_idletasks()
        self._center_on_parent(parent_window)
        
        # Create the dialog content
        self._create_dialog_content()
        
        # Load current settings into the dialog
        self._load_settings()
        
        # Refresh Anki data
        self._refresh_anki_data()
        
        # Bind events
        self.dialog.bind("<Escape>", self._on_cancel)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        self.is_shown = True
    
    def _center_on_parent(self, parent):
        """Center the dialog on the parent window."""
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # Calculate position
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        
        # Set position
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_dialog_content(self):
        """Create the content of the Anki configuration dialog."""
        # Create a container frame
        container = ttk.Frame(self.dialog)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Main frame with padding for content (tabs)
        main_frame = ttk.Frame(container, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create tabs
        self._create_connection_tab()
        self._create_decks_tab()
        self._create_note_types_tab()
        self._create_field_mapping_tab()
        self._create_preview_tab()
        
        # Fixed bottom frame
        bottom_frame = ttk.Frame(self.dialog, padding=10)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Add a separator above the buttons
        ttk.Separator(bottom_frame, orient="horizontal").pack(fill=tk.X, pady=5)
        
        # Buttons frame
        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Status label
        self.status_var = tk.StringVar()
        status_label = ttk.Label(button_frame, textvariable=self.status_var, foreground="gray")
        status_label.pack(side=tk.LEFT, padx=5)
        
        # Save button
        self.save_button = ttk.Button(button_frame, text="Save", command=self._on_save, width=10)
        self.save_button.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel, width=10).pack(side=tk.RIGHT, padx=5)
    
    def _create_connection_tab(self):
        """Create the connection settings tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Connection")
        
        # Connection settings frame
        connection_frame = ttk.LabelFrame(tab, text="Connection Settings", padding=10)
        connection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # URL
        url_frame = ttk.Frame(connection_frame)
        url_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(url_frame, text="Anki Connect URL:").pack(side=tk.LEFT, padx=(0, 5))
        self.url_var = tk.StringVar(value="http://localhost:8765")
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=40)
        url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Test connection button
        self.test_button = ttk.Button(url_frame, text="Test Connection", command=self._on_test_connection)
        self.test_button.pack(side=tk.LEFT, padx=5)
        
        # Connection status
        self.connection_status_var = tk.StringVar(value="Not connected")
        connection_status = ttk.Label(connection_frame, textvariable=self.connection_status_var)
        connection_status.pack(anchor=tk.W, pady=5)
        
        # Add a separator
        ttk.Separator(connection_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Integration options frame
        integration_frame = ttk.Frame(connection_frame)
        integration_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(integration_frame, text="Integration Options:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # Enable/Disable Anki integration
        self.anki_enabled_var = tk.BooleanVar(value=True)
        anki_enabled_cb = ttk.Checkbutton(
            integration_frame,
            text="Enable Anki integration",
            variable=self.anki_enabled_var
        )
        anki_enabled_cb.pack(anchor=tk.W, pady=2)
        
        # Auto-export checkbox
        self.auto_export_var = tk.BooleanVar(value=False)
        auto_export_cb = ttk.Checkbutton(
            integration_frame,
            text="Automatically export new entries to Anki",
            variable=self.auto_export_var
        )
        auto_export_cb.pack(anchor=tk.W, pady=2)
        
        # Skip confirmation checkbox
        self.skip_confirmation_var = tk.BooleanVar(value=False)
        skip_confirmation_cb = ttk.Checkbutton(
            integration_frame,
            text="Skip confirmation when exporting (export immediately)",
            variable=self.skip_confirmation_var
        )
        skip_confirmation_cb.pack(anchor=tk.W, pady=2)
        
        # Instructions
        instructions_frame = ttk.LabelFrame(tab, text="Setup Instructions", padding=10)
        instructions_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        instructions_text = scrolledtext.ScrolledText(
            instructions_frame, 
            wrap=tk.WORD, 
            width=60, 
            height=10
        )
        instructions_text.pack(fill=tk.BOTH, expand=True)
        
        instructions = (
            "To use Anki integration, you need to have:\n\n"
            "1. Anki installed on your computer\n"
            "2. AnkiConnect add-on installed in Anki\n"
            "   - Open Anki\n"
            "   - Go to Tools > Add-ons > Get Add-ons\n"
            "   - Enter code: 2055492159\n"
            "   - Restart Anki\n\n"
            "3. Anki must be running for the integration to work\n\n"
            "4. Default port is 8765, you shouldn't need to change it\n"
            "   unless you've configured AnkiConnect differently.\n\n"
            "5. Click 'Test Connection' to verify that the connection works."
        )
        
        instructions_text.insert(tk.END, instructions)
        instructions_text.config(state=tk.DISABLED)
    
    def _create_decks_tab(self):
        """Create the decks tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Decks")
        
        # Default deck frame
        default_deck_frame = ttk.LabelFrame(tab, text="Default Deck", padding=10)
        default_deck_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Default deck
        ttk.Label(default_deck_frame, text="Select default deck:").pack(anchor=tk.W, pady=(0, 5))
        self.default_deck_var = tk.StringVar()
        self.default_deck_combo = ttk.Combobox(
            default_deck_frame, 
            textvariable=self.default_deck_var,
            state="readonly",
            width=40
        )
        self.default_deck_combo.pack(anchor=tk.W, pady=(0, 5))
        
        # Refresh decks button
        refresh_button = ttk.Button(default_deck_frame, text="Refresh Decks", command=self._on_refresh_decks)
        refresh_button.pack(anchor=tk.W, pady=5)
        
        # Available decks frame
        available_decks_frame = ttk.LabelFrame(tab, text="Available Decks", padding=10)
        available_decks_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        # Decks listbox with scrollbar
        decks_frame = ttk.Frame(available_decks_frame)
        decks_frame.pack(fill=tk.BOTH, expand=True)
        
        self.decks_listbox = tk.Listbox(decks_frame, height=10)
        scrollbar = ttk.Scrollbar(decks_frame, orient="vertical", command=self.decks_listbox.yview)
        self.decks_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.decks_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind event to update selected deck
        self.decks_listbox.bind("<<ListboxSelect>>", self._on_deck_select)
    
    def _create_note_types_tab(self):
        """Create the note types tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Note Types")
        
        # Default note type frame
        default_note_type_frame = ttk.LabelFrame(tab, text="Default Note Type", padding=10)
        default_note_type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Default note type
        ttk.Label(default_note_type_frame, text="Select default note type:").pack(anchor=tk.W, pady=(0, 5))
        self.default_note_type_var = tk.StringVar()
        self.default_note_type_combo = ttk.Combobox(
            default_note_type_frame, 
            textvariable=self.default_note_type_var,
            state="readonly",
            width=40
        )
        self.default_note_type_combo.pack(anchor=tk.W, pady=(0, 5))
        
        # Refresh note types button
        refresh_button = ttk.Button(default_note_type_frame, text="Refresh Note Types", command=self._on_refresh_note_types)
        refresh_button.pack(anchor=tk.W, pady=5)
        
        # Available note types frame
        available_note_types_frame = ttk.LabelFrame(tab, text="Available Note Types", padding=10)
        available_note_types_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        # Note types listbox with scrollbar
        note_types_frame = ttk.Frame(available_note_types_frame)
        note_types_frame.pack(fill=tk.BOTH, expand=True)
        
        self.note_types_listbox = tk.Listbox(note_types_frame, height=10)
        scrollbar = ttk.Scrollbar(note_types_frame, orient="vertical", command=self.note_types_listbox.yview)
        self.note_types_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.note_types_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind event to update selected note type
        self.note_types_listbox.bind("<<ListboxSelect>>", self._on_note_type_select)
    
    def _create_field_mapping_tab(self):
        """Create the field mapping tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Field Mapping")
        
        # Note type selection
        note_type_frame = ttk.Frame(tab)
        note_type_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(note_type_frame, text="Configure mapping for:").pack(side=tk.LEFT, padx=(0, 5))
        self.mapping_note_type_var = tk.StringVar()
        self.mapping_note_type_combo = ttk.Combobox(
            note_type_frame, 
            textvariable=self.mapping_note_type_var,
            state="readonly",
            width=30
        )
        self.mapping_note_type_combo.pack(side=tk.LEFT, padx=5)
        self.mapping_note_type_combo.bind("<<ComboboxSelected>>", self._on_mapping_note_type_change)
        
        # Deck selection for this note type
        deck_frame = ttk.Frame(tab)
        deck_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(deck_frame, text="Deck for this note type:").pack(side=tk.LEFT, padx=(0, 5))
        self.note_type_deck_var = tk.StringVar()
        self.note_type_deck_combo = ttk.Combobox(
            deck_frame, 
            textvariable=self.note_type_deck_var,
            state="readonly",
            width=30
        )
        self.note_type_deck_combo.pack(side=tk.LEFT, padx=5)
        
        # Field mapping frame
        field_mapping_frame = ttk.LabelFrame(tab, text="Field Mapping", padding=10)
        field_mapping_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        # Create a scrollable canvas for the field mappings
        canvas = tk.Canvas(field_mapping_frame)
        scrollbar = ttk.Scrollbar(field_mapping_frame, orient="vertical", command=canvas.yview)
        self.field_mapping_frame_inner = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create a window inside the canvas containing the frame
        self.field_mapping_window = canvas.create_window((0, 0), window=self.field_mapping_frame_inner, anchor=tk.NW)
        
        # Configure the canvas to resize the window if the frame changes size
        def configure_canvas(event):
            canvas.configure(scrollregion=canvas.bbox("all"), width=event.width)
            canvas.itemconfig(self.field_mapping_window, width=event.width)
        
        self.field_mapping_frame_inner.bind("<Configure>", configure_canvas)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self.field_mapping_window, width=e.width))
        
        # Field mappings will be added dynamically
        self.field_mapping_vars = {}
        self.field_handling_vars = {}
        self.field_default_vars = {}
    
    def _create_preview_tab(self):
        """Create the preview tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Preview")
        
        # Preview frame
        preview_frame = ttk.LabelFrame(tab, text="Export Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Export example frame
        example_frame = ttk.Frame(preview_frame)
        example_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(example_frame, text="Sample dictionary entry will be displayed here").pack(anchor=tk.W)
        
        # JSON Preview
        json_frame = ttk.LabelFrame(preview_frame, text="JSON Preview", padding=10)
        json_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        self.json_preview = scrolledtext.ScrolledText(json_frame, wrap=tk.WORD, width=60, height=10)
        self.json_preview.pack(fill=tk.BOTH, expand=True)
        
        # Sample data for preview
        sample_data = {
            "headword": "example",
            "part_of_speech": "noun",
            "metadata": {
                "source_language": "English",
                "target_language": "Czech",
                "definition_language": "English"
            },
            "meanings": [
                {
                    "definition": "An instance typical of its class",
                    "examples": [
                        {
                            "sentence": "This is just an example.",
                            "translation": "Toto je jen příklad."
                        }
                    ]
                }
            ]
        }
        
        # Display sample data
        self.json_preview.insert(tk.END, json.dumps(sample_data, indent=2))
        self.json_preview.config(state=tk.DISABLED)
    
    def _load_settings(self):
        """Load current settings into the dialog."""
        # Connection settings
        self.url_var.set(self.settings.get('anki_url', 'http://localhost:8765'))
        self.anki_enabled_var.set(self.settings.get('anki_enabled', False))
        self.auto_export_var.set(self.settings.get('auto_export', False))
        self.skip_confirmation_var.set(self.settings.get('skip_confirmation', False))
        
        # Default deck and note type
        self.default_deck_var.set(self.settings.get('default_deck', ''))
        self.default_note_type_var.set(self.settings.get('default_note_type', ''))
        
        # Field mappings will be loaded after note types are loaded
    
    def _refresh_anki_data(self):
        """Refresh data from Anki."""
        # Update connection status
        self._update_connection_status()
        
        # Try to load decks and note types
        if self.anki_service.get_connection_status():
            self._load_decks()
            self._load_note_types()
    
    def _update_connection_status(self):
        """Update the connection status display."""
        if self.anki_service.get_connection_status():
            self.connection_status_var.set("Connected to Anki")
            self.connection_status_var.config(foreground="green")
        else:
            self.connection_status_var.set("Not connected to Anki")
            self.connection_status_var.config(foreground="red")
    
    def _load_decks(self):
        """Load decks from Anki."""
        try:
            self.decks = self.anki_service.list_decks()
            
            # Update decks listbox
            self.decks_listbox.delete(0, tk.END)
            for deck in self.decks:
                self.decks_listbox.insert(tk.END, deck)
            
            # Update deck comboboxes
            self.default_deck_combo['values'] = self.decks
            self.note_type_deck_combo['values'] = self.decks
            
            # Set default deck if it exists
            default_deck = self.settings.get('default_deck', '')
            if default_deck and default_deck in self.decks:
                self.default_deck_var.set(default_deck)
                
            # Select default deck in listbox
            if default_deck:
                try:
                    index = self.decks.index(default_deck)
                    self.decks_listbox.selection_set(index)
                    self.decks_listbox.see(index)
                except ValueError:
                    pass
                    
        except Exception as e:
            self.status_var.set(f"Error loading decks: {str(e)}")
    
    def _load_note_types(self):
        """Load note types from Anki."""
        try:
            self.note_types = self.anki_service.list_note_types()
            
            # Update note types listbox
            self.note_types_listbox.delete(0, tk.END)
            for note_type in self.note_types:
                self.note_types_listbox.insert(tk.END, note_type)
            
            # Update note type comboboxes
            self.default_note_type_combo['values'] = self.note_types
            self.mapping_note_type_combo['values'] = self.note_types
            
            # Set default note type if it exists
            default_note_type = self.settings.get('default_note_type', '')
            if default_note_type and default_note_type in self.note_types:
                self.default_note_type_var.set(default_note_type)
                self.mapping_note_type_var.set(default_note_type)
                
                # Load field mappings for this note type
                self._load_field_mappings(default_note_type)
                
            # Select default note type in listbox
            if default_note_type:
                try:
                    index = self.note_types.index(default_note_type)
                    self.note_types_listbox.selection_set(index)
                    self.note_types_listbox.see(index)
                except ValueError:
                    pass
                    
        except Exception as e:
            self.status_var.set(f"Error loading note types: {str(e)}")
    
    def _load_field_mappings(self, note_type):
        """Load field mappings for the selected note type."""
        if not note_type or not self.anki_service.get_connection_status():
            return
            
        try:
            # Get fields for this note type
            self.fields = self.anki_service.get_note_type_fields(note_type)
            
            # Get saved mappings for this note type
            note_types_config = self.settings.get('note_types', {})
            note_type_config = note_types_config.get(note_type, {})
            field_mappings = note_type_config.get('field_mappings', {})
            field_handling = note_type_config.get('empty_field_handling', {})
            
            # Get deck for this note type
            deck = note_type_config.get('deck', self.settings.get('default_deck', ''))
            if deck and deck in self.decks:
                self.note_type_deck_var.set(deck)
            
            # Clear existing field mapping widgets
            for widget in self.field_mapping_frame_inner.winfo_children():
                widget.destroy()
                
            # Clear variables
            self.field_mapping_vars = {}
            self.field_handling_vars = {}
            self.field_default_vars = {}
            
            # Create new field mapping widgets
            ttk.Label(self.field_mapping_frame_inner, text="Anki Field", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            ttk.Label(self.field_mapping_frame_inner, text="Dictionary Field Path", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
            ttk.Label(self.field_mapping_frame_inner, text="Empty Field Handling", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
            ttk.Label(self.field_mapping_frame_inner, text="Default Value", font=("Arial", 10, "bold")).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
            
            # Dictionary field path examples
            examples = [
                "headword",
                "part_of_speech",
                "metadata.target_language",
                "metadata.definition_language",
                "meanings.0.definition",
                "meanings.0.examples.0.sentence",
                "meanings.0.examples.0.translation",
                "selected_meaning.definition",
                "selected_example.sentence",
                "selected_example.translation"
            ]
            
            # Create field mapping for each Anki field
            for i, field in enumerate(self.fields):
                # Field name
                ttk.Label(self.field_mapping_frame_inner, text=field).grid(row=i+1, column=0, padx=5, pady=5, sticky=tk.W)
                
                # Dictionary field path
                self.field_mapping_vars[field] = tk.StringVar(value=field_mappings.get(field, ""))
                field_mapping_combo = ttk.Combobox(self.field_mapping_frame_inner, textvariable=self.field_mapping_vars[field], width=30)
                field_mapping_combo['values'] = examples
                field_mapping_combo.grid(row=i+1, column=1, padx=5, pady=5, sticky=tk.W)
                
                # Empty field handling
                handling_config = field_handling.get(field, {})
                self.field_handling_vars[field] = tk.StringVar(value=handling_config.get('action', 'placeholder'))
                handling_combo = ttk.Combobox(self.field_mapping_frame_inner, textvariable=self.field_handling_vars[field], state="readonly", width=15)
                handling_combo['values'] = ["skip", "default", "placeholder", "error"]
                handling_combo.grid(row=i+1, column=2, padx=5, pady=5, sticky=tk.W)
                
                # Default value
                self.field_default_vars[field] = tk.StringVar(value=handling_config.get('default', f"[No {field}]"))
                default_entry = ttk.Entry(self.field_mapping_frame_inner, textvariable=self.field_default_vars[field], width=20)
                default_entry.grid(row=i+1, column=3, padx=5, pady=5, sticky=tk.W)
                
        except Exception as e:
            self.status_var.set(f"Error loading field mappings: {str(e)}")
    
    def _get_config_from_ui(self):
        """Get configuration from UI components."""
        config = {
            'anki_url': self.url_var.get(),
            'anki_enabled': self.anki_enabled_var.get(),
            'auto_export': self.auto_export_var.get(),
            'skip_confirmation': self.skip_confirmation_var.get(),
            'default_deck': self.default_deck_var.get(),
            'default_note_type': self.default_note_type_var.get()
        }
        
        # Get note type configurations
        note_types_config = self.settings.get('note_types', {}).copy()
        current_note_type = self.mapping_note_type_var.get()
        
        if current_note_type:
            # Create or update config for this note type
            note_type_config = note_types_config.get(current_note_type, {})
            
            # Set deck for this note type
            note_type_config['deck'] = self.note_type_deck_var.get()
            
            # Get field mappings
            field_mappings = {}
            for field, var in self.field_mapping_vars.items():
                mapping = var.get()
                if mapping:
                    field_mappings[field] = mapping
                    
            note_type_config['field_mappings'] = field_mappings
            
            # Get empty field handling
            empty_field_handling = {}
            for field, handling_var in self.field_handling_vars.items():
                handling = handling_var.get()
                if handling:
                    field_config = {'action': handling}
                    
                    # Add default value if action is 'default'
                    if handling == 'default':
                        default_value = self.field_default_vars[field].get()
                        field_config['default'] = default_value
                        
                    empty_field_handling[field] = field_config
                    
            note_type_config['empty_field_handling'] = empty_field_handling
            
            # Update the note type config
            note_types_config[current_note_type] = note_type_config
            
        # Update note types configuration
        config['note_types'] = note_types_config
        
        return config
    
    # Event handlers
    
    def _on_test_connection(self):
        """Handle test connection button click."""
        url = self.url_var.get()
        
        # Update the Anki service URL
        self.anki_service.url = url
        
        # Test the connection
        if self.anki_service.refresh_connection_status():
            self.connection_status_var.set("Connected to Anki")
            self.status_var.set("Connection successful")
            
            # Update decks and note types
            self._load_decks()
            self._load_note_types()
        else:
            self.connection_status_var.set("Failed to connect to Anki")
            self.status_var.set("Connection failed - make sure Anki is running with AnkiConnect addon")
    
    def _on_refresh_decks(self):
        """Handle refresh decks button click."""
        self._load_decks()
        self.status_var.set("Decks refreshed")
    
    def _on_refresh_note_types(self):
        """Handle refresh note types button click."""
        self._load_note_types()
        self.status_var.set("Note types refreshed")
    
    def _on_deck_select(self, event):
        """Handle deck selection in listbox."""
        selection = self.decks_listbox.curselection()
        if selection:
            index = selection[0]
            deck = self.decks_listbox.get(index)
            self.default_deck_var.set(deck)
    
    def _on_note_type_select(self, event):
        """Handle note type selection in listbox."""
        selection = self.note_types_listbox.curselection()
        if selection:
            index = selection[0]
            note_type = self.note_types_listbox.get(index)
            self.default_note_type_var.set(note_type)
            self.mapping_note_type_var.set(note_type)
            
            # Update field mappings
            self._load_field_mappings(note_type)
    
    def _on_mapping_note_type_change(self, event):
        """Handle note type change in mapping tab."""
        note_type = self.mapping_note_type_var.get()
        self._load_field_mappings(note_type)
    
    def _on_save(self, event=None):
        """Save settings and close dialog."""
        # Get configuration from UI
        config = self._get_config_from_ui()
        
        # Publish settings update event
        self.publish_event('settings:anki_config_updated', config)
        
        # Close dialog
        self._close_dialog()
    
    def _on_cancel(self, event=None):
        """Cancel and close dialog."""
        self._close_dialog()
    
    def _close_dialog(self):
        """Close the dialog."""
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None
            self.is_shown = False