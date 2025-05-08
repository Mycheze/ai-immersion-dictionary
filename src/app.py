import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import os
import sys
import time
import threading
import uuid
from dictionary_engine import DictionaryEngine
from user_settings import UserSettings
from database_manager import DatabaseManager
from anki_integration import AnkiConnector, AnkiFieldMapper, AnkiExporter
from anki_config_ui import AnkiConfigDialog
from settings_dialog import SettingsDialog
from request_manager import RequestManager
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
        self.root.geometry("1200x1000")
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
        
        # Load user settings first
        self.user_settings = UserSettings()
        
        # Initialize dictionary engine with user settings
        self.dictionary_engine = DictionaryEngine(db_manager=self.db_manager, user_settings=self.user_settings)
        
        # Initialize the request manager for async API calls
        self.request_manager = RequestManager(self.dictionary_engine)
        self.request_manager.set_ui_callback(self.update_queue_status)
        
        # Queue status update interval (ms)
        self.queue_update_interval = 250
        
        # Dictionary to map request IDs to operations
        self.pending_requests = {}
        
        # Load existing dictionary data from database
        self.filtered_data = []
        
        # Store the current entry for delete/regenerate operations
        self.current_entry = None
        
        # Track what the user is currently viewing
        self.viewed_headword = None
        self.user_selected_entry = False  # Flag to track if user has actively selected an entry
        self.pending_notifications = []
        
        # Clipboard monitoring state
        self.clipboard_monitoring = False
        self.last_clipboard_content = ""
        self.clipboard_check_interval = 500  # milliseconds
        
        # Initialize Anki connector
        self.anki_connector = None
        try:
            settings = self.user_settings.get_settings()
            if settings.get('anki_enabled', False):
                self.anki_connector = AnkiConnector(settings.get('anki_url', 'http://localhost:8765'))
        except Exception as e:
            print(f"Failed to initialize Anki connector: {e}")
        
        # Setup the GUI layout
        self.setup_gui()
        
        # Apply saved user settings
        self.apply_saved_settings()
        
        # Update language options to include custom languages
        self.update_language_options()
        
        # Apply text scaling if saved in settings
        settings = self.user_settings.get_settings()
        text_scale = settings.get('text_scale_factor', 1.0)
        self.apply_text_scaling(text_scale)
        
        # Load initial data
        self.reload_data()
        
        # Update recent lookups list
        self.update_recent_lookups_list()
        
        # Start periodic UI updates for queue status
        self.root.after(self.queue_update_interval, self.periodic_ui_update)
    
    def setup_gui(self):
        # Create the main frame structure
        self.create_frames()
        
        # Create the menu and toolbar
        self.create_toolbar()
        
        # Create the notification area
        self.create_notification_area()
        
        # Create the search and entry panels
        self.create_search_panel()
        self.create_entry_display()
        
        # Create the sentence context panel
        self.create_sentence_context_panel()
        
        # Create the bottom search bar for new entries
        self.create_search_bar()
        
        # Create status bar
        # self.create_status_bar()
        
        # Make sure the bottom panel is visible
        self.bottom_panel.update()
        
        # Add space bar keyboard shortcut for search box focus
        # Bind it to all relevant widgets that might have focus
        def focus_search_box(event):
            # Skip if the event is already in a text input widget
            if isinstance(event.widget, tk.Entry) or isinstance(event.widget, tk.Text):
                return
            
            # Clear and focus on the search box
            self.new_word_entry.delete(0, tk.END)
            self.new_word_entry.focus_set()
            return "break"  # Prevent the space from being inserted
            
        
        # Bind to the main window and all major frames
        self.root.bind("<space>", focus_search_box)
        self.main_container.bind("<space>", focus_search_box)
        self.top_panel.bind("<space>", focus_search_box)
        self.notification_panel.bind("<space>", focus_search_box)
        self.middle_frame.bind("<space>", focus_search_box)
        self.left_panel.bind("<space>", focus_search_box)
        self.right_panel.bind("<space>", focus_search_box)
        self.bottom_panel.bind("<space>", focus_search_box)
        self.entry_display.bind("<space>", focus_search_box)
        self.headword_list.bind("<space>", focus_search_box)

