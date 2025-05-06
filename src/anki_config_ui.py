import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from typing import Dict, List, Any, Optional, Callable
import threading
from anki_integration import AnkiConnector, AnkiFieldMapper, EmptyFieldHandler


class AnkiConfigDialog(tk.Toplevel):
    """
    Dialog for configuring Anki integration settings.
    
    Provides UI for setting up AnkiConnect connection, deck selection,
    note type selection, and field mapping configuration.
    """
    
    def __init__(self, parent, user_settings):
        """
        Initialize the Anki configuration dialog.
        
        Args:
            parent: The parent window
            user_settings: The UserSettings instance
        """
        super().__init__(parent)
        self.parent = parent
        self.user_settings = user_settings
        self.settings = user_settings.get_settings()
        
        # Initialize empty values
        self.anki_connector = None
        self.decks = []
        self.note_types = []
        self.field_mappings = {}
        self.field_handling = {}
        self.fields = []
        
        # Setup dialog
        self.title("Anki Integration Configuration")
        self.geometry("800x700")  # Increased size to ensure buttons are visible
        self.transient(parent)  # Set to be on top of the main window
        self.grab_set()  # Modal dialog
        self.minsize(750, 650)  # Set minimum size to ensure buttons are always visible
        
        # Center the dialog on the parent window
        self.update_idletasks()
        self.center_on_parent()
        
        # Create dialog content
        self.create_widgets()
        
        # Load saved settings
        self.load_settings()
        
        # Initialize anki connector with current URL
        self.init_anki_connector()
    
    def center_on_parent(self):
        """Center the dialog on the parent window"""
        width = self.winfo_width()
        height = self.winfo_height()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Calculate position
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        
        # Set position
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """Create the widgets for the dialog"""
        # Create a container frame to ensure proper layout
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Main frame with padding for content (tabs)
        main_frame = ttk.Frame(container, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create tabs
        self.create_connection_tab()
        self.create_decks_tab()
        self.create_note_types_tab()
        self.create_field_mapping_tab()
        self.create_preview_tab()
        
        # Fixed bottom frame that won't scroll away (outside the scrollable area)
        bottom_frame = ttk.Frame(self, padding=10)
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
        self.save_button = ttk.Button(button_frame, text="Save", command=self.save_settings, width=10)
        self.save_button.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        ttk.Button(button_frame, text="Cancel", command=self.destroy, width=10).pack(side=tk.RIGHT, padx=5)
    
    def create_connection_tab(self):
        """Create the connection settings tab"""
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
        self.test_button = ttk.Button(url_frame, text="Test Connection", command=self.test_connection)
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
    
    def create_decks_tab(self):
        """Create the decks tab"""
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
        refresh_button = ttk.Button(default_deck_frame, text="Refresh Decks", command=self.refresh_decks)
        refresh_button.pack(anchor=tk.W, pady=5)
        
        # Available decks frame
        available_decks_frame = ttk.LabelFrame(tab, text="Available Decks", padding=10)
        available_decks_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        # Decks listbox
        self.decks_listbox = tk.Listbox(available_decks_frame, height=10)
        self.decks_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Bind event to update selected deck
        self.decks_listbox.bind("<<ListboxSelect>>", self.on_deck_select)
    
    def create_note_types_tab(self):
        """Create the note types tab"""
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
        refresh_button = ttk.Button(default_note_type_frame, text="Refresh Note Types", command=self.refresh_note_types)
        refresh_button.pack(anchor=tk.W, pady=5)
        
        # Available note types frame
        available_note_types_frame = ttk.LabelFrame(tab, text="Available Note Types", padding=10)
        available_note_types_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        # Note types listbox
        self.note_types_listbox = tk.Listbox(available_note_types_frame, height=10)
        self.note_types_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Bind event to update selected note type
        self.note_types_listbox.bind("<<ListboxSelect>>", self.on_note_type_select)
    
    def create_field_mapping_tab(self):
        """Create the field mapping tab"""
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
        self.mapping_note_type_combo.bind("<<ComboboxSelected>>", self.on_mapping_note_type_change)
        
        # Tags frame
        tags_frame = ttk.LabelFrame(tab, text="Tags", padding=10)
        tags_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(tags_frame, text="Default tags (comma-separated):").pack(anchor=tk.W, pady=(0, 5))
        self.tags_var = tk.StringVar()
        tags_entry = ttk.Entry(tags_frame, textvariable=self.tags_var, width=40)
        tags_entry.pack(fill=tk.X, pady=(0, 5))
        
        # Field mapping frame
        field_mapping_frame = ttk.LabelFrame(tab, text="Field Mapping", padding=10)
        field_mapping_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollable frame for field mappings
        self.mapping_canvas = tk.Canvas(field_mapping_frame)
        scrollbar = ttk.Scrollbar(field_mapping_frame, orient="vertical", command=self.mapping_canvas.yview)
        self.mapping_frame = ttk.Frame(self.mapping_canvas)
        
        self.mapping_frame.bind(
            "<Configure>",
            lambda e: self.mapping_canvas.configure(scrollregion=self.mapping_canvas.bbox("all"))
        )
        
        self.mapping_canvas.create_window((0, 0), window=self.mapping_frame, anchor="nw")
        self.mapping_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.mapping_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Help frame with instructions
        help_frame = ttk.LabelFrame(tab, text="Instructions", padding=10)
        help_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Instructions text
        instructions_text = (
            "1. Select what dictionary data should go into each Anki field using the dropdowns\n"
            "2. Use the '?' button for detailed help on available field paths\n"
            "3. Choose what happens if a field is empty (skip, default value, placeholder, or error)\n"
            "4. Click 'Update Preview' to see how your note will look in Anki"
        )
        
        help_label = ttk.Label(help_frame, text=instructions_text, justify=tk.LEFT)
        help_label.pack(anchor=tk.W)
    
    def create_preview_tab(self):
        """Create the preview tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Preview")
        
        # Info label
        ttk.Label(
            tab, 
            text="This tab shows a preview of how fields will be mapped for export.",
            wraplength=500
        ).pack(anchor=tk.W, pady=5)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(tab, text="Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Preview text
        self.preview_text = scrolledtext.ScrolledText(
            preview_frame,
            wrap=tk.WORD,
            width=60,
            height=15
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Update preview button
        ttk.Button(tab, text="Update Preview", command=self.update_preview).pack(anchor=tk.W, pady=5)
    
    def load_settings(self):
        """Load saved Anki settings from user settings"""
        # Get Anki settings
        anki_enabled = self.settings.get('anki_enabled', False)
        anki_url = self.settings.get('anki_url', 'http://localhost:8765')
        default_deck = self.settings.get('default_deck', '')
        default_note_type = self.settings.get('default_note_type', '')
        auto_export = self.settings.get('auto_export', False)
        skip_confirmation = self.settings.get('skip_confirmation', False)
        tags = self.settings.get('tags', [])
        
        # Set values in UI
        self.url_var.set(anki_url)
        self.default_deck_var.set(default_deck)
        self.default_note_type_var.set(default_note_type)
        self.mapping_note_type_var.set(default_note_type)
        self.anki_enabled_var.set(anki_enabled)
        self.auto_export_var.set(auto_export)
        self.skip_confirmation_var.set(skip_confirmation)
        self.tags_var.set(', '.join(tags) if isinstance(tags, list) else tags)
        
        # Connect to Anki and load decks/note types
        if anki_enabled:
            self.refresh_decks()
            self.refresh_note_types()
            self.update_field_mapping_ui()
    
    def init_anki_connector(self):
        """Initialize the AnkiConnect connector"""
        url = self.url_var.get().strip()
        if url:
            self.anki_connector = AnkiConnector(url)
            # Test connection in background
            self.test_connection()
    
    def test_connection(self):
        """Test the connection to AnkiConnect"""
        self.test_button.config(state=tk.DISABLED)
        self.connection_status_var.set("Testing connection...")
        self.update_idletasks()
        
        # Run test in background thread
        def test():
            url = self.url_var.get().strip()
            self.anki_connector = AnkiConnector(url)
            
            try:
                connected = self.anki_connector.test_connection()
                if connected:
                    self.connection_status_var.set("Connected successfully!")
                    # Load decks and note types
                    self.refresh_decks()
                    self.refresh_note_types()
                else:
                    self.connection_status_var.set("Failed to connect to Anki.")
            except Exception as e:
                self.connection_status_var.set(f"Error: {str(e)}")
            finally:
                self.test_button.config(state=tk.NORMAL)
        
        threading.Thread(target=test).start()
    
    def refresh_decks(self):
        """Refresh the list of available decks"""
        if not self.anki_connector:
            self.status_var.set("Not connected to Anki")
            return
            
        try:
            self.decks = self.anki_connector.list_decks()
            
            # Update listbox
            self.decks_listbox.delete(0, tk.END)
            for deck in sorted(self.decks):
                self.decks_listbox.insert(tk.END, deck)
                
            # Update combobox
            self.default_deck_combo['values'] = sorted(self.decks)
            
            # Select current default if it exists
            current_default = self.default_deck_var.get()
            if current_default in self.decks:
                self.default_deck_var.set(current_default)
            elif self.decks:
                self.default_deck_var.set(self.decks[0])
                
            self.status_var.set(f"Loaded {len(self.decks)} decks")
        except Exception as e:
            self.status_var.set(f"Error loading decks: {str(e)}")
    
    def refresh_note_types(self):
        """Refresh the list of available note types"""
        if not self.anki_connector:
            self.status_var.set("Not connected to Anki")
            return
            
        try:
            self.note_types = self.anki_connector.list_note_types()
            
            # Update listbox
            self.note_types_listbox.delete(0, tk.END)
            for note_type in sorted(self.note_types):
                self.note_types_listbox.insert(tk.END, note_type)
                
            # Update comboboxes
            self.default_note_type_combo['values'] = sorted(self.note_types)
            self.mapping_note_type_combo['values'] = sorted(self.note_types)
            
            # Select current default if it exists
            current_default = self.default_note_type_var.get()
            if current_default in self.note_types:
                self.default_note_type_var.set(current_default)
                self.mapping_note_type_var.set(current_default)
                
                # Also update the field mapping UI
                self.update_field_mapping_ui()
            elif self.note_types:
                self.default_note_type_var.set(self.note_types[0])
                self.mapping_note_type_var.set(self.note_types[0])
                self.update_field_mapping_ui()
                
            self.status_var.set(f"Loaded {len(self.note_types)} note types")
        except Exception as e:
            self.status_var.set(f"Error loading note types: {str(e)}")
    
    def get_available_field_paths(self):
        """Get a list of available field paths for the dropdown"""
        # Basic paths
        basic_paths = [
            "headword",
            "part_of_speech",
            "metadata.source_language",
            "metadata.target_language",
            "metadata.definition_language"
        ]
        
        # Meaning paths
        meaning_paths = [
            "meanings.0.definition",
            "meanings.0.grammar.gender",
            "meanings.0.grammar.plurality",
            "meanings.0.grammar.tense",
            "meanings.0.grammar.case",
            "meanings.0.examples.0.sentence",
            "meanings.0.examples.0.translation",
            "meanings.1.definition",
            "meanings.1.examples.0.sentence",
            "meanings.1.examples.0.translation"
        ]
        
        # Selected item paths
        selected_paths = [
            "selected_meaning.definition",
            "selected_meaning.grammar.gender",
            "selected_meaning.grammar.plurality",
            "selected_meaning.grammar.tense",
            "selected_meaning.grammar.case",
            "selected_example.sentence",
            "selected_example.translation"
        ]
        
        return basic_paths + meaning_paths + selected_paths
    
    def update_field_mapping_ui(self):
        """Update the field mapping UI with fields from selected note type"""
        note_type = self.mapping_note_type_var.get()
        if not note_type or not self.anki_connector:
            return
            
        # Clear existing fields
        for widget in self.mapping_frame.winfo_children():
            widget.destroy()
            
        try:
            # Get fields for note type
            self.fields = self.anki_connector.get_note_type_fields(note_type)
            
            # Get current mappings for this note type
            note_types_config = self.settings.get('note_types', {})
            note_config = note_types_config.get(note_type, {})
            mappings = note_config.get('field_mappings', {})
            empty_handling = note_config.get('empty_field_handling', {})
            
            # Get available field paths for dropdown
            available_paths = self.get_available_field_paths()
            
            # Section label
            section_label = ttk.Label(
                self.mapping_frame, 
                text="Map Anki Fields to Dictionary Data", 
                font=("Arial", 10, "bold")
            )
            section_label.pack(anchor=tk.W, pady=(5, 10))
            
            # Create frame for each field
            for i, field in enumerate(self.fields):
                field_frame = ttk.Frame(self.mapping_frame)
                field_frame.pack(fill=tk.X, pady=5)
                
                # Field name
                ttk.Label(field_frame, text=f"{field}:", width=15).pack(side=tk.LEFT, padx=5)
                
                # Field mapping dropdown instead of entry
                mapping_var = tk.StringVar(value=mappings.get(field, ""))
                mapping_combo = ttk.Combobox(
                    field_frame, 
                    textvariable=mapping_var,
                    values=available_paths,
                    width=30
                )
                mapping_combo.pack(side=tk.LEFT, padx=5)
                
                # Add a tooltip button to explain the mapping
                help_button = ttk.Button(
                    field_frame, 
                    text="?", 
                    width=2,
                    command=lambda: self.show_field_path_help()
                )
                help_button.pack(side=tk.LEFT)
                
                # Store reference to variable
                self.field_mappings[field] = mapping_var
                
                # Empty field handling
                handling_frame = ttk.Frame(field_frame)
                handling_frame.pack(side=tk.LEFT, padx=5)
                
                ttk.Label(handling_frame, text="If empty:").pack(side=tk.LEFT)
                
                # Get current handling for this field
                field_handling = empty_handling.get(field, {"action": "placeholder"})
                action = field_handling.get("action", "placeholder")
                
                # Action dropdown
                action_var = tk.StringVar(value=action)
                action_combo = ttk.Combobox(
                    handling_frame,
                    textvariable=action_var,
                    values=["skip", "default", "placeholder", "error"],
                    state="readonly",
                    width=10
                )
                action_combo.pack(side=tk.LEFT, padx=5)
                
                # Default value entry (only visible for 'default' action)
                default_frame = ttk.Frame(handling_frame)
                default_frame.pack(side=tk.LEFT)
                
                default_label = ttk.Label(default_frame, text="Default:")
                default_var = tk.StringVar(value=field_handling.get("default", ""))
                default_entry = ttk.Entry(default_frame, textvariable=default_var, width=15)
                
                # Show/hide default value entry based on action
                def toggle_default_visibility(*args):
                    if action_var.get() == "default":
                        default_label.pack(side=tk.LEFT, padx=(5, 0))
                        default_entry.pack(side=tk.LEFT, padx=(0, 5))
                    else:
                        default_label.pack_forget()
                        default_entry.pack_forget()
                
                action_var.trace_add("write", toggle_default_visibility)
                toggle_default_visibility()
                
                # Store references to variables
                self.field_handling[field] = (action_var, default_var)
            
            # Update the preview
            self.update_preview()
            
        except Exception as e:
            self.status_var.set(f"Error loading fields: {str(e)}")
    
    def show_field_path_help(self):
        """Show help dialog for field paths"""
        help_dialog = tk.Toplevel(self)
        help_dialog.title("Field Path Help")
        help_dialog.geometry("550x550")
        help_dialog.transient(self)
        help_dialog.grab_set()
        
        # Center the dialog
        help_dialog.update_idletasks()
        width = help_dialog.winfo_width()
        height = help_dialog.winfo_height()
        x = (help_dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (help_dialog.winfo_screenheight() // 2) - (height // 2)
        help_dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Content frame
        content_frame = ttk.Frame(help_dialog, padding=15)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(
            content_frame,
            text="Understanding Field Paths",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Help text
        help_text = scrolledtext.ScrolledText(
            content_frame, 
            wrap=tk.WORD,
            width=60,
            height=20
        )
        help_text.pack(fill=tk.BOTH, expand=True, pady=10)
        
        explanation = """
Field paths tell Anki how to extract data from the dictionary entry.

Basic Fields:
- headword: The word being defined
- part_of_speech: Grammatical category (noun, verb, etc.)
- metadata.source_language: Your base language
- metadata.target_language: Language you're learning
- metadata.definition_language: Language of definitions

Meanings and Examples:
- meanings.0.definition: First definition
- meanings.1.definition: Second definition
- meanings.0.grammar.gender: Grammatical gender of first meaning
- meanings.0.examples.0.sentence: First example of first meaning
- meanings.0.examples.0.translation: Translation of first example

Selected Items (when exporting one specific example):
- selected_meaning.definition: The currently selected definition
- selected_example.sentence: The selected example sentence
- selected_example.translation: Translation of selected example

Note: Numbers (0, 1, etc.) refer to array indices (starting at 0 for the first item).
        """
        
        help_text.insert(tk.END, explanation)
        help_text.config(state=tk.DISABLED)
        
        # Close button
        ttk.Button(
            content_frame,
            text="Close",
            command=help_dialog.destroy
        ).pack(side=tk.RIGHT, pady=10)
    
    def update_preview(self):
        """Update the preview of field mappings"""
        note_type = self.mapping_note_type_var.get()
        if not note_type or not self.fields:
            return
            
        # Create a sample entry
        sample_entry = {
            "headword": "example",
            "part_of_speech": "noun",
            "metadata": {
                "source_language": "English",
                "target_language": "Czech",
                "definition_language": "English"
            },
            "meanings": [
                {
                    "definition": "a representative form or pattern",
                    "grammar": {
                        "gender": "masculine",
                        "plurality": "singular"
                    },
                    "examples": [
                        {
                            "sentence": "Tohle je příklad.",
                            "translation": "This is an example."
                        }
                    ]
                }
            ],
            "selected_meaning": {
                "definition": "a representative form or pattern",
                "grammar": {
                    "gender": "masculine",
                    "plurality": "singular"
                }
            },
            "selected_example": {
                "sentence": "Tohle je příklad.",
                "translation": "This is an example."
            }
        }
        
        # Get current mappings
        field_mappings = {}
        for field, var in self.field_mappings.items():
            field_mappings[field] = var.get()
            
        # Get current empty field handling
        empty_field_handling = {}
        for field, (action_var, default_var) in self.field_handling.items():
            action = action_var.get()
            if action == "default":
                empty_field_handling[field] = {
                    "action": action,
                    "default": default_var.get()
                }
            else:
                empty_field_handling[field] = {
                    "action": action
                }
                
        # Create field mapper
        field_mapper = AnkiFieldMapper(field_mappings, empty_field_handling)
        
        # Map fields
        mapped_fields = field_mapper.map_entry_to_fields(sample_entry)
        
        # Update preview
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        
        self.preview_text.insert(tk.END, f"Note Type: {note_type}\n\n")
        
        for field in self.fields:
            mapping = field_mappings.get(field, "")
            value = mapped_fields.get(field, "<not mapped>")
            
            self.preview_text.insert(tk.END, f"{field}:\n")
            self.preview_text.insert(tk.END, f"  Mapping: {mapping}\n")
            self.preview_text.insert(tk.END, f"  Value: {value}\n\n")
            
        self.preview_text.config(state=tk.DISABLED)
    
    def on_deck_select(self, event):
        """Handle selection of a deck from the list"""
        selection = self.decks_listbox.curselection()
        if selection:
            selected_deck = self.decks_listbox.get(selection[0])
            self.default_deck_var.set(selected_deck)
    
    def on_note_type_select(self, event):
        """Handle selection of a note type from the list"""
        selection = self.note_types_listbox.curselection()
        if selection:
            selected_note_type = self.note_types_listbox.get(selection[0])
            self.default_note_type_var.set(selected_note_type)
            self.mapping_note_type_var.set(selected_note_type)
            self.update_field_mapping_ui()
    
    def on_mapping_note_type_change(self, event):
        """Handle change of note type in field mapping tab"""
        self.update_field_mapping_ui()
    
    def save_settings(self):
        """Save settings back to user settings"""
        # Get values from UI
        anki_url = self.url_var.get().strip()
        default_deck = self.default_deck_var.get()
        default_note_type = self.default_note_type_var.get()
        auto_export = self.auto_export_var.get()
        
        # Get tags
        tags_str = self.tags_var.get().strip()
        tags = [tag.strip() for tag in tags_str.split(',')] if tags_str else []
        
        # Get note type configurations
        note_types_config = self.settings.get('note_types', {})
        
        # Update current note type configuration
        current_note_type = self.mapping_note_type_var.get()
        if current_note_type:
            # Get mappings
            field_mappings = {}
            for field, var in self.field_mappings.items():
                mapping = var.get().strip()
                if mapping:
                    field_mappings[field] = mapping
                    
            # Get empty field handling
            empty_field_handling = {}
            for field, (action_var, default_var) in self.field_handling.items():
                action = action_var.get()
                if action == "default":
                    empty_field_handling[field] = {
                        "action": action,
                        "default": default_var.get()
                    }
                else:
                    empty_field_handling[field] = {
                        "action": action
                    }
                    
            # Update configuration
            note_types_config[current_note_type] = {
                "deck": default_deck,
                "field_mappings": field_mappings,
                "empty_field_handling": empty_field_handling
            }
            
        # Create settings dictionary
        new_settings = {
            'anki_enabled': self.anki_enabled_var.get(),
            'anki_url': anki_url,
            'default_deck': default_deck,
            'default_note_type': default_note_type,
            'note_types': note_types_config,
            'auto_export': auto_export,
            'skip_confirmation': self.skip_confirmation_var.get(),
            'tags': tags
        }
        
        # Update settings
        self.user_settings.update_settings(new_settings)
        
        # Show success message
        self.status_var.set("Settings saved successfully")
        
        # Close dialog after a delay
        self.after(1000, self.destroy)