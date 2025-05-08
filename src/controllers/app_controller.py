"""
Application Controller

This module provides the main application controller, which coordinates
the overall application flow, initialization, and shutdown.
"""

import tkinter as tk
from typing import Dict, Any, Optional, List

from .base_controller import BaseController

class AppController(BaseController):
    """
    Main application controller.
    
    This controller manages the overall application lifecycle, coordinating
    the initialization of models, views, and other controllers, as well as
    handling application-wide events and operations.
    
    Attributes:
        root: The root Tkinter window
        models: Dictionary of models accessible to the controller
        views: Dictionary of views accessible to the controller
        controllers: Dictionary of child controllers
        event_bus: Event system for controller-related notifications
    """
    
    def __init__(self, root, models=None, views=None, event_bus=None):
        """
        Initialize the application controller.
        
        Args:
            root: The root Tkinter window
            models: Dictionary of models accessible to the controller
            views: Dictionary of views accessible to the controller
            event_bus: Event system for controller-related notifications
        """
        super().__init__(models, views, event_bus)
        
        self.root = root
        self.controllers = {}
        
        # Initialize application
        self._initialize_application()
    
    def _register_event_handlers(self):
        """Register event handlers for the application controller."""
        # Register application-level event handlers
        self.register_event_handler('window:closing', self._on_window_closing)
        self.register_event_handler('error:occurred', self._on_error)
        
        # Register action handlers
        self.register_event_handler('action:increase_text_size', self._on_increase_text_size)
        self.register_event_handler('action:decrease_text_size', self._on_decrease_text_size)
        self.register_event_handler('action:reset_text_size', self._on_reset_text_size)
        self.register_event_handler('action:toggle_fullscreen', self._on_toggle_fullscreen)
        self.register_event_handler('action:open_settings', self._on_open_settings)
        self.register_event_handler('action:export_dictionary', self._on_export_dictionary)
        self.register_event_handler('action:import_dictionary', self._on_import_dictionary)
    
    def _initialize_application(self):
        """Initialize the application components."""
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close_button)
        
        # Apply initial user settings
        self._apply_user_settings()
        
        # Initialize database and language data
        self._load_language_data()
        
        # Layout the main views
        self._layout_views()
        
        # Apply any other initialization
        self._post_initialization()
    
    def _apply_user_settings(self):
        """Apply user settings to the application."""
        user_model = self.get_model('user')
        if not user_model:
            return
            
        # Apply text scaling
        scale_factor = user_model.get_setting('text_scale_factor', 1.0)
        self._update_text_scaling(scale_factor)
        
        # Apply language settings
        main_window = self.get_view('main_window')
        if main_window:
            # Update UI status based on settings
            main_window.set_status_message("Applying settings...")
        
        # Apply theme settings
        theme = user_model.get_setting('theme', 'system')
        self._apply_theme(theme)
        
        # Notify that settings have been applied
        if self.event_bus:
            self.event_bus.publish('settings:applied', {
                'scale_factor': scale_factor,
                'theme': theme
            })
    
    def _load_language_data(self):
        """Load language data from the database."""
        dictionary_model = self.get_model('dictionary')
        if not dictionary_model:
            return
            
        main_window = self.get_view('main_window')
        if main_window:
            main_window.set_status_message("Loading language data...")
            
        # Get all available languages
        try:
            language_data = dictionary_model.get_all_languages()
            
            # Update language filter if available
            language_filter = self.get_view('language_filter')
            if language_filter:
                language_filter.set_available_languages(language_data)
                
            # Notify that language data has been loaded
            if self.event_bus:
                self.event_bus.publish('languages:loaded', {
                    'languages': language_data
                })
                
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:database', {
                    'message': f"Failed to load language data: {str(e)}"
                })
        finally:
            if main_window:
                main_window.set_status_message("Ready")
    
    def _layout_views(self):
        """Layout the main application views."""
        main_window = self.get_view('main_window')
        if not main_window:
            return
            
        # Get the main views
        search_panel = self.get_view('search_panel')
        entry_display = self.get_view('entry_display')
        language_filter = self.get_view('language_filter')
        
        # Layout in the main window
        main_frame = main_window.frame
        
        # Configure main grid - allocate maximum space to the entry display
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=0, minsize=150)  # Language filter - fixed width
        main_frame.grid_columnconfigure(1, weight=0, minsize=200)  # Search panel - fixed width
        main_frame.grid_columnconfigure(2, weight=3)  # Entry display - give it maximum possible space
        
        # Layout the views
        if language_filter:
            language_filter.frame.grid(row=0, column=0, sticky="ns", padx=5, pady=5)
            
        if search_panel:
            search_panel.frame.grid(row=0, column=1, sticky="ns", padx=5, pady=5)
            
        if entry_display:
            # Give the entry display more space for long definitions and ensure it expands properly
            entry_display.frame.grid(row=0, column=2, sticky="nsew", padx=10, pady=5)
    
    def _post_initialization(self):
        """Perform post-initialization tasks."""
        # Update API connection status
        self._update_api_status()
        
        # Update Anki connection status
        self._update_anki_status()
        
        # Check if any recent lookups to display
        self._load_recent_lookups()
        
        # Start background monitoring for clipboard if enabled
        user_model = self.get_model('user')
        if user_model and user_model.get_setting('monitor_clipboard', False):
            search_panel = self.get_view('search_panel')
            if search_panel:
                search_panel.start_clipboard_monitoring()
    
    def _update_api_status(self):
        """Update the API connection status in the UI."""
        api_model = self.get_model('api')
        main_window = self.get_view('main_window')
        
        if not api_model or not main_window:
            return
            
        # Check if API client is initialized
        connected = api_model.client is not None
        
        # Update main window status
        main_window.set_api_status(connected)
    
    def _update_anki_status(self):
        """Update the Anki connection status in the UI."""
        anki_model = self.get_model('anki')
        main_window = self.get_view('main_window')
        
        if not anki_model or not main_window:
            return
            
        # Test Anki connection
        connected = anki_model.test_connection()
        
        # Update main window status
        main_window.set_anki_status(connected)
    
    def _load_recent_lookups(self):
        """Load recent lookups from user settings."""
        user_model = self.get_model('user')
        search_panel = self.get_view('search_panel')
        
        if not user_model or not search_panel:
            return
            
        # Get recent lookups
        recent_lookups = user_model.get_recent_lookups()
        
        # Update search panel
        if recent_lookups:
            search_panel.update_history_list(recent_lookups)
    
    def _update_text_scaling(self, scale_factor: float):
        """
        Update text scaling throughout the application.
        
        Args:
            scale_factor: The text scale factor to apply
        """
        # Update scale factor in all views
        for view_name, view in self.views.items():
            if hasattr(view, 'scale_factor'):
                view.scale_factor = scale_factor
                
            if hasattr(view, 'update_scale'):
                view.update_scale()
                
        # Save the scale factor to user settings
        user_model = self.get_model('user')
        if user_model:
            user_model.set_setting('text_scale_factor', scale_factor)
            
        # Notify of scale factor change
        if self.event_bus:
            self.event_bus.publish('ui:scale_factor_changed', {
                'scale_factor': scale_factor
            })
    
    def _apply_theme(self, theme: str):
        """
        Apply a theme to the application.
        
        Args:
            theme: The theme to apply ('light', 'dark', or 'system')
        """
        import platform
        import tkinter as tk
        from tkinter import ttk
        
        # Define color schemes for each theme
        # Each theme defines colors for various UI elements
        color_schemes = {
            'light': {
                'bg': '#FFFFFF',  # Background
                'fg': '#000000',  # Foreground text
                'select_bg': '#CCE4F7',  # Selection background
                'select_fg': '#000000',  # Selection text
                'button': '#F0F0F0',  # Button background
                'button_active': '#E0E0E0',  # Button when pressed
                'entry_bg': '#FFFFFF',  # Entry field background
                'entry_fg': '#000000',  # Entry field text
                'highlight_bg': '#E8F0F8',  # Highlight background
                'highlight_fg': '#000000',  # Highlight text
                'listbox_bg': '#FFFFFF',  # Listbox background
                'frame_bg': '#F5F5F5',  # Frame background
                'scrollbar': '#C0C0C0',  # Scrollbar color
                'heading_fg': '#000000',  # Heading text
                'border': '#C0C0C0',  # Border color
            },
            'dark': {
                'bg': '#2E2E2E',  # Background
                'fg': '#E0E0E0',  # Foreground text
                'select_bg': '#4A6984',  # Selection background
                'select_fg': '#FFFFFF',  # Selection text
                'button': '#3E3E3E',  # Button background
                'button_active': '#505050',  # Button when pressed
                'entry_bg': '#3E3E3E',  # Entry field background
                'entry_fg': '#E0E0E0',  # Entry field text
                'highlight_bg': '#404D5D',  # Highlight background
                'highlight_fg': '#E0E0E0',  # Highlight text
                'listbox_bg': '#2E2E2E',  # Listbox background
                'frame_bg': '#2A2A2A',  # Frame background
                'scrollbar': '#505050',  # Scrollbar color
                'heading_fg': '#E0E0E0',  # Heading text
                'border': '#505050',  # Border color
            },
            'system': {}  # Will be determined based on system settings
        }
        
        # Determine system theme if 'system' is selected
        if theme == 'system':
            # Try to detect system theme (this is platform-specific)
            system_theme = 'light'  # Default to light
            
            # On Windows, check registry
            if platform.system() == 'Windows':
                try:
                    import winreg
                    registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                    key = winreg.OpenKey(registry, r'Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize')
                    # AppsUseLightTheme = 0 means dark theme
                    use_light_theme = winreg.QueryValueEx(key, 'AppsUseLightTheme')[0]
                    system_theme = 'light' if use_light_theme else 'dark'
                except:
                    # If any error occurs, fall back to light theme
                    system_theme = 'light'
                    
            # On macOS, check dark mode
            elif platform.system() == 'Darwin':
                try:
                    import subprocess
                    result = subprocess.run(
                        ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                        capture_output=True, text=True
                    )
                    # If 'Dark' is returned, use dark theme
                    system_theme = 'dark' if 'dark' in result.stdout.lower() else 'light'
                except:
                    # If any error occurs, fall back to light theme
                    system_theme = 'light'
                    
            # For all other platforms or if detection fails, use light theme
            
            # Use the detected system theme
            theme = system_theme
            
        # Get the theme colors
        colors = color_schemes.get(theme, color_schemes['light'])
        
        # Get the root window
        root = self.root
        if not root:
            return
            
        # Apply theme to the root window
        style = ttk.Style(root)
        
        # Configure ttk styles for various widgets
        style.configure('TFrame', background=colors['frame_bg'])
        style.configure('TLabel', background=colors['bg'], foreground=colors['fg'])
        style.configure('TButton', 
                        background=colors['button'],
                        foreground=colors['fg'],
                        bordercolor=colors['border'])
        style.map('TButton',
                 background=[('active', colors['button_active'])])
        style.configure('TEntry',
                        fieldbackground=colors['entry_bg'],
                        foreground=colors['entry_fg'],
                        bordercolor=colors['border'])
        style.configure('TCombobox',
                        fieldbackground=colors['entry_bg'],
                        foreground=colors['entry_fg'],
                        selectbackground=colors['select_bg'],
                        selectforeground=colors['select_fg'])
        style.configure('TScrollbar', background=colors['scrollbar'], troughcolor=colors['bg'])
        style.configure('TNotebook', background=colors['bg'])
        style.configure('TNotebook.Tab', 
                        background=colors['bg'],
                        foreground=colors['fg'],
                        padding=[5, 2])
        style.map('TNotebook.Tab',
                 background=[('selected', colors['highlight_bg'])],
                 foreground=[('selected', colors['highlight_fg'])])
                 
        # Apply theme to tk widgets that aren't covered by ttk styling
        root.configure(background=colors['bg'])
        
        # Set theme configuration for text widgets (used in many views)
        text_config = {
            'background': colors['bg'],
            'foreground': colors['fg'],
            'selectbackground': colors['select_bg'],
            'selectforeground': colors['select_fg'],
            'insertbackground': colors['fg'],  # Text cursor color
        }
        
        # Apply theme to all views
        for view_name, view in self.views.items():
            # If view has a method to apply theme, call it
            if hasattr(view, 'apply_theme'):
                view.apply_theme(theme, colors)
            # Otherwise, try to set colors on common widgets
            elif hasattr(view, 'frame'):
                view.frame.configure(background=colors['bg'])
                
        # Save the theme setting
        user_model = self.get_model('user')
        if user_model:
            user_model.set_setting('theme', theme)
            
        # Notify of theme change
        self.publish_event('ui:theme_changed', {
            'theme': theme
        })
    
    def add_controller(self, name: str, controller):
        """
        Add a child controller to the application.
        
        Args:
            name: Name to identify the controller
            controller: The controller instance to add
        """
        self.controllers[name] = controller
        
        # Notify of controller addition
        if self.event_bus:
            self.event_bus.publish('controller:added', {
                'name': name
            })
    
    def get_controller(self, name: str):
        """
        Get a child controller by name.
        
        Args:
            name: Name of the controller to get
            
        Returns:
            The controller instance or None if not found
        """
        return self.controllers.get(name)
    
    def start(self):
        """Start the application main loop."""
        try:
            # Log application start
            self.log_info("Starting application main loop")
            
            # Notify application start
            if self.event_bus:
                self.event_bus.publish('application:started', {})
                
            # Start the Tkinter main loop
            self.root.mainloop()
            
        except Exception as e:
            # Log the error
            self.log_error("Error in application main loop", exc_info=True, error=str(e))
            
            # Notify of fatal error
            if self.event_bus:
                self.event_bus.publish('error:fatal', {
                    'message': f"Fatal application error: {str(e)}"
                })
                
            # Ensure clean shutdown
            self.shutdown()
            
            # Re-raise the exception
            raise
    
    def shutdown(self):
        """Shutdown the application gracefully."""
        self.log_info("Shutting down application")
        
        # Notify of shutdown
        if self.event_bus:
            self.event_bus.publish('application:shutdown', {})
            
        # Shutdown child controllers
        for controller_name, controller in self.controllers.items():
            self.log_debug(f"Shutting down {controller_name} controller")
            if hasattr(controller, 'shutdown'):
                controller.shutdown()
                
        # Clean up resources
        self._cleanup_resources()
        
        self.log_info("Application shutdown complete")
    
    def _cleanup_resources(self):
        """Clean up application resources."""
        self.log_debug("Cleaning up application resources")
        
        # Save user settings
        user_model = self.get_model('user')
        if user_model:
            self.log_debug("Saving user settings")
            user_model.save_settings()
            
        # Shut down request service
        request_service = self.get_model('request_service')
        if request_service:
            self.log_debug("Shutting down request service")
            request_service.shutdown()
            
        # Clean up any temporary files
        self._cleanup_temp_files()
            
        self.log_debug("Resource cleanup complete")
        
    def _cleanup_temp_files(self):
        """Clean up temporary files created by the application."""
        import os
        import tempfile
        import glob
        
        try:
            # Clean up temp files with our app prefix
            temp_dir = tempfile.gettempdir()
            temp_files = glob.glob(os.path.join(temp_dir, "deepdict_temp_*"))
            
            if temp_files:
                self.log_debug(f"Cleaning up {len(temp_files)} temporary files")
                
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        self.log_warning(f"Failed to remove temp file {temp_file}", error=str(e))
        except Exception as e:
            self.log_warning("Error during temp file cleanup", error=str(e))
    
    # Event handlers
    
    def _on_window_close_button(self):
        """Handle window close button click."""
        # Notify of window closing
        if self.event_bus:
            self.event_bus.publish('window:closing', {})
            
        # Shutdown the application
        self.shutdown()
        
        # Destroy the root window
        self.root.destroy()
    
    def _on_window_closing(self, data: Optional[Dict[str, Any]] = None):
        """Handle window closing event."""
        # This event is dispatched by the main window view
        # We've already registered the window close handler, so no need to duplicate
        pass
    
    def _on_error(self, data: Optional[Dict[str, Any]] = None):
        """Handle error events."""
        if not data:
            return
            
        message = data.get('message', 'An error occurred')
        severity = data.get('severity', 'error')
        
        # Update status message
        main_window = self.get_view('main_window')
        if main_window:
            main_window.set_status_message(f"Error: {message}")
            
        # Log the error based on severity
        if severity == 'critical':
            self.log_error(message, error_type='critical')
        elif severity == 'warning':
            self.log_warning(message, event_data=data)
        else:
            self.log_error(message, event_data=data)
    
    def _on_increase_text_size(self, data: Optional[Dict[str, Any]] = None):
        """Handle increase text size action."""
        user_model = self.get_model('user')
        if not user_model:
            return
            
        # Get current scale factor
        scale_factor = user_model.get_setting('text_scale_factor', 1.0)
        
        # Increase by 10%, max 2.0
        scale_factor = min(2.0, scale_factor + 0.1)
        
        # Update scaling
        self._update_text_scaling(scale_factor)
    
    def _on_decrease_text_size(self, data: Optional[Dict[str, Any]] = None):
        """Handle decrease text size action."""
        user_model = self.get_model('user')
        if not user_model:
            return
            
        # Get current scale factor
        scale_factor = user_model.get_setting('text_scale_factor', 1.0)
        
        # Decrease by 10%, min 0.5
        scale_factor = max(0.5, scale_factor - 0.1)
        
        # Update scaling
        self._update_text_scaling(scale_factor)
    
    def _on_reset_text_size(self, data: Optional[Dict[str, Any]] = None):
        """Handle reset text size action."""
        # Reset to default scale factor (1.0)
        self._update_text_scaling(1.0)
    
    def _on_toggle_fullscreen(self, data: Optional[Dict[str, Any]] = None):
        """Handle toggle fullscreen action."""
        # The main window view already handles this action
        self.log_trace("Fullscreen action handled by main window")
        pass
    
    def _on_open_settings(self, data: Optional[Dict[str, Any]] = None):
        """Handle open settings action."""
        self.log_info("Opening settings dialog")
        
        # Get the settings controller
        settings_controller = self.get_controller('settings')
        if settings_controller:
            # Show settings dialog
            settings_controller.show_settings_dialog(self.root)
        else:
            # If settings controller not available, just publish the event
            self.log_debug("Settings controller not available, publishing event")
            self.publish_event('settings:dialog_requested', {
                'parent_window': self.root
            })
    
    def _on_export_dictionary(self, data: Optional[Dict[str, Any]] = None):
        """
        Handle export dictionary action.
        
        Exports dictionary entries to a JSON file selected by the user.
        """
        # Get the main window for dialog parent
        main_window = self.get_view('main_window')
        if not main_window or not main_window.root:
            self.publish_event('error:dialog', {
                'message': "Cannot export dictionary: No window available"
            })
            return
            
        # Get dictionary model
        dictionary_model = self.get_model('dictionary')
        if not dictionary_model:
            self.publish_event('error:dialog', {
                'message': "Cannot export dictionary: Dictionary model not available"
            })
            return
        
        # Get user settings for default directory
        user_model = self.get_model('user')
        last_export_dir = user_model.get_setting('last_export_dir', '') if user_model else ''
        
        # Import tkinter file dialog here to avoid global import
        from tkinter import filedialog
        
        # Show file dialog
        file_path = filedialog.asksaveasfilename(
            parent=main_window.root,
            title="Export Dictionary", 
            defaultextension=".json",
            initialdir=last_export_dir if last_export_dir else None,
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        # If user canceled, exit
        if not file_path:
            return
            
        # Remember the directory for next time
        if user_model:
            import os
            user_model.set_setting('last_export_dir', os.path.dirname(file_path))
        
        # Show an indeterminate progress indicator
        main_window.set_status_message("Exporting dictionary...")
        
        try:
            # Get all entries
            # First get all languages to create filters
            languages = dictionary_model.get_all_languages()
            target_languages = languages.get('target_languages', [])
            
            all_entries = []
            
            # For each target language, get entries
            for target_lang in target_languages:
                entries = dictionary_model.search_entries({
                    'target_language': target_lang
                })
                all_entries.extend(entries)
            
            # Create export data
            export_data = {
                'entries': all_entries,
                'metadata': {
                    'export_date': self._get_current_datetime(),
                    'entry_count': len(all_entries)
                }
            }
            
            # Save to file
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            # Show success message
            main_window.set_status_message(f"Exported {len(all_entries)} entries to {file_path}")
            
            # Publish export completed event
            self.publish_event('dictionary:export_completed', {
                'file_path': file_path,
                'entry_count': len(all_entries)
            })
            
        except Exception as e:
            # Show error message
            main_window.set_status_message("Export failed")
            
            self.publish_event('error:dialog', {
                'message': f"Export failed: {str(e)}"
            })
            
            # Publish export failed event
            self.publish_event('dictionary:export_failed', {
                'file_path': file_path,
                'error': str(e)
            })
    
    def _on_import_dictionary(self, data: Optional[Dict[str, Any]] = None):
        """
        Handle import dictionary action.
        
        Imports dictionary entries from a JSON file selected by the user.
        """
        # Get the main window for dialog parent
        main_window = self.get_view('main_window')
        if not main_window or not main_window.root:
            self.publish_event('error:dialog', {
                'message': "Cannot import dictionary: No window available"
            })
            return
            
        # Get dictionary model
        dictionary_model = self.get_model('dictionary')
        if not dictionary_model:
            self.publish_event('error:dialog', {
                'message': "Cannot import dictionary: Dictionary model not available"
            })
            return
        
        # Get user settings for default directory
        user_model = self.get_model('user')
        last_import_dir = user_model.get_setting('last_import_dir', '') if user_model else ''
        
        # Import tkinter file dialog and messagebox here to avoid global import
        from tkinter import filedialog, messagebox
        
        # Show file dialog
        file_path = filedialog.askopenfilename(
            parent=main_window.root,
            title="Import Dictionary", 
            initialdir=last_import_dir if last_import_dir else None,
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        # If user canceled, exit
        if not file_path:
            return
            
        # Remember the directory for next time
        if user_model:
            import os
            user_model.set_setting('last_import_dir', os.path.dirname(file_path))
        
        # Show an indeterminate progress indicator
        main_window.set_status_message("Importing dictionary...")
        
        try:
            # Load the file
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Extract entries
            if 'entries' not in import_data:
                raise ValueError("Invalid import file: 'entries' key not found")
                
            entries = import_data['entries']
            
            # Confirm import with user
            entry_count = len(entries)
            confirm = messagebox.askyesno(
                "Confirm Import",
                f"Import {entry_count} entries from {file_path}?\n\n"
                "Note: This will add entries to your dictionary. "
                "Duplicate entries (same headword and languages) will be skipped.",
                parent=main_window.root
            )
            
            if not confirm:
                main_window.set_status_message("Import canceled")
                return
            
            # Import entries
            success_count = 0
            skip_count = 0
            
            for entry in entries:
                # Validate entry
                if dictionary_model.is_valid_entry(entry):
                    # Add entry
                    try:
                        # Try to save the entry
                        entry_id = dictionary_model.save_entry(entry)
                        
                        if entry_id:
                            success_count += 1
                        else:
                            skip_count += 1
                    except Exception:
                        skip_count += 1
                else:
                    skip_count += 1
            
            # Show success message
            main_window.set_status_message(
                f"Imported {success_count} entries, skipped {skip_count} entries"
            )
            
            # Publish import completed event
            self.publish_event('dictionary:import_completed', {
                'file_path': file_path,
                'success_count': success_count,
                'skip_count': skip_count,
                'total_count': entry_count
            })
            
            # Refresh the UI
            self.publish_event('dictionary:data_changed', {})
            
        except Exception as e:
            # Show error message
            main_window.set_status_message("Import failed")
            
            self.publish_event('error:dialog', {
                'message': f"Import failed: {str(e)}"
            })
            
            # Publish import failed event
            self.publish_event('dictionary:import_failed', {
                'file_path': file_path,
                'error': str(e)
            })
            
    def _get_current_datetime(self) -> str:
        """
        Get current date and time in ISO format.
        
        Returns:
            Current date and time as a string
        """
        from datetime import datetime
        return datetime.now().isoformat()