#    def create_status_bar(self):
#        """Create a status bar to show current language settings"""
#        self.status_bar = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
#        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
#        
#        self.status_label = tk.Label(self.status_bar, text="", anchor=tk.W, padx=5)
#        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
#        
#        # Update status immediately
#        self.update_status_bar()
#
#    def update_status_bar(self):
#        """Update the status bar with current language settings"""
#        if hasattr(self, 'status_label'):
#            target_lang = self.target_lang_var.get()
#            definition_lang = self.definition_lang_var.get()
#            source_lang = self.source_lang_var.get()
#            
#            status_text = f"Learning: {target_lang} | Definitions: {definition_lang}"
#            self.status_label.config(text=status_text)

    def create_notification_area(self):
        """Create a dedicated area for displaying notifications"""
        # Create a frame for notification content
        self.notification_content_frame = tk.Frame(self.notification_panel, bg="#f0f0f0")
        self.notification_content_frame.pack(fill=tk.X, expand=True, padx=10, pady=5)
        
        # Create the notification label
        self.notification_label = tk.Label(
            self.notification_content_frame,
            text="",
            font=("Arial", 10, "bold"),
            bg="#f0f0f0",
            fg="#008800",  # Green color for notifications
            anchor=tk.W
        )
        self.notification_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Create a "View" button for completed entries
        self.view_notification_btn = ttk.Button(
            self.notification_content_frame,
            text="View",
            command=self.show_notification_entry,
            width=5
        )
        self.view_notification_btn.pack(side=tk.LEFT, padx=5)
        
        # Create a "Close" button to dismiss notifications
        self.close_notification_btn = ttk.Button(
            self.notification_content_frame,
            text="✕",
            command=self.clear_notifications,
            width=2
        )
        self.close_notification_btn.pack(side=tk.LEFT, padx=5)
    
    def create_frames(self):
        # Main container frame to manage layout
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Top panel for toolbar
        self.top_panel = tk.Frame(self.main_container)
        self.top_panel.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Notification panel for displaying system notifications
        self.notification_panel = tk.Frame(self.main_container, bg="#f0f0f0", bd=1, relief=tk.GROOVE)
        self.notification_panel.pack(side=tk.TOP, fill=tk.X, padx=5, pady=0)
        # Initially hide the notification panel until there's a notification to show
        self.notification_panel.pack_forget()
        
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
        
        # Sentence context panel (between entry display and bottom search bar)
        self.sentence_panel = tk.Frame(self.main_container)
        self.sentence_panel.pack(side=tk.BOTTOM, fill=tk.X, before=self.bottom_panel, padx=5, pady=5)
    
    def create_search_panel(self):
        # Search box
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.left_panel, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X, padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self.filter_headwords)
        # Add standard text editing shortcuts
        self.add_standard_text_bindings(self.search_entry)
        
        # Recent lookups section
        self.recent_lookups_frame = ttk.LabelFrame(self.left_panel, text="Recent Lookups")
        self.recent_lookups_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Recent lookups list
        self.recent_lookups_list = tk.Listbox(self.recent_lookups_frame, height=5)
        self.recent_lookups_list.pack(expand=False, fill=tk.X, padx=5, pady=5)
        self.recent_lookups_list.bind("<<ListboxSelect>>", self.show_recent_lookup)
        
        # Headword list (main dictionary list)
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
        
        # Source language (base language) - hidden but kept for internal use
        # Initialize with "English" for now - will be updated in apply_saved_settings
        self.source_lang_var = tk.StringVar(value="English")
        
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
        
        # Add standard text editing shortcuts for selection and copying
        self.add_standard_text_bindings(self.entry_display)
        
        # Make sure we can select text even in disabled state
        self.entry_display.bind("<1>", lambda event: self.entry_display.focus_set())
        
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
        self.entry_display.tag_config("context_header", font=("Arial", 10, "bold"), foreground="#008800")  # Green for context
        self.entry_display.tag_config("headword", font=("Arial", 16, "bold"))
        self.entry_display.tag_config("pos", font=("Arial", 12, "italic"))
        self.entry_display.tag_config("definition", font=("Arial", 12, "bold"))
        self.entry_display.tag_config("grammar", font=("Arial", 10), foreground="gray")
        self.entry_display.tag_config("example_label", font=("Arial", 10, "italic"))
        self.entry_display.tag_config("context_example_label", font=("Arial", 10, "italic"), foreground="#008800")  # Green for context examples
        self.entry_display.tag_config("example", font=("Arial", 12))
        self.entry_display.tag_config("context_example", font=("Arial", 12), background="#f0fff0")  # Light green background for context examples
        self.entry_display.tag_config("translation", font=("Arial", 10, "italic"), foreground="blue")
        self.entry_display.tag_config("status", font=("Arial", 12), foreground="green")
        self.entry_display.tag_config("multiword_headword", font=("Arial", 16, "bold"), foreground="navy")
    
    def create_search_bar(self):
        # Bottom search bar for new entries
        # Add a visible border to make the search bar stand out
        search_frame = tk.Frame(self.bottom_panel, bd=2, relief=tk.GROOVE)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Status bar for API queue
        self.queue_status_frame = tk.Frame(search_frame, bg="#f0f0f0")
        self.queue_status_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        # Queue status indicators
        self.queue_status_label = tk.Label(
            self.queue_status_frame, 
            text="API Queue: Idle", 
            font=("Arial", 9),
            bg="#f0f0f0",
            fg="#555555"
        )
        self.queue_status_label.pack(side=tk.LEFT, padx=5)
        
        # Progress/status indicators
        self.queue_active_label = tk.Label(
            self.queue_status_frame, 
            text="", 
            font=("Arial", 9),
            bg="#f0f0f0",
            fg="#555555"
        )
        self.queue_active_label.pack(side=tk.LEFT, padx=5)
        
        # Notification functionality has been moved to the dedicated notification area
        
        # Progress bar for active operations
        self.queue_progress = ttk.Progressbar(
            self.queue_status_frame,
            orient=tk.HORIZONTAL,
            length=200,
            mode='indeterminate'
        )
        self.queue_progress.pack(side=tk.LEFT, padx=5)
        
        # Cancel button for clearing the queue
        self.cancel_queue_btn = ttk.Button(
            self.queue_status_frame,
            text="Cancel All",
            command=self.cancel_all_requests,
            width=10
        )
        self.cancel_queue_btn.pack(side=tk.RIGHT, padx=5)
        
        # Initially hide the cancel button and progress bar
        self.queue_progress.pack_forget()
        self.cancel_queue_btn.pack_forget()
        
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
        
        # Add standard text editing shortcuts
        self.add_standard_text_bindings(self.new_word_entry)
    
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
        
        # Set source language equal to definition language
        self.source_lang_var.set(definition_lang)
        
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
        
        # Update source_lang_var to match definition_lang
        self.source_lang_var.set(definition_lang)
        
        # Update user settings
        self.user_settings.update_settings({
            'target_language': target_lang,
            'definition_language': definition_lang,
            'source_language': definition_lang  # Set source language equal to definition language
        })
        
        # Update the dictionary engine's settings
        engine_settings = self.user_settings.get_template_replacements()
        self.dictionary_engine.settings = engine_settings
        
        # Update status bar
        # self.update_status_bar()
        
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
        
        # Check if this is a context-based entry
        has_context = metadata.get("has_context", False)
        context_badge = " [Context-Aware]" if has_context else ""
        
        # Add a context badge to the header if entry is context-based
        self.entry_display.insert(tk.END, 
            f"{metadata['source_language']} → {metadata['target_language']} (Definitions in {metadata['definition_language']}){context_badge}\n\n", 
            "language_header" if not has_context else "context_header")
        
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
            
            # Display examples with export buttons
            for j, example in enumerate(meaning.get('examples', [])):
                # Check if this is a context sentence
                is_context = example.get("is_context_sentence", False)
                
                # Use different styling for context examples
                if is_context:
                    self.entry_display.insert(tk.END, f"\n   Context Example:\n", "context_example_label")
                else:
                    self.entry_display.insert(tk.END, f"\n   Example:\n", "example_label")
                
                # Create a frame for example and export button
                example_frame = tk.Frame(self.entry_display)
                self.entry_display.window_create(tk.END, window=example_frame)
                
                # Example text with different style for context examples - get scale factor from settings
                scale_factor = self.user_settings.get_setting('text_scale_factor', 1.0)
                
                # Use Text widget instead of Label to allow text selection
                example_text = tk.Text(example_frame, 
                                     font=("Arial", int(12 * scale_factor)),
                                     wrap=tk.WORD,
                                     height=1,  # Initial height, will be adjusted
                                     width=40,
                                     background="#f0fff0" if is_context else "white",  # Light green background for context
                                     relief=tk.FLAT,  # Remove the default border
                                     padx=5,
                                     pady=5)
                
                # Insert the example sentence
                example_text.insert(tk.END, f"   {example['sentence']}")
                
                # Calculate required height based on content
                # Get the number of lines in the widget
                line_count = int(example_text.index('end-1c').split('.')[0])
                # Set height based on content, with a minimum of 1 line
                example_text.config(height=max(1, min(line_count, 5)))
                
                # Make the text read-only but still selectable
                example_text.config(state=tk.DISABLED)
                
                # Allow the user to select text even in disabled state
                example_text.bind("<1>", lambda event: example_text.focus_set())
                
                # Add standard text editing shortcuts for selection and copying
                self.add_standard_text_bindings(example_text)
                
                example_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                # Export button (📤 icon)
                if self.anki_connector:
                    export_btn = ttk.Button(
                        example_frame, 
                        text="📤", 
                        width=3,
                        command=lambda m=i-1, e=j: self.export_example_to_anki(m, e)
                    )
                    export_btn.pack(side=tk.RIGHT, padx=5)
                
                self.entry_display.insert(tk.END, "\n")
                
                # Translation (if available)
                if example.get("translation"):
                    self.entry_display.insert(tk.END, f"   {example['translation']}\n\n", "translation")
        
        self.entry_display.config(state=tk.DISABLED)
    
    def clear_entry_display(self):
        """Clear the entry display area"""
        self.entry_display.config(state=tk.NORMAL)
        self.entry_display.delete(1.0, tk.END)
        self.entry_display.config(state=tk.DISABLED)
    
    def show_status_message(self, message):
        """Show a status message in a dedicated section, not overwriting the entry display"""
        # Create status bar if it doesn't exist
        if not hasattr(self, 'status_bar'):
            self.status_bar = tk.Frame(self.right_panel, height=25, bg="#f0f0f0")
            self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
            
            self.status_label = tk.Label(self.status_bar, text="", 
                                        font=("Arial", 10), fg="green", bg="#f0f0f0",
                                        anchor=tk.W)
            self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Update the status label
        self.status_label.config(text=message)
        
        # Schedule message clear after 10 seconds
        self.root.after(10000, lambda: self.status_label.config(text=""))
    
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
            self.update_recent_lookups_list()  # Update recent lookups UI
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
        
        # Reduce excessive logging - comment out debug prints
        # Debug info can be re-enabled for troubleshooting if needed
        # print(f"Languages in database: {db_languages}")
        # print(f"Custom languages: {custom_languages}")
        # print(f"Removed languages: {removed_languages}")
        
        # Combine all languages and remove the ones marked as removed
        all_languages = db_languages.union(custom_languages) - removed_languages
        
        # Get the raw custom language data for handling standardized names
        raw_custom_languages = self.user_settings.get_setting('custom_languages', [])
        standardized_to_display = {}
        
        # Build mapping of standardized names to display names
        for lang in raw_custom_languages:
            if isinstance(lang, dict):
                std_name = lang.get("standardized_name", "")
                display_name = lang.get("display_name", std_name)
                if std_name and display_name:
                    standardized_to_display[std_name] = display_name
        
        # During removals, we need to check for both display and standardized names
        filtered_languages = set()
        for lang in all_languages:
            # Check if this language (or its standardized/display name) is in removed_languages
            if lang in removed_languages:
                continue
            
            # Check if the standardized version of this name is removed
            std_name = self.get_standardized_language_name(lang)
            if std_name in removed_languages:
                continue
                
            filtered_languages.add(lang)
        
        # Sort languages (keeping "All" at the top for target language)
        target_languages = ["All"] + sorted(filtered_languages)
        definition_languages = sorted(filtered_languages)
        
        # Reduce excessive logging
        # print(f"Final languages shown: {filtered_languages}")
        
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
        """Display the selected dictionary entry triggered by user selection"""
        selection = self.headword_list.curselection()
        if not selection:
            return
        
        # Get the selected word from the listbox
        selected_word = self.headword_list.get(selection[0])
        
        # Track what the user is currently viewing
        self.viewed_headword = selected_word.lower()
        # Set flag indicating user has actively selected an entry
        self.user_selected_entry = True
        
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
            # Removed add_to_recent_lookups call - we only want to add when searching new words
        else:
            # If not found in database, fall back to filtered data
            for e in self.filtered_data:
                if e["headword"] == selected_word:
                    if (target_lang == "All" or e["metadata"]["target_language"] == target_lang) and \
                       (e["metadata"]["definition_language"] == definition_lang):
                        entry = e
                        self.current_entry = entry
                        self.display_entry(entry)
                        # Removed add_to_recent_lookups call - we only want to add when searching new words
                        break
    
    def search_new_word(self):
        """Handle searching for a new word asynchronously"""
        word = self.new_word_var.get().strip()
        if not word:
            return
        
        # DEBUG PRINTS - will help diagnose issues    
        print(f"SEARCH: Starting search for word: '{word}'")
        
        # Clear the search field but don't disable it - users can still enter words
        self.new_word_entry.delete(0, tk.END)
        
        # Check if we have active sentence context
        sentence_context = None
        if hasattr(self, 'context_active') and self.context_active and self.current_sentence_context:
            sentence_context = self.current_sentence_context
            context_status = "with context"
            # Update indicator to show active context
            self.set_context_indicator_color("blue")
            print(f"SEARCH: Using sentence context: '{sentence_context}'")
        else:
            context_status = ""
        
        # Show status with context indication
        status_msg = f"Queued: '{word}'{' ' + context_status if context_status else ''}..."
        self.show_status_message(status_msg)
        
        # Get current language settings
        target_lang = self.target_lang_var.get() if self.target_lang_var.get() != "All" else None
        source_lang = self.source_lang_var.get()
        definition_lang = self.definition_lang_var.get()
        
        print(f"SEARCH: Languages - Target: {target_lang}, Source: {source_lang}, Definition: {definition_lang}")
        
        # First, check if the word already exists - this is synchronous
        existing_entry = self.db_manager.get_entry_by_headword(
            word, 
            source_lang=source_lang,
            target_lang=target_lang,
            definition_lang=definition_lang
        )
        
        if existing_entry:
            print(f"SEARCH: Found existing entry for exact word '{word}'")
            # Use the direct display method for consistency
            self._direct_display_entry(existing_entry, word, sentence_context)
            print(f"SEARCH: Displayed existing entry for '{word}'")
            return
        
        # Create a copy of the word and context for use in callbacks
        word_copy = word
        context_copy = sentence_context
        
        # Step 2: Get lemma asynchronously (using context if available)
        params = {
            'word': word,
            'sentence_context': sentence_context
        }
        
        self.show_status_message(f"Getting lemma for '{word}'...")
        print(f"SEARCH: Getting lemma for '{word}'...")
        
        # Create a request for lemma
        request_id = self.request_manager.add_request(
            'lemma',
            params,
            success_callback=lambda lemma: self._on_lemma_received(
                lemma, word_copy, target_lang, source_lang, definition_lang, context_copy
            ),
            error_callback=lambda error: self._on_lemma_error(error, word_copy)
        )
        
        # Store the request ID for potential cancellation
        request_key = f"lemma_{word}"
        self.pending_requests[request_key] = request_id
        print(f"SEARCH: Added lemma request with ID {request_id}")
    
    def _on_lemma_received(self, lemma, original_word, target_lang, source_lang, definition_lang, sentence_context):
        """Handle received lemma from async request"""
        print(f"SEARCH: Received lemma: '{lemma}' for word '{original_word}'")
        
        # Check if lemma exists
        existing_entry = self.db_manager.get_entry_by_headword(
            lemma, 
            source_lang=source_lang,
            target_lang=target_lang,
            definition_lang=definition_lang
        )
        
        if existing_entry:
            print(f"SEARCH: Found existing entry for lemma '{lemma}'")
            # Process on main thread to ensure UI updates properly
            self.root.after(0, lambda: self._direct_display_entry(
                existing_entry, lemma, sentence_context
            ))
        else:
            # Create new entry with context if available
            print(f"SEARCH: Creating new entry for lemma '{lemma}'")
            self.show_status_message(f"Creating new entry for '{lemma}'...")
            
            params = {
                'word': lemma,
                'target_lang': target_lang,
                'source_lang': source_lang,
                'sentence_context': sentence_context
            }
            
            # Create a request for new entry
            request_id = self.request_manager.add_request(
                'entry',
                params,
                success_callback=lambda entry: self._on_entry_created(
                    entry, lemma, original_word, sentence_context
                ),
                error_callback=lambda error: self._on_entry_error(error, lemma, sentence_context)
            )
            
            # Store the request ID for potential cancellation
            request_key = f"entry_{lemma}"
            self.pending_requests[request_key] = request_id
            print(f"SEARCH: Added entry creation request with ID {request_id}")
            
    def _direct_display_entry(self, entry, lemma, sentence_context=None):
        """Direct display method that bypasses all the notification and select logic"""
        print(f"SEARCH: Directly displaying entry for '{lemma}'")
        
        # Make sure any existing notifications are cleared
        self.clear_notifications()
        
        # Update the current entry
        self.current_entry = entry
        
        # Show status in the dedicated status bar
        self.show_status_message(f"Found existing entry for '{lemma}'")
        
        # First make sure the entry is selected in the list - BEFORE displaying content
        try:
            # Force select it in the list
            self.select_and_show_headword(lemma.lower())
            print(f"SEARCH: Selected '{lemma}' in headword list")
        except Exception as e:
            print(f"SEARCH: Error selecting in list: {e}")
        
        # Clear and enable the display
        self.entry_display.config(state=tk.NORMAL)
        self.entry_display.delete(1.0, tk.END)
        
        # Display the entry directly - this should be the LAST operation
        self.display_entry(entry)
        
        # Make sure the display gets focus
        self.entry_display.focus_set()
        
        # Update and ensure the UI refreshes
        self.root.update_idletasks()
        
        # Add to recent lookups
        self.add_to_recent_lookups(entry)
        
        # Clear any sentence context
        if sentence_context:
            self.clear_sentence_context()
            
        print(f"SEARCH: Successfully displayed entry for '{lemma}'")
    
    def _process_existing_entry(self, entry, lemma, sentence_context):
        """Process existing entry on main thread"""
        # Update current_entry directly to ensure it's in sync
        self.current_entry = entry
        
        # Make sure any existing notifications are cleared
        self.clear_notifications()
        
        # Update queue status to show success
        self.queue_status_label.config(
            text=f"Found existing entry for '{lemma}'", 
            fg="#0066cc"  # Blue color for info
        )
        
        # Display the entry in the main area
        self.display_entry(entry)
        
        # Add to recent lookups
        self.add_to_recent_lookups(entry)
        
        # Select the word in the list after a short delay to ensure UI responsiveness
        self.root.after(100, lambda: self.select_and_show_headword(lemma.lower()))
        
        # Clear the sentence context window after finding the existing lemma
        if sentence_context:
            self.clear_sentence_context()
    
    def _on_entry_created(self, new_entry, lemma, original_word, sentence_context):
        """Handle created entry from async request"""
        print(f"SEARCH: Entry creation callback for '{lemma}'")
        if new_entry:
            # Process on main thread
            self.root.after(0, lambda: self._direct_display_new_entry(
                new_entry, lemma, original_word, sentence_context
            ))
        else:
            print(f"SEARCH: Failed to create entry for '{lemma}'")
            self.root.after(0, lambda: self._on_entry_error(
                "Failed to create entry", lemma, sentence_context
            ))
    
    def _direct_display_new_entry(self, new_entry, lemma, original_word, sentence_context):
        """Direct display method for new entries that bypasses all the notification logic"""
        print(f"SEARCH: Saving and displaying new entry for '{lemma}'")
        entry_id = self.db_manager.add_entry(new_entry)
        
        if entry_id:
            print(f"SEARCH: Successfully saved entry with ID {entry_id}")
            
            # If we had sentence context, save it in the database
            if sentence_context:
                self.db_manager.save_sentence_context(entry_id, sentence_context, original_word)
                # Clear the sentence context window after creating card successfully
                self.clear_sentence_context()
            
            # Make sure any existing notifications are cleared
            self.clear_notifications()
            
            # Update the current entry
            self.current_entry = new_entry
            
            # First show success message in the status bar (not in the entry display)
            self.show_status_message(f"Added new entry for '{lemma}'")
            
            # *** RELOAD DATA FIRST - This ensures the entry is in the list ***
            try:
                self.reload_data()
                print(f"SEARCH: Data reloaded for '{lemma}'")
            except Exception as e:
                print(f"SEARCH: Error reloading data: {e}")
            
            # Force select the entry in the list - BEFORE displaying
            try:
                self.select_and_show_headword(lemma.lower())
                print(f"SEARCH: Selected '{lemma}' in headword list")
            except Exception as e:
                print(f"SEARCH: Error selecting in list: {e}")
                
            # Now clear and enable the display after list is updated
            self.entry_display.config(state=tk.NORMAL)
            self.entry_display.delete(1.0, tk.END)
            
            # Display the entry directly - this should be the LAST operation
            self.display_entry(new_entry)
            print(f"SEARCH: Entry displayed for '{lemma}'")
            
            # Make sure the display gets focus
            self.entry_display.focus_set()
            
            # Update and ensure the UI refreshes
            self.root.update_idletasks()
            
            # Add to recent lookups
            self.add_to_recent_lookups(new_entry)
        else:
            print(f"SEARCH: Failed to save entry to database for '{lemma}'")
            self.show_status_message(f"Error: Failed to save entry for '{lemma}'")
            
            # Set context indicator back to red if context was active but failed
            if sentence_context:
                self.set_context_indicator_color("red")
    
    def _on_lemma_error(self, error, word, sentence_context=None):
        """Handle lemma error on main thread"""
        self.root.after(0, lambda: self.show_status_message(
            f"Error getting lemma for '{word}': {error}"
        ))
        
        # Set context indicator back to red if context was active but failed
        if sentence_context:
            self.set_context_indicator_color("red")
    
    def _on_entry_error(self, error, lemma, sentence_context=None):
        """Handle entry creation error on main thread"""
        self.root.after(0, lambda: self.show_status_message(
            f"Error creating entry for '{lemma}': {error}"
        ))
        
        # Set context indicator back to red if context was active but failed
        if sentence_context:
            self.set_context_indicator_color("red")

    def select_and_show_headword(self, headword: str):
        """Helper method to find and select a headword in the listbox without triggering display"""
        # Temporarily unbind the selection event to prevent auto-display
        self.headword_list.unbind("<<ListboxSelect>>")
        
        for i in range(self.headword_list.size()):
            if self.headword_list.get(i).lower() == headword:
                self.headword_list.selection_clear(0, tk.END)
                self.headword_list.selection_set(i)
                self.headword_list.see(i)
                break
                
        # Re-bind the selection event after making the selection
        self.headword_list.bind("<<ListboxSelect>>", self.show_entry)
    
    def show_recent_lookup(self, event):
        """Display the dictionary entry from the recent lookups list"""
        # Prevent interference with the main headword list
        self.headword_list.selection_clear(0, tk.END)
        
        selection = self.recent_lookups_list.curselection()
        if not selection:
            return
        
        # Get the selected index
        idx = selection[0]
        
        # Get the lookup data from user settings
        recent_lookups = self.user_settings.get_recent_lookups()
        if not recent_lookups or idx >= len(recent_lookups):
            return
            
        # Get the lookup entry
        lookup = recent_lookups[idx]
        headword = lookup.get('headword')
        target_lang = lookup.get('target_language')
        definition_lang = lookup.get('definition_language')
        source_lang = definition_lang  # Source language equals definition language
        
        # Track what the user is currently viewing
        self.viewed_headword = headword.lower()
        # Set flag indicating user has actively selected an entry
        self.user_selected_entry = True
        
        # Get the entry from the database
        entry = self.db_manager.get_entry_by_headword(
            headword,
            source_lang=source_lang,
            target_lang=target_lang,
            definition_lang=definition_lang
        )
        
        if entry:
            # Store the current entry reference
            self.current_entry = entry
            # Display the entry
            self.display_entry(entry)
            
            # Clear selection after displaying the entry
            self.recent_lookups_list.selection_clear(0, tk.END)
        else:
            self.show_status_message(f"Could not find entry for '{headword}'")
            
        # Keep focus on the recent lookup list for better UX
        self.recent_lookups_list.focus_set()
    
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
        
        # Add Anki configuration button
        self.anki_config_btn = ttk.Button(self.top_panel, text="⚙️ Anki Config", command=self.show_anki_config)
        self.anki_config_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Add Settings button
        self.settings_btn = ttk.Button(self.top_panel, text="⚙️ Settings", command=self.show_settings_dialog)
        self.settings_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Create admin buttons (only shown when ALT is pressed)
        self.admin_buttons_frame = tk.Frame(self.top_panel)
        self.admin_buttons_frame.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Add reload button to admin frame
        self.reload_btn = ttk.Button(self.admin_buttons_frame, text="Reload Data", command=self.reload_data)
        self.reload_btn.pack(side=tk.RIGHT, padx=5, pady=0)

        # Add clear cache button for debugging
        self.clear_cache_btn = ttk.Button(self.admin_buttons_frame, text="Clear Lemma Cache", command=self.clear_lemma_cache)
        self.clear_cache_btn.pack(side=tk.RIGHT, padx=5, pady=0)

        # Add migrate button for one-time migration from JSON
        self.migrate_btn = ttk.Button(self.admin_buttons_frame, text="Migrate JSON", command=self.migrate_json_data)
        self.migrate_btn.pack(side=tk.RIGHT, padx=5, pady=0)
        
        # Hide admin buttons by default
        self.admin_buttons_frame.pack_forget()

        # Add application title to top left
        self.title_label = ttk.Label(self.top_panel, text="AI-Powered Dictionary", font=("Arial", 14, "bold"))
        self.title_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Bind key events to show/hide admin buttons
        self.root.bind("<Alt-KeyPress>", self.show_admin_buttons)
        self.root.bind("<Alt-KeyRelease>", self.hide_admin_buttons)

    def clear_lemma_cache(self):
        """Clear the lemma cache for debugging"""
        self.db_manager.clear_lemma_cache()
        self.show_status_message("Lemma cache cleared successfully!")
    
    def show_add_language_dialog(self):
        """Show dialog to add a new learning language"""
        # Create a new top-level window
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Language")
        dialog.geometry("450x400")  # Taller dialog for confirmation step
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
        
        # Status message for feedback
        status_var = tk.StringVar()
        status_label = ttk.Label(tab1, textvariable=status_var, foreground="blue")
        status_label.pack(pady=(0, 5))
        
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
        
        # Confirmation frame (initially hidden)
        confirmation_frame = ttk.LabelFrame(frame, text="Confirm Language")
        
        ttk.Label(confirmation_frame, text="We detected this language as:").pack(pady=(5, 0))
        
        # Display detected language info
        standardized_var = tk.StringVar()
        standardized_label = ttk.Label(confirmation_frame, textvariable=standardized_var, font=("Arial", 10, "bold"))
        standardized_label.pack(pady=(0, 10))
        
        ttk.Label(confirmation_frame, text="Display name:").pack(anchor=tk.W)
        
        # Allow user to edit display name
        display_var = tk.StringVar()
        display_entry = ttk.Entry(confirmation_frame, textvariable=display_var, width=30)
        display_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Confirmation buttons
        confirm_btn_frame = ttk.Frame(confirmation_frame)
        confirm_btn_frame.pack(fill=tk.X)
        
        def confirm_language():
            # Save the validated language with both display and standardized names
            self.save_custom_language(display_var.get(), standardized_var.get())
            
            # Update language options
            self.update_language_options()
            
            # Show success message
            self.show_status_message(f"Added language: {display_var.get()}")
            
            # Close dialog
            dialog.destroy()
        
        def back_to_input():
            # Hide confirmation frame and show tabs again
            confirmation_frame.pack_forget()
            tab_control.pack(expand=1, fill="both")
            button_frame.pack(fill=tk.X, pady=(10, 0))
            
            # Clear the status message
            status_var.set("")
            
            # Focus back on the language entry
            language_entry.focus()
        
        ttk.Button(confirm_btn_frame, text="Confirm", command=confirm_language).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(confirm_btn_frame, text="Back", command=back_to_input).pack(side=tk.RIGHT)
        
        # Button frame for initial tabs
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def validate_and_add_language():
            new_language = language_var.get().strip()
            if not new_language:
                status_var.set("Please enter a language name")
                return
                
            status_var.set("Validating language...")
            dialog.update_idletasks()  # Force UI update
            
            # Check if language already exists
            languages = self.db_manager.get_all_languages()
            all_current_languages = set(languages["target_languages"]) | set(languages["definition_languages"]) | set(self.load_custom_languages())
            
            if new_language in all_current_languages:
                status_var.set(f"Language '{new_language}' already exists")
                return
            
            # Validate the language name using the dictionary engine
            validation_result = self.dictionary_engine.validate_language(new_language)
            
            # Show confirmation dialog
            standardized_var.set(validation_result["standardized_name"])
            display_var.set(validation_result["display_name"])
            
            # Hide tabs and show confirmation
            tab_control.pack_forget()
            button_frame.pack_forget()
            confirmation_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
            display_entry.focus()
        
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
                validate_and_add_language()
            else:  # Restore language tab
                restore_language()
        
        def cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Next", command=handle_action).pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.RIGHT)
        
        # Bind Enter key to add language when in the entry field
        language_entry.bind("<Return>", lambda e: validate_and_add_language())
    
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
    
    def save_custom_language(self, display_name, standardized_name=None):
        """
        Save custom language to user settings
        
        Args:
            display_name: The display name of the language (user's original input)
            standardized_name: The standardized English name of the language
        """
        # If standardized_name is not provided, use display_name
        if standardized_name is None:
            standardized_name = display_name
            
        # Get current custom languages
        custom_languages = self.user_settings.get_setting('custom_languages', [])
        
        # Structure for storing language data
        language_entry = {
            "display_name": display_name,
            "standardized_name": standardized_name
        }
        
        # Check if language already exists (by standardized name)
        for i, lang in enumerate(custom_languages):
            if isinstance(lang, dict) and lang.get("standardized_name") == standardized_name:
                # Update existing entry
                custom_languages[i] = language_entry
                self.user_settings.update_settings({'custom_languages': custom_languages})
                return
            elif not isinstance(lang, dict) and lang == standardized_name:
                # Replace string entry with dict entry
                custom_languages[i] = language_entry
                self.user_settings.update_settings({'custom_languages': custom_languages})
                return
        
        # If we get here, language doesn't exist, so add it
        custom_languages.append(language_entry)
        self.user_settings.update_settings({'custom_languages': custom_languages})
    
    def load_custom_languages(self):
        """Load custom languages from user settings"""
        languages = self.user_settings.get_setting('custom_languages', [])
        
        # Ensure we return a list of strings for compatibility
        result = []
        for lang in languages:
            if isinstance(lang, dict):
                # Add the display name for UI
                result.append(lang.get("display_name", ""))
            else:
                # For backward compatibility with old string-based format
                result.append(lang)
                
        return result
        
    def get_standardized_language_name(self, display_name):
        """Get standardized name for a language display name"""
        languages = self.user_settings.get_setting('custom_languages', [])
        
        # Search for the language in the custom_languages list
        for lang in languages:
            if isinstance(lang, dict):
                if lang.get("display_name") == display_name:
                    return lang.get("standardized_name", display_name)
        
        # If not found, return the display name
        return display_name
    
    def save_removed_language(self, language):
        """Save removed language to user settings"""
        # Get current removed languages
        removed_languages = self.user_settings.get_setting('removed_languages', [])
        
        # Get standardized name for this language (if it exists)
        standardized_name = self.get_standardized_language_name(language)
        
        # Store both display name and standardized name to ensure proper removal
        if language not in removed_languages:
            removed_languages.append(language)
            self.user_settings.update_settings({'removed_languages': removed_languages})
            print(f"Added '{language}' to removed languages list.")
        
        # Also add standardized version if different and not already in list
        if standardized_name != language and standardized_name not in removed_languages:
            removed_languages.append(standardized_name)
            self.user_settings.update_settings({'removed_languages': removed_languages})
            print(f"Added standardized name '{standardized_name}' to removed languages list.")
    
    def remove_from_removed_languages(self, language):
        """Remove a language from the removed languages list"""
        removed_languages = self.user_settings.get_setting('removed_languages', [])
        
        # Get standardized name for this language (if it exists)
        standardized_name = self.get_standardized_language_name(language)
        
        removed = False
        
        # Remove display name if present
        if language in removed_languages:
            removed_languages.remove(language)
            removed = True
            print(f"Removed '{language}' from removed languages list.")
        
        # Also remove standardized version if present
        if standardized_name != language and standardized_name in removed_languages:
            removed_languages.remove(standardized_name)
            removed = True
            print(f"Removed standardized name '{standardized_name}' from removed languages list.")
        
        # Update settings if anything was removed
        if removed:
            self.user_settings.update_settings({'removed_languages': removed_languages})
            return True
        else:
            print(f"Warning: '{language}' not found in removed languages list.")
            return False
    
    def load_removed_languages(self):
        """Load removed languages from user settings"""
        return self.user_settings.get_setting('removed_languages', [])
    
    def show_admin_buttons(self, event=None):
        """Show admin buttons when ALT key is pressed"""
        if hasattr(self, 'admin_buttons_frame'):
            self.admin_buttons_frame.pack(side=tk.RIGHT, padx=5, pady=5)
    
    def hide_admin_buttons(self, event=None):
        """Hide admin buttons when ALT key is released"""
        if hasattr(self, 'admin_buttons_frame'):
            self.admin_buttons_frame.pack_forget()
            
    def create_sentence_context_panel(self):
        """Create a panel for sentence context input"""
        # Create labeled frame with a border
        self.sentence_frame = ttk.LabelFrame(self.sentence_panel, text="Sentence Context")
        self.sentence_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top bar with label and character counter
        top_bar = tk.Frame(self.sentence_frame)
        top_bar.pack(fill=tk.X, padx=5, pady=(3, 0))
        
        self.char_count_var = tk.StringVar(value="0/150")
        ttk.Label(top_bar, text="Enter/paste a sentence (max 150 chars):").pack(side=tk.LEFT)
        ttk.Label(top_bar, textvariable=self.char_count_var).pack(side=tk.RIGHT)
        
        # Middle section with text entry and scrollbar
        text_frame = tk.Frame(self.sentence_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)
        
        # Create text widget for sentence input with scrollbar
        self.sentence_text = tk.Text(text_frame, height=2, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, command=self.sentence_text.yview)
        self.sentence_text.config(yscrollcommand=scrollbar.set)
        
        self.sentence_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bottom bar with buttons
        button_bar = tk.Frame(self.sentence_frame)
        button_bar.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Instruction label
        ttk.Label(button_bar, text="Double-click or select text to lookup:", font=("Arial", 8)).pack(side=tk.LEFT)
        
        # Clear button on the right
        self.clear_btn = ttk.Button(button_bar, text="Clear", width=8, command=self.clear_sentence_context)
        self.clear_btn.pack(side=tk.RIGHT, padx=5)
        
        # Context status indicator (dot)
        self.context_indicator = tk.Canvas(button_bar, width=16, height=16, bg="#f0f0f0", highlightthickness=0)
        self.context_indicator.pack(side=tk.RIGHT, padx=5)
        self.context_indicator.create_oval(4, 4, 12, 12, fill="gray", outline="")
        
        # Bind events
        self.sentence_text.bind("<KeyRelease>", self.update_char_count)
        self.sentence_text.bind("<Double-Button-1>", self.on_word_double_click)
        self.sentence_text.bind("<<Selection>>", self.on_text_selection)
        # Add standard text editing shortcuts
        self.add_standard_text_bindings(self.sentence_text)
        
        # Initialize instance variables
        self.current_sentence_context = None
        self.context_active = False
        
    def update_char_count(self, event=None):
        """Update the character count display and limit input"""
        text = self.sentence_text.get("1.0", "end-1c")
        count = len(text)
        
        # Update the count display
        self.char_count_var.set(f"{count}/150")
        
        # Limit to 150 characters
        if count > 150:
            # Delete the excess characters
            self.sentence_text.delete("1.0 + 150 chars", "end-1c")
            # Update the count again
            self.char_count_var.set("150/150")
            
        # Store current context
        self.current_sentence_context = self.sentence_text.get("1.0", "end-1c").strip()
        
    def clear_sentence_context(self):
        """Clear the sentence context field"""
        self.sentence_text.delete("1.0", tk.END)
        self.current_sentence_context = None
        self.context_active = False
        self.update_char_count()
        self.set_context_indicator_color("gray")
        
    def on_word_double_click(self, event):
        """Handle double-click in the sentence to select a word"""
        try:
            # Get position at click
            index = self.sentence_text.index(f"@{event.x},{event.y}")
            
            # Get the line and character offset
            line, char = map(int, index.split('.'))
            
            # Get the content of the current line
            line_content = self.sentence_text.get(f"{line}.0", f"{line}.end")
            
            # Find word boundaries
            left = right = char
            
            # Find the start of the word
            while left > 0 and line_content[left-1].isalnum() or line_content[left-1] in "-_'":
                left -= 1
                
            # Find the end of the word
            while right < len(line_content) and (line_content[right].isalnum() or line_content[right] in "-_'"):
                right += 1
                
            # Select the word
            self.sentence_text.tag_remove(tk.SEL, "1.0", tk.END)
            self.sentence_text.tag_add(tk.SEL, f"{line}.{left}", f"{line}.{right}")
            
            # Get the selected word
            selected_word = line_content[left:right]
            
            if selected_word:
                # Update the new word entry with the selected word
                self.new_word_var.set(selected_word)
                
                # Set context as active
                self.context_active = True
                self.set_context_indicator_color("green")
                
                # Focus on the search button
                self.search_btn.focus_set()
                
        except Exception as e:
            print(f"Error handling double-click: {e}")
            
    def on_text_selection(self, event=None):
        """Handle manual text selection in the sentence"""
        try:
            # Check if there is a selection
            if self.sentence_text.tag_ranges(tk.SEL):
                # Get the selected text
                selected_text = self.sentence_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                
                if selected_text and len(selected_text.strip()) > 0:
                    # Update the new word entry with the selected text
                    self.new_word_var.set(selected_text)
                    
                    # Set context as active
                    self.context_active = True
                    self.set_context_indicator_color("green")
                    
                    # Focus on the search button
                    self.search_btn.focus_set()
            
        except Exception as e:
            print(f"Error handling text selection: {e}")
            
    def set_context_indicator_color(self, color):
        """Update the context indicator color"""
        self.context_indicator.delete("all")
        self.context_indicator.create_oval(4, 4, 12, 12, fill=color, outline="")
    
    def toggle_clipboard_monitoring(self):
        """Toggle clipboard monitoring on/off"""
        is_enabled = self.clipboard_monitor_var.get()
        
        # Reduce debug logging
        # print(f"Toggle clipboard monitoring: {is_enabled}")
        
        if is_enabled:
            # If we're about to enable monitoring, force a single clipboard check right away
            try:
                current_clip = pyperclip.paste()
                # Reduce debug logging
                # print(f"Current clipboard content: '{current_clip}'")
                if current_clip.strip():
                    # Update the field with current clipboard content immediately
                    self.update_entry_from_clipboard(current_clip)
            except Exception as e:
                print(f"Error accessing clipboard during toggle: {e}")
            
            self.start_clipboard_monitoring()
            # Reduce console output, keep status message for user
            # print("Clipboard monitoring enabled")
            
            # Add message to entry field if it's empty
            if not self.new_word_var.get().strip():
                self.show_status_message("Clipboard monitoring enabled. Copy text to automatically fill the search box.")
        else:
            self.stop_clipboard_monitoring()
            # Reduce console output, keep status message for user
            # print("Clipboard monitoring disabled")
            self.show_status_message("Clipboard monitoring disabled")
            
        # Save the setting
        self.user_settings.update_settings({'clipboard_monitoring': is_enabled})
    
    def start_clipboard_monitoring(self):
        """Start the clipboard monitoring process"""
        # First ensure any existing monitoring is stopped to prevent multiple timers
        self.stop_clipboard_monitoring()
        
        # Then start new monitoring
        self.clipboard_monitoring = True
        
        # Get initial clipboard content
        try:
            self.last_clipboard_content = pyperclip.paste()
            # Reduce debug output
            # print(f"Initial clipboard content: '{self.last_clipboard_content}'")
        except Exception as e:
            print(f"Error accessing clipboard: {e}")
            self.last_clipboard_content = ""
        
        # Add info to the status area
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
            
            # Remove excessive debug printing
            # Only log when content actually changes
            
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
        if self.clipboard_monitoring:  # Double-check flag to prevent multiple timers
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
        
        # Reduce debug info
        # print(f"Attempting to delete entry: '{headword}'")
        # print(f"Source language: {metadata['source_language']}")
        # print(f"Target language: {metadata['target_language']}")
        # print(f"Definition language: {metadata['definition_language']}")
        
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
            # print(f"Successfully deleted entry '{headword}' from database")
            
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
            
            # Select the first item in the list if there are any entries
            if self.headword_list.size() > 0:
                self.headword_list.selection_clear(0, tk.END)
                self.headword_list.selection_set(0)
                self.headword_list.see(0)
                # Trigger selection event to update current_entry
                event = tk.Event()
                event.widget = self.headword_list
                self.show_entry(event)
        else:
            self.show_status_message(f"Failed to delete entry '{headword}'.")
    
    def regenerate_current_entry(self):
        """Regenerate the currently displayed entry asynchronously"""
        if not self.current_entry:
            self.show_status_message("No entry selected to regenerate.")
            return
            
        headword = self.current_entry["headword"]
        metadata = self.current_entry["metadata"]
        
        # Ask for confirmation
        confirm = tk.messagebox.askyesno(
            "Confirm Regenerate",
            f"Are you sure you want to regenerate '{headword}'?\nThis will replace the current entry with a new one."
        )
        
        if not confirm:
            return
            
        # Show status
        self.show_status_message(f"Queued: Regenerating '{headword}'...")
        
        # Add random seed to ensure variation
        import random
        random.seed(time.time())
        variation_seed = random.randint(1, 10000)
        
        # Prepare parameters for async request
        params = {
            'headword': headword,
            'target_lang': metadata["target_language"],
            'source_lang': metadata["source_language"],
            'definition_lang': metadata["definition_language"],
            'variation_seed': variation_seed
        }
        
        # Add regeneration request to queue
        request_id = self.request_manager.add_request(
            'regenerate',
            params,
            success_callback=lambda entry: self._on_regenerate_success(entry, headword),
            error_callback=lambda error: self._on_regenerate_error(error, headword)
        )
        
        # Store the request ID
        request_key = f"regenerate_{headword}"
        self.pending_requests[request_key] = request_id
    
    def _on_regenerate_success(self, new_entry, headword):
        """Handle successful entry regeneration"""
        if new_entry:
            # Process on main thread
            self.root.after(0, lambda: self._process_regenerated_entry(new_entry, headword))
        else:
            self.root.after(0, lambda: self.show_status_message(
                f"Failed to regenerate entry '{headword}'."
            ))
            
    def _process_regenerated_entry(self, new_entry, headword):
        """Process regenerated entry on main thread"""
        print(f"SEARCH: Processing regenerated entry for '{headword}'")
        
        # Update current entry
        self.current_entry = new_entry
        
        # Show status in the status bar
        self.show_status_message(f"Regenerated entry for '{headword}'")
        
        # Reload data FIRST to ensure the entry is in the list
        try:
            self.reload_data()
            print(f"SEARCH: Data reloaded for regenerated '{headword}'")
        except Exception as e:
            print(f"SEARCH: Error reloading data: {e}")
        
        # Force select the entry in the list BEFORE displaying content
        try:
            self.select_and_show_headword(headword.lower())
            print(f"SEARCH: Selected regenerated '{headword}' in headword list")
        except Exception as e:
            print(f"SEARCH: Error selecting in list: {e}")
        
        # Clear and enable the display
        self.entry_display.config(state=tk.NORMAL)
        self.entry_display.delete(1.0, tk.END)
        
        # Display the entry as the LAST operation
        self.display_entry(new_entry)
        print(f"SEARCH: Displayed regenerated entry for '{headword}'")
        
        # Make sure the display gets focus
        self.entry_display.focus_set()
        
        # Update and ensure the UI refreshes
        self.root.update_idletasks()
    
    def _on_regenerate_error(self, error, headword):
        """Handle entry regeneration error"""
        self.root.after(0, lambda: self.show_status_message(
            f"Error regenerating entry '{headword}': {error}"
        ))
    
    def show_anki_config(self):
        """Show Anki configuration dialog"""
        dialog = AnkiConfigDialog(self.root, self.user_settings)
        
        # Wait for dialog to be closed
        self.root.wait_window(dialog)
        
        # After dialog is closed, check if we need to re-initialize Anki connector
        settings = self.user_settings.get_settings()
        if settings.get('anki_enabled', False):
            try:
                self.anki_connector = AnkiConnector(settings.get('anki_url', 'http://localhost:8765'))
                # Test connection
                if self.anki_connector.test_connection():
                    self.show_status_message("Connected to Anki successfully!")
                else:
                    self.show_status_message("Failed to connect to Anki. Check if Anki is running.")
                    self.anki_connector = None
            except Exception as e:
                self.show_status_message(f"Error connecting to Anki: {str(e)}")
                self.anki_connector = None
        else:
            self.anki_connector = None
            
        # Redisplay current entry to update export buttons
        if self.current_entry:
            self.display_entry(self.current_entry)
            
    def show_settings_dialog(self):
        """Show application settings dialog"""
        dialog = SettingsDialog(self.root, self.user_settings)
        
        # Wait for dialog to be closed
        self.root.wait_window(dialog)
        
        # After dialog is closed, apply the text scaling
        settings = self.user_settings.get_settings()
        text_scale = settings.get('text_scale_factor', 1.0)
        
        # Apply text scaling to the UI
        self.apply_text_scaling(text_scale)
        
        # Show status message
        self.show_status_message(f"Text scaling set to {text_scale:.2f}x")
        
    def apply_text_scaling(self, scale_factor):
        """Apply text scaling to all UI elements"""
        # Update font sizes based on the scale factor
        self.update_tag_fonts(scale_factor)
        
        # Update entry display font
        base_entry_size = 12
        new_entry_size = int(base_entry_size * scale_factor)
        self.entry_display.config(font=("Arial", new_entry_size))
        
        # Update search elements
        self.new_word_entry.config(font=("Arial", int(12 * scale_factor)))
        self.hint_label.config(font=("Arial", int(8 * scale_factor)))
        
        # Update toolbar title
        self.title_label.config(font=("Arial", int(14 * scale_factor), "bold"))
        
        # Update headword list
        self.headword_list.config(font=("Arial", int(10 * scale_factor)))
        
        # Update recent lookups list
        self.recent_lookups_list.config(font=("Arial", int(10 * scale_factor)))
        
        # Update search entry
        self.search_entry.config(font=("Arial", int(10 * scale_factor)))
        
        # Update language filter labels and dropdowns
        for child in self.language_filter_frame.winfo_children():
            if isinstance(child, tk.Label):
                child.config(font=("Arial", int(10 * scale_factor)))
        
        # Update target and definition language dropdowns
        style = ttk.Style()
        style.configure("TCombobox", font=("Arial", int(10 * scale_factor)))
        
        # Update sentence context panel
        if hasattr(self, 'sentence_text'):
            self.sentence_text.config(font=("Arial", int(10 * scale_factor)))
            
            # Update char count and instructions label
            for child in self.sentence_frame.winfo_children():
                if isinstance(child, tk.Frame):
                    for subchild in child.winfo_children():
                        if isinstance(subchild, ttk.Label):
                            subchild.config(font=("Arial", int(8 * scale_factor)))
                            
        # Update search bar title and label
        for child in self.bottom_panel.winfo_children():
            if isinstance(child, tk.Frame):  # This should be the search_frame
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Label) and "Add New Word" in subchild["text"]:
                        subchild.config(font=("Arial", int(12 * scale_factor), "bold"))
                    elif isinstance(subchild, tk.Frame):  # input_frame or hint_frame
                        for sub_subchild in subchild.winfo_children():
                            if isinstance(sub_subchild, tk.Label) and "Enter word" in sub_subchild["text"]:
                                sub_subchild.config(font=("Arial", int(10 * scale_factor)))
        
        # Update example text in entries with the newly scaled fonts
        if self.current_entry:
            self.display_entry(self.current_entry)
        
    def update_tag_fonts(self, scale_factor):
        """Update all tag fonts with the new scale factor"""
        # Calculate new font sizes
        size_10 = int(10 * scale_factor)
        size_12 = int(12 * scale_factor)
        size_16 = int(16 * scale_factor)
        
        # Update tag configurations
        self.entry_display.tag_config("language_header", font=("Arial", size_10), foreground="gray")
        self.entry_display.tag_config("context_header", font=("Arial", size_10, "bold"), foreground="#008800")
        self.entry_display.tag_config("headword", font=("Arial", size_16, "bold"))
        self.entry_display.tag_config("pos", font=("Arial", size_12, "italic"))
        self.entry_display.tag_config("definition", font=("Arial", size_12, "bold"))
        self.entry_display.tag_config("grammar", font=("Arial", size_10), foreground="gray")
        self.entry_display.tag_config("example_label", font=("Arial", size_10, "italic"))
        self.entry_display.tag_config("context_example_label", font=("Arial", size_10, "italic"), foreground="#008800")
        self.entry_display.tag_config("example", font=("Arial", size_12))
        self.entry_display.tag_config("context_example", font=("Arial", size_12), background="#f0fff0")
        self.entry_display.tag_config("translation", font=("Arial", size_10, "italic"), foreground="blue")
        self.entry_display.tag_config("status", font=("Arial", size_12), foreground="green")
        self.entry_display.tag_config("multiword_headword", font=("Arial", size_16, "bold"), foreground="navy")
        
    def update_recent_lookups_list(self):
        """Update the recent lookups listbox with the most recent lookups"""
        # Clear the current content
        self.recent_lookups_list.delete(0, tk.END)
        
        # Get recent lookups from user settings
        recent_lookups = self.user_settings.get_recent_lookups()
        
        if not recent_lookups:
            self.recent_lookups_list.insert(tk.END, "No recent lookups")
            return
            
        # Add each recent lookup to the listbox
        for lookup in recent_lookups:
            headword = lookup.get('headword', '')
            
            # Display only the headword without language information
            self.recent_lookups_list.insert(tk.END, headword)
            
        # Apply same font as main headword list
        font = self.headword_list.cget("font")
        self.recent_lookups_list.config(font=font)
            
    def add_to_recent_lookups(self, entry):
        """Add an entry to the recent lookups list"""
        if not entry:
            return
            
        # Get required fields from the entry
        headword = entry.get('headword')
        metadata = entry.get('metadata', {})
        target_lang = metadata.get('target_language')
        definition_lang = metadata.get('definition_language')
        
        if not (headword and target_lang and definition_lang):
            return
            
        # Add to recent lookups in user settings
        self.user_settings.add_recent_lookup(headword, target_lang, definition_lang)
        
        # Update the UI
        self.update_recent_lookups_list()
    
    def update_queue_status(self):
        """Update the UI based on the current queue status"""
        # This method is called by the RequestManager when queue status changes
        # Ensure UI updates happen on the main thread
        self.root.after(0, self._update_queue_status_ui)
    
    def _update_queue_status_ui(self):
        """Update UI elements based on queue status (called on main thread)"""
        pending_count = self.request_manager.get_pending_count()
        active_count = self.request_manager.get_active_count()
        
        # Update status label
        if pending_count == 0 and active_count == 0:
            self.queue_status_label.config(text="API Queue: Idle", fg="#555555")
            self.queue_active_label.config(text="")
            self.queue_progress.pack_forget()
            self.cancel_queue_btn.pack_forget()
        else:
            total = pending_count + active_count
            self.queue_status_label.config(
                text=f"API Queue: {total} operation{'s' if total > 1 else ''}", 
                fg="#0066cc"
            )
            self.queue_active_label.config(
                text=f"Active: {active_count} | Pending: {pending_count}"
            )
            
            # Show progress bar if operations are in progress
            if active_count > 0:
                if not self.queue_progress.winfo_ismapped():
                    self.queue_progress.pack(side=tk.LEFT, padx=5)
                    # Start the indeterminate progress animation
                    self.queue_progress.start(15)  # Speed in ms
            else:
                self.queue_progress.pack_forget()
                self.queue_progress.stop()
            
            # Show cancel button if there are operations
            if not self.cancel_queue_btn.winfo_ismapped():
                self.cancel_queue_btn.pack(side=tk.RIGHT, padx=5)
    
    def periodic_ui_update(self):
        """Periodically update the UI status"""
        # Update the UI with current queue status
        self._update_queue_status_ui()
        
        # Schedule the next update
        self.root.after(self.queue_update_interval, self.periodic_ui_update)
    
    def cancel_all_requests(self):
        """Cancel all pending API requests"""
        count = self.request_manager.cancel_all_requests()
        self.show_status_message(f"Cancelled {count} API operation{'s' if count != 1 else ''}")
        # Re-enable the search button
        self.search_btn.config(state=tk.NORMAL)
        # Clear any notifications
        self.clear_notifications()
        
    def show_notification(self, message, headword, entry):
        """Show a notification for a completed request"""
        # Store the notification data for the view button
        self.latest_notification = {
            'headword': headword,
            'entry': entry
        }
        
        # Update notification label
        self.notification_label.config(text=message)
        
        # Show notification panel if it's not already visible
        if not self.notification_panel.winfo_ismapped():
            self.notification_panel.pack(side=tk.TOP, fill=tk.X, padx=5, pady=0, after=self.top_panel)
            
        # No longer automatically showing the entry - the user can click "View" if they want to
            
    def clear_notifications(self):
        """Clear all notifications"""
        self.notification_label.config(text="")
        self.notification_panel.pack_forget()
        self.latest_notification = None
        
    def show_notification_entry(self):
        """Show the entry from the latest notification"""
        if not hasattr(self, 'latest_notification') or not self.latest_notification:
            return
            
        headword = self.latest_notification['headword']
        entry = self.latest_notification['entry']
        
        # Update viewed headword
        self.viewed_headword = headword.lower()
        # Set user selection flag to false to ensure display isn't skipped
        self.user_selected_entry = False
        
        # Update current entry
        self.current_entry = entry
        
        # First display the entry to ensure its content is visible
        self.display_entry(entry)
        
        # Then select it in the list (without triggering another display operation)
        self.select_and_show_headword(headword.lower())
        
        # Clear the notification
        self.clear_notifications()
        
    def export_example_to_anki(self, meaning_index, example_index):
        """Export a specific example to Anki"""
        if not self.current_entry or not self.anki_connector:
            return
        
        try:
            meaning = self.current_entry["meanings"][meaning_index]
            example = meaning["examples"][example_index]
            
            focused_entry = {
                "headword": self.current_entry["headword"],
                "part_of_speech": self.current_entry.get("part_of_speech", ""),
                "metadata": self.current_entry["metadata"],
                "selected_meaning": meaning,
                "selected_example": example
            }
            
            # Check if we should skip confirmation
            settings = self.user_settings.get_settings()
            if settings.get('skip_confirmation', False):
                # Export directly without showing dialog
                self.direct_export_to_anki(focused_entry)
            else:
                # Show dialog for confirmation
                self.show_anki_export_dialog(focused_entry)
        except (IndexError, KeyError) as e:
            self.show_status_message(f"Error selecting example: {str(e)}")
            
    def direct_export_to_anki(self, focused_entry):
        """Export entry directly to Anki without confirmation"""
        settings = self.user_settings.get_settings()
        note_type = settings.get('default_note_type', 'Example-Based')
        note_config = settings.get('note_types', {}).get(note_type, {})
        
        field_mappings = note_config.get('field_mappings', {})
        empty_handling = note_config.get('empty_field_handling', {})
        
        mapper = AnkiFieldMapper(field_mappings, empty_handling)
        
        try:
            exporter = AnkiExporter(self.anki_connector, mapper, settings)
            note_id = exporter.export_entry(focused_entry, note_type)
            
            if note_id:
                self.show_status_message(f"Successfully exported '{focused_entry['headword']}' to Anki!")
            else:
                self.show_status_message("Export failed: No note ID returned")
        except Exception as e:
            self.show_status_message(f"Export failed: {str(e)}")
            
    def delete_previous_word(self, event):
        """Handle Ctrl+Backspace to delete the previous word in an entry widget"""
        entry_widget = event.widget
        
        # For Entry widgets, get() returns the entire contents without indices
        full_text = entry_widget.get()
        
        # Get the current cursor position
        cursor_pos = entry_widget.index(tk.INSERT)
        
        if cursor_pos == 0:  # If cursor is at the beginning of the entry, do nothing
            return "break"
            
        # Get the text from beginning to cursor
        text_before_cursor = full_text[:cursor_pos]
        
        # Find the start of the previous word
        word_start = cursor_pos
        
        # Skip any spaces directly to the left of the cursor
        for i in range(cursor_pos - 1, -1, -1):
            if text_before_cursor[i].isspace():
                word_start = i
            else:
                break
                
        # Now find the actual beginning of the word
        for i in range(word_start - 1, -1, -1):
            if text_before_cursor[i].isspace():
                word_start = i + 1
                break
            if i == 0:
                word_start = 0
                break
        
        # Delete from the start of the word to cursor position
        entry_widget.delete(word_start, cursor_pos)
        
        return "break"  # Prevents default Backspace behavior
        
    def add_standard_text_bindings(self, widget):
        """
        Add standard text editing keyboard shortcuts to an Entry or Text widget
        This makes text editing behavior more consistent with standard editors
        """
        # Select all text (Ctrl+A)
        if isinstance(widget, tk.Entry):
            def select_all_entry(event):
                event.widget.select_range(0, tk.END)
                event.widget.icursor(tk.END)  # Set cursor position to the end
                return "break"
            widget.bind("<Control-a>", select_all_entry)
            widget.bind("<Control-A>", select_all_entry)
            
        elif isinstance(widget, tk.Text):
            def select_all_text(event):
                event.widget.tag_add(tk.SEL, "1.0", tk.END)
                event.widget.mark_set(tk.INSERT, tk.END)
                return "break"
            widget.bind("<Control-a>", select_all_text)
            widget.bind("<Control-A>", select_all_text)
        
        # Copy selected text (Ctrl+C)
        def copy_selection(event):
            try:
                if isinstance(event.widget, tk.Entry):
                    if event.widget.selection_present():
                        selected_text = event.widget.selection_get()
                        event.widget.clipboard_clear()
                        event.widget.clipboard_append(selected_text)
                elif isinstance(event.widget, tk.Text):
                    if event.widget.tag_ranges(tk.SEL):
                        selected_text = event.widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                        event.widget.clipboard_clear()
                        event.widget.clipboard_append(selected_text)
            except Exception as e:
                print(f"Error copying text: {e}")
            return "break"
        
        widget.bind("<Control-c>", copy_selection)
        widget.bind("<Control-C>", copy_selection)
        
        # Delete previous word (Ctrl+Backspace)
        if isinstance(widget, tk.Entry):
            widget.bind("<Control-BackSpace>", self.delete_previous_word)
        elif isinstance(widget, tk.Text):
            widget.bind("<Control-BackSpace>", self.delete_previous_word_text)
        
        # Cut selected text (Ctrl+X)
        def cut_selection(event):
            try:
                if isinstance(event.widget, tk.Entry):
                    if event.widget.selection_present():
                        selected_text = event.widget.selection_get()
                        event.widget.clipboard_clear()
                        event.widget.clipboard_append(selected_text)
                        event.widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                elif isinstance(event.widget, tk.Text):
                    if event.widget.tag_ranges(tk.SEL):
                        selected_text = event.widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                        event.widget.clipboard_clear()
                        event.widget.clipboard_append(selected_text)
                        # Make sure text is editable before trying to cut
                        state = event.widget.cget("state")
                        if state == tk.DISABLED:
                            event.widget.config(state=tk.NORMAL)
                            event.widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                            event.widget.config(state=tk.DISABLED)
                        else:
                            event.widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except Exception as e:
                print(f"Error cutting text: {e}")
            return "break"
            
        # Only bind cut to editable widgets
        if isinstance(widget, tk.Entry) or (isinstance(widget, tk.Text) and widget.cget("state") != tk.DISABLED):
            widget.bind("<Control-x>", cut_selection)
            widget.bind("<Control-X>", cut_selection)
        
        # Paste text (Ctrl+V)
        def paste_text(event):
            try:
                clipboard_text = event.widget.clipboard_get()
                if not clipboard_text:
                    return "break"
                    
                if isinstance(event.widget, tk.Entry):
                    if event.widget.selection_present():
                        event.widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    event.widget.insert(tk.INSERT, clipboard_text)
                elif isinstance(event.widget, tk.Text):
                    if event.widget.tag_ranges(tk.SEL):
                        # Make sure text is editable before trying to paste
                        state = event.widget.cget("state")
                        if state == tk.DISABLED:
                            event.widget.config(state=tk.NORMAL)
                            event.widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                            event.widget.insert(tk.INSERT, clipboard_text)
                            event.widget.config(state=tk.DISABLED)
                        else:
                            event.widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                            event.widget.insert(tk.INSERT, clipboard_text)
                    else:
                        # Make sure text is editable before trying to paste
                        state = event.widget.cget("state")
                        if state == tk.DISABLED:
                            event.widget.config(state=tk.NORMAL)
                            event.widget.insert(tk.INSERT, clipboard_text)
                            event.widget.config(state=tk.DISABLED)
                        else:
                            event.widget.insert(tk.INSERT, clipboard_text)
            except Exception as e:
                print(f"Error pasting text: {e}")
            return "break"
            
        # Only bind paste to editable widgets
        if isinstance(widget, tk.Entry) or (isinstance(widget, tk.Text) and widget.cget("state") != tk.DISABLED):
            widget.bind("<Control-v>", paste_text)
            widget.bind("<Control-V>", paste_text)
            
    def delete_previous_word_text(self, event):
        """Handle Ctrl+Backspace to delete the previous word in a Text widget"""
        text_widget = event.widget
        
        # Check if widget is editable
        is_disabled = text_widget.cget("state") == tk.DISABLED
        if is_disabled:
            # If we can't edit, do nothing
            return "break"
            
        # Get the current cursor position (format is "line.column")
        cursor_pos = text_widget.index(tk.INSERT)
        
        # If at beginning of text, do nothing
        if cursor_pos == "1.0":
            return "break"
            
        # Split line and column
        line, col = map(int, cursor_pos.split('.'))
        
        if col == 0:
            # If at beginning of a line (but not the first line), move to end of previous line
            if line > 1:
                prev_line = line - 1
                prev_line_end = text_widget.index(f"{prev_line}.end")
                # Extract end column of previous line
                _, prev_col = map(int, prev_line_end.split('.'))
                
                # Get the text from previous line
                prev_line_text = text_widget.get(f"{prev_line}.0", prev_line_end)
                
                # Find the start of the last word in the previous line
                word_start = prev_col
                
                # Skip any spaces at the end
                for i in range(prev_col - 1, -1, -1):
                    if prev_line_text[i].isspace():
                        word_start = i
                    else:
                        break
                
                # Now find the beginning of the word
                for i in range(word_start - 1, -1, -1):
                    if prev_line_text[i].isspace():
                        word_start = i + 1
                        break
                    if i == 0:
                        word_start = 0
                        break
                
                # Delete from word start to the current cursor position
                text_widget.delete(f"{prev_line}.{word_start}", cursor_pos)
        else:
            # We're in the middle of a line
            # Get text from beginning of current line to cursor
            text_before_cursor = text_widget.get(f"{line}.0", cursor_pos)
            
            # Find the start of the previous word
            word_start = col
            
            # Skip any spaces directly to the left of the cursor
            for i in range(col - 1, -1, -1):
                if text_before_cursor[i].isspace():
                    word_start = i
                else:
                    break
                
            # Now find the actual beginning of the word
            for i in range(word_start - 1, -1, -1):
                if text_before_cursor[i].isspace():
                    word_start = i + 1
                    break
                if i == 0:
                    word_start = 0
                    break
            
            # Delete from word start to the current cursor position
            text_widget.delete(f"{line}.{word_start}", cursor_pos)
        
        return "break"  # Prevents default Backspace behavior

    def show_anki_export_dialog(self, focused_entry):
        """Show dialog to preview and confirm Anki export"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Export to Anki")
        dialog.geometry("500x600")
        dialog.transient(self.root)  # Set to be on top of the main window
        
        # Create preview frame
        preview_frame = ttk.LabelFrame(dialog, text="Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Generate preview
        settings = self.user_settings.get_settings()
        note_type = settings.get('default_note_type', 'Example-Based')
        note_config = settings.get('note_types', {}).get(note_type, {})
        
        field_mappings = note_config.get('field_mappings', {})
        empty_handling = note_config.get('empty_field_handling', {})
        
        mapper = AnkiFieldMapper(field_mappings, empty_handling)
        fields = mapper.map_entry_to_fields(focused_entry)
        
        # Display preview
        preview_text = scrolledtext.ScrolledText(preview_frame, height=10)
        preview_text.pack(fill=tk.BOTH, expand=True)
        
        preview_text.insert(tk.END, f"Note Type: {note_type}\n\n")
        preview_text.insert(tk.END, f"Deck: {note_config.get('deck', settings.get('default_deck', 'Default'))}\n\n")
        preview_text.insert(tk.END, "Fields:\n\n")
        
        for field_name, value in fields.items():
            if value:
                preview_text.insert(tk.END, f"{field_name}:\n{value}\n\n")
        
        preview_text.config(state=tk.DISABLED)
        
        # Status label
        status_var = tk.StringVar(value="Ready to export")
        status_label = ttk.Label(dialog, textvariable=status_var)
        status_label.pack(pady=5)
        
        # Button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Export button
        def do_export():
            export_btn.config(state=tk.DISABLED)
            status_var.set("Exporting...")
            dialog.update_idletasks()
            
            try:
                exporter = AnkiExporter(self.anki_connector, mapper, settings)
                note_id = exporter.export_entry(focused_entry, note_type)
                
                if note_id:
                    status_var.set("Successfully exported to Anki!")
                    export_btn.config(state=tk.NORMAL)
                    
                    # Change button color to green to indicate success
                    export_btn.config(style="Success.TButton")
                    
                    # Close dialog after a delay
                    dialog.after(1500, dialog.destroy)
                else:
                    status_var.set("Export failed: No note ID returned")
                    export_btn.config(state=tk.NORMAL)
            except Exception as e:
                status_var.set(f"Export failed: {str(e)}")
                export_btn.config(state=tk.NORMAL)
                
                # Change button color to red to indicate failure
                export_btn.config(style="Danger.TButton")
        
        # Create button styles
        style = ttk.Style()
        style.configure("Success.TButton", background="green", foreground="white")
        style.configure("Danger.TButton", background="red", foreground="white")
        
        export_btn = ttk.Button(button_frame, text="Export", command=do_export)
        export_btn.pack(side=tk.RIGHT, padx=5)
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = DictionaryApp(root)
    
    # Handle window close event to clean up resources
    def on_closing():
        if hasattr(app, 'request_manager'):
            app.request_manager.shutdown()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    root.mainloop()
