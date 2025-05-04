import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import os
import sys
import time
from dictionary_engine import DictionaryEngine
from user_settings import UserSettings
from database_manager import DatabaseManager
try:
    # On Windows and macOS
    import pyperclip
except ImportError:
    # On Linux (requires additional packages)
    try:
        import subprocess
        def paste():
            try:
                return subprocess.check_output(['xclip', '-selection', 'clipboard', '-o']).decode('utf-8')
            except Exception:
                try:
                    return subprocess.check_output(['xsel', '-b']).decode('utf-8')
                except Exception:
                    return ""
        
        class Pyperclip:
            @staticmethod
            def paste():
                return paste()
        
        pyperclip = Pyperclip
    except Exception as e:
        print(f"Failed to set up clipboard fallback: {e}")
        # Create a dummy clipboard class for graceful fallback
        class DummyClipboard:
            @staticmethod
            def paste():
                return ""
        
        pyperclip = DummyClipboard
        print("Using dummy clipboard implementation")

class DictionaryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-Powered Immersion Dictionary")
        self.root.geometry("900x760")
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
        
        # Load user settings first
        self.user_settings = UserSettings()
        
        # Initialize dictionary engine with user settings
        self.dictionary_engine = DictionaryEngine(db_manager=self.db_manager, user_settings=self.user_settings)
        
        # Load existing dictionary data from database
        self.filtered_data = []
        
        # Store the current entry for delete/regenerate operations
        self.current_entry = None
        
        # Clipboard monitoring state
        self.clipboard_monitoring = False
        self.last_clipboard_content = ""
        self.clipboard_check_interval = 500  # milliseconds
        
        # Setup the GUI layout
        self.setup_gui()
        
        # Apply saved user settings
        self.apply_saved_settings()
        
        # Update language options to include custom languages
        self.update_language_options()
        
        # Load initial data
        self.reload_data()
    
    def setup_gui(self):
        # Create the main frame structure
        self.create_frames()
        
        # Create the menu and toolbar
        self.create_toolbar()
        
        # Create the search and entry panels
        self.create_search_panel()
        self.create_entry_display()
        
        # Create the bottom search bar for new entries
        self.create_search_bar()
        
        # Create status bar
        self.create_status_bar()
        
        # Make sure the bottom panel is visible
        self.bottom_panel.update()

    def create_status_bar(self):
        """Create a status bar to show current language settings"""
        self.status_bar = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = tk.Label(self.status_bar, text="", anchor=tk.W, padx=5)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Update status immediately
        self.update_status_bar()

    def update_status_bar(self):
        """Update the status bar with current language settings"""
        if hasattr(self, 'status_label'):
            target_lang = self.target_lang_var.get()
            definition_lang = self.definition_lang_var.get()
            source_lang = self.source_lang_var.get()
            
            status_text = f"Learning: {target_lang} | Definitions: {definition_lang} | Native: {source_lang}"
            self.status_label.config(text=status_text)
    
    def create_frames(self):
        # Main container frame to manage layout
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Top panel for toolbar
        self.top_panel = tk.Frame(self.main_container)
        self.top_panel.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Middle frame to contain the left and right panels
        self.middle_frame = tk.Frame(self.main_container)
        self.middle_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel for search and headword list
        self.left_panel = tk.Frame(self.middle_frame, width=200, bg="#f0f0f0")
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Right panel for displaying entries
        self.right_panel = tk.Frame(self.middle_frame)
        self.right_panel.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        # Bottom panel for search bar
        self.bottom_panel = tk.Frame(self.main_container)
        self.bottom_panel.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=10)
    
    def create_search_panel(self):
        # Search box
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.left_panel, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X, padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self.filter_headwords)
        
        # Headword list
        self.headword_list = tk.Listbox(self.left_panel)
        self.headword_list.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        self.headword_list.bind("<<ListboxSelect>>", self.show_entry)
        
        # Language filter controls
        self.language_filter_frame = tk.Frame(self.left_panel)
        self.language_filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Target language dropdown (learning language)
        tk.Label(self.language_filter_frame, text="Learning Language:").pack(anchor=tk.W)
        self.target_lang_var = tk.StringVar()
        self.target_lang_dropdown = ttk.Combobox(
            self.language_filter_frame, 
            textvariable=self.target_lang_var,
            state="readonly"
        )
        self.target_lang_dropdown.pack(fill=tk.X, pady=(0, 5))
        self.target_lang_dropdown.bind("<<ComboboxSelected>>", self.on_language_change)
        
        # Source language (native language) - display only, not editable
        tk.Label(self.language_filter_frame, text="Native Language:").pack(anchor=tk.W)
        self.source_lang_var = tk.StringVar(value="English")
        self.source_lang_display = ttk.Label(self.language_filter_frame, text="English")
        self.source_lang_display.pack(fill=tk.X, pady=(0, 5))
        
        # Definition language dropdown
        tk.Label(self.language_filter_frame, text="Definition Language:").pack(anchor=tk.W)
        self.definition_lang_var = tk.StringVar()
        self.definition_lang_dropdown = ttk.Combobox(
            self.language_filter_frame, 
            textvariable=self.definition_lang_var,
            state="readonly"
        )
        self.definition_lang_dropdown.pack(fill=tk.X)
        self.definition_lang_dropdown.bind("<<ComboboxSelected>>", self.on_language_change)
        
        # Initialize language dropdowns
        self.update_language_options()
    
    def create_entry_display(self):
        # Container frame for the entry display and action buttons
        self.entry_container = tk.Frame(self.right_panel)
        self.entry_container.pack(expand=True, fill=tk.BOTH)
        
        # Entry display
        self.entry_display = scrolledtext.ScrolledText(
            self.entry_container, wrap=tk.WORD, font=("Arial", 12), padx=10, pady=10
        )
        self.entry_display.pack(expand=True, fill=tk.BOTH)
        self.entry_display.config(state=tk.DISABLED)
        
        # Action buttons frame (at the bottom right)
        self.action_buttons_frame = tk.Frame(self.entry_container, bg="#f0f0f0")
        self.action_buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # Delete button (trash can)
        self.delete_button = ttk.Button(
            self.action_buttons_frame, 
            text="🗑️", 
            width=3,
            command=self.delete_current_entry
        )
        self.delete_button.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Regenerate button (refresh icon)
        self.regenerate_button = ttk.Button(
            self.action_buttons_frame, 
            text="🔄", 
            width=3,
            command=self.regenerate_current_entry
        )
        self.regenerate_button.pack(side=tk.RIGHT, padx=5)
        
        # Configure tags for formatting
        self.entry_display.tag_config("language_header", font=("Arial", 10), foreground="gray")
        self.entry_display.tag_config("headword", font=("Arial", 16, "bold"))
        self.entry_display.tag_config("pos", font=("Arial", 12, "italic"))
        self.entry_display.tag_config("definition", font=("Arial", 12, "bold"))
        self.entry_display.tag_config("grammar", font=("Arial", 10), foreground="gray")
        self.entry_display.tag_config("example_label", font=("Arial", 10, "italic"))
        self.entry_display.tag_config("example", font=("Arial", 12))
        self.entry_display.tag_config("translation", font=("Arial", 10, "italic"), foreground="blue")
        self.entry_display.tag_config("status", font=("Arial", 12), foreground="green")
        self.entry_display.tag_config("multiword_headword", font=("Arial", 16, "bold"), foreground="navy")
    
    def create_search_bar(self):
        # Bottom search bar for new entries
        # Add a visible border to make the search bar stand out
        search_frame = tk.Frame(self.bottom_panel, bd=2, relief=tk.GROOVE)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Title for the search area to make it more visible
        search_title = tk.Label(search_frame, text="Add New Word to Dictionary", font=("Arial", 12, "bold"))
        search_title.pack(pady=(5, 10))
        
        # Input area with clear label
        input_frame = tk.Frame(search_frame)
        input_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(input_frame, text="Enter word:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.new_word_var = tk.StringVar()
        self.new_word_entry = ttk.Entry(input_frame, textvariable=self.new_word_var, width=30, font=("Arial", 12))
        self.new_word_entry.pack(side=tk.LEFT, padx=5, ipady=3)  # Add some padding to make the entry larger
        
        self.search_btn = ttk.Button(input_frame, text="Search", command=self.search_new_word)
        self.search_btn.pack(side=tk.LEFT, padx=5)
        
        # Add clipboard monitoring checkbox
        self.clipboard_monitor_var = tk.BooleanVar(value=False)
        self.clipboard_monitor_cb = ttk.Checkbutton(
            input_frame,
            text="Enable clipboard monitoring",
            variable=self.clipboard_monitor_var,
            command=self.toggle_clipboard_monitoring
        )
        self.clipboard_monitor_cb.pack(side=tk.LEFT, padx=10)
        
        # Add a hint about current language settings
        hint_frame = tk.Frame(search_frame)
        hint_frame.pack(fill=tk.X, padx=20, pady=(0, 5))
        
        self.hint_label = tk.Label(hint_frame, text="Using your selected language preferences", font=("Arial", 8), fg="gray")
        self.hint_label.pack(side=tk.LEFT)
        
        # Bind Enter key to search
        self.new_word_entry.bind("<Return>", lambda event: self.search_new_word())
    
    def apply_saved_settings(self):
        """Apply saved user settings for language preferences"""
        settings = self.user_settings.get_settings()
        
        # Set language dropdowns based on user preferences
        target_lang = settings.get('target_language', 'Czech')
        definition_lang = settings.get('definition_language', 'English')
        
        # Check if values exist in dropdowns and set them
        if target_lang in self.target_lang_dropdown['values']:
            self.target_lang_var.set(target_lang)
        else:
            self.target_lang_var.set("All")
            
        # Set definition language
        self.definition_lang_var.set(definition_lang)
        
        # Set clipboard monitoring state if it was saved
        if hasattr(self, 'clipboard_monitor_var'):
            clipboard_enabled = settings.get('clipboard_monitoring', False)
            print(f"Loading clipboard monitoring setting: {clipboard_enabled}")
            self.clipboard_monitor_var.set(clipboard_enabled)
            if clipboard_enabled:
                # Use after to ensure the UI is fully loaded before starting monitoring
                self.root.after(1000, self.start_clipboard_monitoring)
        
        # Update the hint label
        self.update_hint_label()
            
        # Apply language filters
        self.apply_language_filters()
        
        # Update headword list
        self.update_headword_list()
    
    def update_hint_label(self):
        """Update the hint label to show current language settings"""
        source_lang = self.source_lang_var.get()
        target_lang = self.target_lang_var.get()
        definition_lang = self.definition_lang_var.get()
        
        hint_text = f"Learning: {target_lang} | Definitions in: {definition_lang}"
        if hasattr(self, 'hint_label'):
            self.hint_label.config(text=hint_text)
    
    def on_language_change(self, event=None):
        """Save user language preferences and apply filters"""
        # Save settings
        target_lang = self.target_lang_var.get()
        definition_lang = self.definition_lang_var.get()
        
        # Update user settings
        self.user_settings.update_settings({
            'target_language': target_lang,
            'definition_language': definition_lang,
            'source_language': 'English'  # Keep source language as English for now
        })
        
        # Update the dictionary engine's settings
        engine_settings = self.user_settings.get_template_replacements()
        self.dictionary_engine.settings = engine_settings
        
        # Update status bar
        self.update_status_bar()
        
        # Update the hint label
        self.update_hint_label()
        
        # Apply filters
        self.apply_language_filters()
    
    def display_entry(self, entry):
        """Format and display a dictionary entry"""
        self.entry_display.config(state=tk.NORMAL)
        self.entry_display.delete(1.0, tk.END)
        
        # Display language information
        metadata = entry["metadata"]
        self.entry_display.insert(tk.END, 
            f"{metadata['source_language']} → {metadata['target_language']} (Definitions in {metadata['definition_language']})\n\n", 
            "language_header")
        
        # Highlight multi-word headwords with a special tag
        headword = entry['headword']
        if ' ' in headword or '-' in headword:
            self.entry_display.insert(tk.END, f"{headword}\n", "multiword_headword")
        else:
            self.entry_display.insert(tk.END, f"{headword}\n", "headword")
        
        # Handle both part_of_speech and part_of speech variations
        part_of_speech = entry.get("part_of_speech") or entry.get("part_of speech", "unknown")
        self.entry_display.insert(tk.END, f"({part_of_speech})\n\n", "pos")
        
        # Display each meaning
        for i, meaning in enumerate(entry["meanings"], 1):
            self.entry_display.insert(tk.END, f"{i}. {meaning['definition']}\n", "definition")
            
            # Display grammar info if available
            grammar_info = []
            for k, v in meaning["grammar"].items():
                if v:
                    grammar_info.append(f"{k}: {v}")
            
            if grammar_info:
                self.entry_display.insert(tk.END, "   " + ", ".join(grammar_info) + "\n", "grammar")
            
            # Display examples
            for example in meaning["examples"]:
                self.entry_display.insert(tk.END, f"\n   Example:\n", "example_label")
                self.entry_display.insert(tk.END, f"   {example['sentence']}\n", "example")
                if example.get("translation"):
                    self.entry_display.insert(tk.END, f"   {example['translation']}\n\n", "translation")
        
        self.entry_display.config(state=tk.DISABLED)
    
    def clear_entry_display(self):
        """Clear the entry display area"""
        self.entry_display.config(state=tk.NORMAL)
        self.entry_display.delete(1.0, tk.END)
        self.entry_display.config(state=tk.DISABLED)
    
    def show_status_message(self, message):
        """Show a status message in the entry display"""
        self.entry_display.config(state=tk.NORMAL)
        self.entry_display.delete(1.0, tk.END)
        self.entry_display.insert(tk.END, message, "status")
        self.entry_display.config(state=tk.DISABLED)
    
    def update_headword_list(self):
        """Update the listbox with current filtered headwords"""
        self.headword_list.delete(0, tk.END)
        for entry in sorted(self.filtered_data, key=lambda x: x["headword"]):
            self.headword_list.insert(tk.END, entry["headword"])
    
    def reload_data(self):
        """Reload data from the database and update the display"""
        try:
            self.update_language_options()
            self.apply_language_filters()
            self.update_headword_list()
            self.clear_entry_display()
            print("Data reloaded successfully")
        except Exception as e:
            print(f"Error reloading data: {e}")
    
    def update_language_options(self):
        """Update the available options in language dropdowns"""
        languages = self.db_manager.get_all_languages()
        
        # Get languages from database and custom languages from settings
        db_languages = set(languages["target_languages"]).union(set(languages["definition_languages"]))
        custom_languages = set(self.load_custom_languages())
        removed_languages = set(self.load_removed_languages())
        
        # Print debug info
        print(f"Languages in database: {db_languages}")
        print(f"Custom languages: {custom_languages}")
        print(f"Removed languages: {removed_languages}")
        
        # Combine all languages and remove the ones marked as removed
        all_languages = db_languages.union(custom_languages) - removed_languages
        
        # Sort languages (keeping "All" at the top for target language)
        target_languages = ["All"] + sorted(all_languages)
        definition_languages = sorted(all_languages)
        
        print(f"Final languages shown: {all_languages}")
        
        self.target_lang_dropdown["values"] = target_languages
        self.definition_lang_dropdown["values"] = definition_languages
    
    def apply_language_filters(self, event=None):
        """Apply language filters based on dropdown selections"""
        target_lang = self.target_lang_var.get()
        definition_lang = self.definition_lang_var.get()
        
        # Filter by both target language and definition language
        self.filtered_data = self.db_manager.search_entries(
            target_lang=target_lang if target_lang != "All" else None,
            definition_lang=definition_lang if definition_lang else None
        )
        
        self.update_headword_list()
    
    def filter_headwords(self, event=None):
        """Filter headwords based on search input"""
        search_term = self.search_var.get().lower().strip()
        target_lang = self.target_lang_var.get()
        definition_lang = self.definition_lang_var.get()
        
        # If search term contains multiple words, search for exact matches or beginning-of-word matches
        if ' ' in search_term or '-' in search_term:
            self.filtered_data = self.db_manager.search_entries(
                search_term=search_term,
                target_lang=target_lang if target_lang != "All" else None,
                definition_lang=definition_lang if definition_lang else None
            )
        else:
            # For single words, use fuzzy matching
            self.filtered_data = self.db_manager.search_entries(
                search_term=search_term,
                target_lang=target_lang if target_lang != "All" else None,
                definition_lang=definition_lang if definition_lang else None
            )
        
        self.update_headword_list()
    
    def show_entry(self, event):
        """Display the selected dictionary entry"""
        selection = self.headword_list.curselection()
        if not selection:
            return
        
        selected_word = self.headword_list.get(selection[0])
        
        # Find the exact entry that matches current filter settings
        target_lang = self.target_lang_var.get()
        definition_lang = self.definition_lang_var.get()
        source_lang = self.source_lang_var.get()
        
        # Get the entry directly from the database to ensure we have the most up-to-date version
        entry = self.db_manager.get_entry_by_headword(
            selected_word,
            source_lang=source_lang,
            target_lang=None if target_lang == "All" else target_lang,
            definition_lang=definition_lang
        )
        
        if entry:
            # Store a reference to the current entry for delete/regenerate operations
            self.current_entry = entry
            # Display the entry
            self.display_entry(entry)
        else:
            # If not found in database, fall back to filtered data
            for e in self.filtered_data:
                if e["headword"] == selected_word:
                    if (target_lang == "All" or e["metadata"]["target_language"] == target_lang) and \
                       (e["metadata"]["definition_language"] == definition_lang):
                        entry = e
                        self.current_entry = entry
                        self.display_entry(entry)
                        break
    
    def search_new_word(self):
        """Handle searching for a new word"""
        word = self.new_word_var.get().strip()
        if not word:
            return
        
        # Clear the search field
        self.new_word_entry.delete(0, tk.END)
        
        # Show status
        self.show_status_message(f"Processing: '{word}'...")
        self.root.update()
        
        # Get current language settings
        target_lang = self.target_lang_var.get() if self.target_lang_var.get() != "All" else None
        source_lang = self.source_lang_var.get()
        definition_lang = self.definition_lang_var.get()
        
        # Step 1: Get lemma (now preserves multi-word expressions)
        lemma = self.dictionary_engine.get_lemma(word)
        
        # Step 2: Check if word exists
        existing_entry = self.db_manager.get_entry_by_headword(
            word, 
            source_lang=source_lang,
            target_lang=target_lang,
            definition_lang=definition_lang
        )
        
        if existing_entry:
            self.display_entry(existing_entry)
            self.select_and_show_headword(word.lower())
            return
        
        # Step 3: Check if lemma exists
        existing_entry = self.db_manager.get_entry_by_headword(
            lemma, 
            source_lang=source_lang,
            target_lang=target_lang,
            definition_lang=definition_lang
        )
        
        if existing_entry:
            self.display_entry(existing_entry)
            self.select_and_show_headword(lemma.lower())
        else:
            # Create new entry
            new_entry = self.dictionary_engine.create_new_entry(lemma, target_lang, source_lang)
            
            if new_entry:
                entry_id = self.db_manager.add_entry(new_entry)
                if entry_id:
                    self.reload_data()
                    self.display_entry(new_entry)
                    self.select_and_show_headword(lemma.lower())
                else:
                    self.show_status_message(f"Error: Failed to save entry for '{lemma}'")
            else:
                self.show_status_message(f"Error: Failed to create entry for '{lemma}'")

    def select_and_show_headword(self, headword: str):
        """Helper method to find and select a headword in the listbox"""
        for i in range(self.headword_list.size()):
            if self.headword_list.get(i).lower() == headword:
                self.headword_list.selection_clear(0, tk.END)
                self.headword_list.selection_set(i)
                self.headword_list.see(i)
                break
    
    def migrate_json_data(self):
        """Migrate data from JSON file to database"""
        try:
            # Migrate the main output.json file
            self.db_manager.migrate_from_json("output.json")
            
            # Reload data to reflect the imported entries
            self.reload_data()
            
            self.show_status_message("JSON data migrated successfully!")
        except Exception as e:
            self.show_status_message(f"Error migrating JSON data: {str(e)}")

    def create_toolbar(self):
        # Add manage languages button with submenu
        self.manage_lang_menu = tk.Menu(self.root, tearoff=0)
        self.manage_lang_menu.add_command(label="Add or Restore Language", command=self.show_add_language_dialog)
        self.manage_lang_menu.add_command(label="Hide Language", command=self.show_remove_language_dialog)
        
        self.manage_lang_btn = ttk.Button(self.top_panel, text="Manage Languages", command=self.show_language_menu)
        self.manage_lang_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Add reload button to top right
        self.reload_btn = ttk.Button(self.top_panel, text="Reload Data", command=self.reload_data)
        self.reload_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # Add clear cache button for debugging
        self.clear_cache_btn = ttk.Button(self.top_panel, text="Clear Lemma Cache", command=self.clear_lemma_cache)
        self.clear_cache_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # Add migrate button for one-time migration from JSON
        self.migrate_btn = ttk.Button(self.top_panel, text="Migrate JSON", command=self.migrate_json_data)
        self.migrate_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # Add application title to top left
        self.title_label = ttk.Label(self.top_panel, text="AI-Powered Dictionary", font=("Arial", 14, "bold"))
        self.title_label.pack(side=tk.LEFT, padx=5, pady=5)

    def clear_lemma_cache(self):
        """Clear the lemma cache for debugging"""
        self.db_manager.clear_lemma_cache()
        self.show_status_message("Lemma cache cleared successfully!")
    
    def show_add_language_dialog(self):
        """Show dialog to add a new learning language"""
        # Create a new top-level window
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Language")
        dialog.geometry("450x300")
        dialog.transient(self.root)  # Set to be on top of the main window
        dialog.grab_set()  # Make it modal
        
        # Center the dialog on the main window
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create dialog content
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Add Language", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Create tabs for two ways to add a language
        tab_control = ttk.Notebook(frame)
        
        # Tab 1: Add new language
        tab1 = ttk.Frame(tab_control)
        tab_control.add(tab1, text="Add New Language")
        
        ttk.Label(tab1, text="Enter language name:").pack(pady=(10, 5))
        
        language_var = tk.StringVar()
        language_entry = ttk.Entry(tab1, textvariable=language_var, width=30)
        language_entry.pack(pady=(0, 15))
        language_entry.focus()
        
        # Tab 2: Restore removed language
        tab2 = ttk.Frame(tab_control)
        tab_control.add(tab2, text="Restore Removed Language")
        
        # Get removed languages
        removed_languages = self.load_removed_languages()
        
        if not removed_languages:
            ttk.Label(tab2, text="No removed languages to restore", foreground="gray").pack(pady=20)
            restore_combo = None
            restore_var = None
        else:
            ttk.Label(tab2, text="Select language to restore:").pack(pady=(10, 5))
            restore_var = tk.StringVar()
            restore_combo = ttk.Combobox(tab2, textvariable=restore_var, values=sorted(removed_languages), state="readonly", width=28)
            restore_combo.pack(pady=(0, 15))
        
        tab_control.pack(expand=1, fill="both")
        
        # Button frame
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def add_new_language():
            new_language = language_var.get().strip()
            if new_language:
                # Update the dropdown options
                languages = self.db_manager.get_all_languages()
                all_current_languages = set(languages["target_languages"]) | set(languages["definition_languages"]) | set(self.load_custom_languages())
                
                if new_language not in all_current_languages:
                    # Save the custom language to user settings
                    self.save_custom_language(new_language)
                    
                    # Update language options
                    self.update_language_options()
                    
                    # Show success message
                    self.show_status_message(f"Added language: {new_language}")
                else:
                    self.show_status_message(f"Language '{new_language}' already exists")
                
                dialog.destroy()
                
        def restore_language():
            if restore_var and restore_combo:
                language_to_restore = restore_var.get().strip()
                if language_to_restore:
                    # Remove from the removed_languages list
                    self.remove_from_removed_languages(language_to_restore)
                    
                    # Update language options
                    self.update_language_options()
                    
                    # Show success message
                    self.show_status_message(f"Restored language: {language_to_restore}")
                    
                    dialog.destroy()
        
        def handle_action():
            current_tab = tab_control.index(tab_control.select())
            if current_tab == 0:  # Add new language tab
                add_new_language()
            else:  # Restore language tab
                restore_language()
        
        def cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Apply", command=handle_action).pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.RIGHT)
        
        # Bind Enter key to add language when in the entry field
        language_entry.bind("<Return>", lambda e: add_new_language())
    
    def show_remove_language_dialog(self):
        """Show dialog to remove a language from the dropdown"""
        # Create a new top-level window
        dialog = tk.Toplevel(self.root)
        dialog.title("Remove Language")
        dialog.geometry("350x250")
        dialog.transient(self.root)  # Set to be on top of the main window
        dialog.grab_set()  # Make it modal
        
        # Center the dialog on the main window
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create dialog content
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Remove Language", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        ttk.Label(frame, text="Select language to remove:").pack(pady=(0, 5))
        
        # Get current languages
        languages = self.db_manager.get_all_languages()
        all_languages = set(languages["target_languages"]) | set(languages["definition_languages"]) | set(self.load_custom_languages())
        removed_languages = set(self.load_removed_languages())
        available_languages = all_languages - removed_languages
        
        if not available_languages:
            ttk.Label(frame, text="No languages to remove", foreground="red").pack(pady=(0, 10))
        else:
            language_var = tk.StringVar()
            language_combo = ttk.Combobox(frame, textvariable=language_var, values=sorted(available_languages), state="readonly", width=28)
            language_combo.pack(pady=(0, 15))
            language_combo.focus()
        
        # Button frame
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)
        
        def remove_language():
            if available_languages:
                language_to_remove = language_var.get().strip()
                if language_to_remove:
                    # Add to removed languages list
                    self.save_removed_language(language_to_remove)
                    
                    # Update language options
                    self.update_language_options()
                    
                    # Show success message
                    self.show_status_message(f"Removed language: {language_to_remove}")
                
                dialog.destroy()
        
        def cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Remove", command=remove_language).pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.RIGHT)
    
    def show_language_menu(self):
        """Show the language management menu"""
        # Get the button coordinates
        x = self.manage_lang_btn.winfo_rootx()
        y = self.manage_lang_btn.winfo_rooty() + self.manage_lang_btn.winfo_height()
        
        # Show the menu at the button location
        self.manage_lang_menu.tk_popup(x, y)
    
    def save_custom_language(self, language):
        """Save custom language to user settings"""
        # Get current custom languages
        custom_languages = self.user_settings.get_setting('custom_languages', [])
        
        if language not in custom_languages:
            custom_languages.append(language)
            self.user_settings.update_settings({'custom_languages': custom_languages})
    
    def load_custom_languages(self):
        """Load custom languages from user settings"""
        return self.user_settings.get_setting('custom_languages', [])
    
    def save_removed_language(self, language):
        """Save removed language to user settings"""
        # Get current removed languages
        removed_languages = self.user_settings.get_setting('removed_languages', [])
        
        if language not in removed_languages:
            removed_languages.append(language)
            self.user_settings.update_settings({'removed_languages': removed_languages})
            print(f"Added '{language}' to removed languages list.")
    
    def remove_from_removed_languages(self, language):
        """Remove a language from the removed languages list"""
        removed_languages = self.user_settings.get_setting('removed_languages', [])
        
        if language in removed_languages:
            removed_languages.remove(language)
            self.user_settings.update_settings({'removed_languages': removed_languages})
            print(f"Removed '{language}' from removed languages list.")
            return True
        else:
            print(f"Warning: '{language}' not found in removed languages list.")
            return False
    
    def load_removed_languages(self):
        """Load removed languages from user settings"""
        return self.user_settings.get_setting('removed_languages', [])
    
    def toggle_clipboard_monitoring(self):
        """Toggle clipboard monitoring on/off"""
        is_enabled = self.clipboard_monitor_var.get()
        
        print(f"Toggle clipboard monitoring: {is_enabled}")
        
        if is_enabled:
            # If we're about to enable monitoring, force a single clipboard check right away
            try:
                current_clip = pyperclip.paste()
                print(f"Current clipboard content: '{current_clip}'")
                if current_clip.strip():
                    # Update the field with current clipboard content immediately
                    self.update_entry_from_clipboard(current_clip)
            except Exception as e:
                print(f"Error accessing clipboard during toggle: {e}")
            
            self.start_clipboard_monitoring()
            print("Clipboard monitoring enabled")
            
            # Add message to entry field if it's empty
            if not self.new_word_var.get().strip():
                self.show_status_message("Clipboard monitoring enabled. Copy text to automatically fill the search box.")
        else:
            self.stop_clipboard_monitoring()
            print("Clipboard monitoring disabled")
            self.show_status_message("Clipboard monitoring disabled")
            
        # Save the setting
        self.user_settings.update_settings({'clipboard_monitoring': is_enabled})
    
    def start_clipboard_monitoring(self):
        """Start the clipboard monitoring process"""
        if not self.clipboard_monitoring:
            self.clipboard_monitoring = True
            # Get initial clipboard content
            try:
                self.last_clipboard_content = pyperclip.paste()
                print(f"Initial clipboard content: '{self.last_clipboard_content}'")
            except Exception as e:
                print(f"Error accessing clipboard: {e}")
                self.last_clipboard_content = ""
            
            # Add debug output to the status area
            self.show_status_message(f"Clipboard monitoring enabled. Checking every {self.clipboard_check_interval/1000} seconds.")
            self.root.update()
            
            # Start the periodic clipboard check
            self.check_clipboard()
            
    def stop_clipboard_monitoring(self):
        """Stop clipboard monitoring"""
        self.clipboard_monitoring = False
        
    def check_clipboard(self):
        """Check for changes in clipboard content"""
        if not self.clipboard_monitoring:
            return
            
        try:
            # Get current clipboard content
            clipboard_content = pyperclip.paste()
            
            # Debug print for every check
            print(f"Clipboard check - Current: '{clipboard_content}', Last: '{self.last_clipboard_content}'")
            
            # If content has changed and isn't empty
            if clipboard_content != self.last_clipboard_content and clipboard_content.strip():
                print(f"New clipboard content detected: '{clipboard_content}'")
                self.last_clipboard_content = clipboard_content
                
                # Update the entry box with new content
                self.update_entry_from_clipboard(clipboard_content)
                
                # Give visual feedback that clipboard content was detected
                self.new_word_entry.focus_set()
                self.new_word_entry.selection_range(0, 'end')
        except Exception as e:
            print(f"Error checking clipboard: {e}")
            # Try to continue anyway
            pass
        
        # ALWAYS schedule the next check, regardless of what happened above
        # This ensures continuous monitoring until explicitly disabled
        self.root.after(self.clipboard_check_interval, self.check_clipboard)
    
    def update_entry_from_clipboard(self, content):
        """Update the entry box with clipboard content"""
        # Clear the current content
        self.new_word_entry.delete(0, tk.END)
        
        # Insert new content (trimmed to first line if multiline)
        first_line = content.strip().split('\n')[0]
        self.new_word_var.set(first_line)
        
        # Visual feedback that content was updated
        self.new_word_entry.config(background="#f0fff0")  # Light green background
        
        # Reset background color after a short delay
        self.root.after(500, lambda: self.new_word_entry.config(background="white"))
        
    def delete_current_entry(self):
        """Delete the currently displayed entry"""
        if not self.current_entry:
            self.show_status_message("No entry selected to delete.")
            return
            
        headword = self.current_entry["headword"]
        metadata = self.current_entry["metadata"]
        
        # Print debug info
        print(f"Attempting to delete entry: '{headword}'")
        print(f"Source language: {metadata['source_language']}")
        print(f"Target language: {metadata['target_language']}")
        print(f"Definition language: {metadata['definition_language']}")
        
        # Ask for confirmation
        confirm = tk.messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete '{headword}'?\nThis action cannot be undone."
        )
        
        if not confirm:
            return
            
        # Delete the entry with explicit language parameters
        success = self.db_manager.delete_entry(
            headword,
            source_lang=metadata["source_language"],
            target_lang=metadata["target_language"],
            definition_lang=metadata["definition_language"]
        )
        
        if success:
            print(f"Successfully deleted entry '{headword}' from database")
            
            # Clear the current entry
            self.current_entry = None
            
            # Clear the display
            self.clear_entry_display()
            
            # Show status message
            self.show_status_message(f"Entry '{headword}' deleted successfully.")
            
            # Force redraw of the UI
            self.root.update_idletasks()
            
            # Reload data from the database
            self.reload_data()
            
            # Manually search to ensure entry is no longer in filtered data
            found = False
            for entry in self.filtered_data:
                if entry["headword"] == headword:
                    found = True
                    break
                    
            if found:
                print(f"WARNING: Entry '{headword}' still found in filtered data after deletion")
            else:
                print(f"Confirmed: Entry '{headword}' no longer in filtered data")
        else:
            self.show_status_message(f"Failed to delete entry '{headword}'.")
    
    def regenerate_current_entry(self):
        """Regenerate the currently displayed entry"""
        if not self.current_entry:
            self.show_status_message("No entry selected to regenerate.")
            return
            
        headword = self.current_entry["headword"]
        metadata = self.current_entry["metadata"]
        
        # Print debug info
        print(f"Attempting to regenerate entry: '{headword}'")
        print(f"Source language: {metadata['source_language']}")
        print(f"Target language: {metadata['target_language']}")
        print(f"Definition language: {metadata['definition_language']}")
        
        # Ask for confirmation
        confirm = tk.messagebox.askyesno(
            "Confirm Regenerate",
            f"Are you sure you want to regenerate '{headword}'?\nThis will replace the current entry with a new one."
        )
        
        if not confirm:
            return
            
        # Show status
        self.show_status_message(f"Regenerating: '{headword}'...")
        self.root.update()
        
        # Force the UI to update before we start the regeneration process
        self.root.after(100)
        
        # Add random seed to ensure variation
        import time
        import random
        random.seed(time.time())
        variation_seed = random.randint(1, 10000)
        
        # Regenerate the entry with added variation instructions and random seed
        new_entry = self.dictionary_engine.regenerate_entry(
            headword,
            target_lang=metadata["target_language"],
            source_lang=metadata["source_language"],
            definition_lang=metadata["definition_language"],
            variation_seed=variation_seed
        )
        
        if new_entry:
            print(f"Successfully regenerated entry '{headword}'")
            
            # Update the current entry
            self.current_entry = new_entry
            
            # Display the new entry
            self.display_entry(new_entry)
            
            # Force redraw of the UI
            self.root.update_idletasks()
            
            # Reload data from the database
            self.reload_data()
            
            # Update the headword list and select the entry
            self.update_headword_list()
            self.select_and_show_headword(headword.lower())
            
            # Show success message
            self.show_status_message(f"Entry '{headword}' regenerated successfully.")
        else:
            self.show_status_message(f"Failed to regenerate entry '{headword}'.")

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = DictionaryApp(root)
    root.mainloop()