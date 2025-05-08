"""
Settings Controller

This module provides a controller for managing application settings, including
user preferences, language settings, and the settings dialog interface.
"""

from typing import Dict, Any, Optional, Callable, List
import tkinter as tk

from .base_controller import BaseController
from ..views.settings_view import SettingsView  # Will create this next

class SettingsController(BaseController):
    """
    Controller for application settings management.
    
    This controller handles user settings operations, including UI interaction,
    settings persistence, and coordination of settings changes across the
    application.
    
    Attributes:
        models: Dictionary of models accessible to the controller
        views: Dictionary of views accessible to the controller
        event_bus: Event system for controller-related notifications
        settings_view: Reference to the settings dialog view
    """
    
    def __init__(self, models=None, views=None, event_bus=None):
        """
        Initialize the settings controller.
        
        Args:
            models: Dictionary of models accessible to the controller
            views: Dictionary of views accessible to the controller
            event_bus: Event system for controller-related notifications
        """
        super().__init__(models, views, event_bus)
        self.settings_view = None
        
        # Register for settings-related events
        self._register_event_handlers()
    
    def _register_event_handlers(self):
        """Register event handlers for settings events."""
        self.register_event_handler('settings:dialog_requested', self._on_settings_dialog_requested)
        self.register_event_handler('settings:update_requested', self._on_settings_update_requested)
        self.register_event_handler('settings:text_scale_changed', self._on_text_scale_changed)
        self.register_event_handler('settings:language_changed', self._on_language_changed)
        
        # Anki settings
        self.register_event_handler('settings:anki_config_requested', self._on_anki_config_requested)
        self.register_event_handler('settings:anki_config_updated', self._on_anki_config_updated)
    
    def show_settings_dialog(self, parent_window: tk.Tk = None):
        """
        Show the settings dialog.
        
        Args:
            parent_window: Parent window for the dialog
        """
        # If no parent window is provided, use the main window from views
        if not parent_window and 'main_window' in self.views:
            parent_window = self.views['main_window'].root
        
        # Check if we have a parent window
        if not parent_window:
            self.publish_event('error:dialog', {
                'message': "Cannot show settings dialog: No parent window available"
            })
            return
        
        # Get user model
        user_model = self.get_model('user')
        if not user_model:
            self.publish_event('error:dialog', {
                'message': "Cannot show settings dialog: User model not available"
            })
            return
        
        # Create and show the settings dialog
        if 'settings' in self.views:
            settings_view = self.views['settings']
            settings_view.show(parent_window)
        else:
            # Create a new settings view
            self.settings_view = SettingsView(
                parent_window, 
                user_model,
                self.event_bus
            )
            
            # Store the view for later use
            if 'settings' not in self.views:
                self.views['settings'] = self.settings_view
    
    def update_settings(self, settings: Dict[str, Any]):
        """
        Update application settings.
        
        Args:
            settings: Dictionary of settings to update
        """
        user_model = self.get_model('user')
        if not user_model:
            self.publish_event('error:dialog', {
                'message': "Cannot update settings: User model not available"
            })
            return
        
        # Update settings in user model
        user_model.update_settings(settings)
        
        # Notify that settings have been updated
        self.publish_event('settings:updated', settings)
        
        # Apply settings to the application
        self._apply_settings(settings)
    
    def _apply_settings(self, settings: Dict[str, Any]):
        """
        Apply settings to the application.
        
        Args:
            settings: Dictionary of settings to apply
        """
        # Apply text scaling if updated
        if 'text_scale_factor' in settings:
            self._apply_text_scaling(settings['text_scale_factor'])
        
        # Apply language settings if any language setting is updated
        language_keys = ['target_language', 'source_language', 'definition_language']
        if any(key in settings for key in language_keys):
            self._apply_language_settings(settings)
        
        # Apply Anki settings if updated
        anki_keys = ['anki_enabled', 'anki_url', 'default_deck', 'default_note_type', 'note_types']
        if any(key in settings for key in anki_keys):
            self._apply_anki_settings(settings)
    
    def _apply_text_scaling(self, scale_factor: float):
        """
        Apply text scaling to all views.
        
        Args:
            scale_factor: The text scale factor to apply
        """
        # Update scale factor in all views
        for view_name, view in self.views.items():
            if hasattr(view, 'update_scale'):
                view.update_scale(scale_factor)
        
        # Notify that text scaling has been applied
        self.publish_event('ui:text_scale_applied', {
            'scale_factor': scale_factor
        })
    
    def _apply_language_settings(self, settings: Dict[str, Any]):
        """
        Apply language settings to components that depend on language.
        
        Args:
            settings: Dictionary of settings with language updates
        """
        # Update language filter view if available
        if 'language_filter' in self.views:
            language_filter = self.views['language_filter']
            
            # Update selected language if target_language is in settings
            if 'target_language' in settings:
                language_filter.set_target_language(settings['target_language'])
            
            # Update definition language if in settings
            if 'definition_language' in settings:
                language_filter.set_definition_language(settings['definition_language'])
        
        # Notify that language settings have been applied
        self.publish_event('language:settings_applied', {
            'target_language': settings.get('target_language'),
            'source_language': settings.get('source_language'),
            'definition_language': settings.get('definition_language')
        })
    
    def _apply_anki_settings(self, settings: Dict[str, Any]):
        """
        Apply Anki settings to Anki components.
        
        Args:
            settings: Dictionary of settings with Anki updates
        """
        anki_model = self.get_model('anki')
        if not anki_model:
            return
        
        # Update Anki connection URL if provided
        if 'anki_url' in settings:
            anki_model.update_connection_url(settings['anki_url'])
        
        # Update field mappings if note types are updated
        if 'note_types' in settings:
            anki_model.update_field_mappings(settings['note_types'])
        
        # Notify that Anki settings have been applied
        self.publish_event('anki:settings_applied', {
            'anki_enabled': settings.get('anki_enabled', False),
            'anki_url': settings.get('anki_url'),
            'default_deck': settings.get('default_deck'),
            'default_note_type': settings.get('default_note_type')
        })
    
    def get_settings(self) -> Dict[str, Any]:
        """
        Get current application settings.
        
        Returns:
            Dictionary of current settings
        """
        user_model = self.get_model('user')
        if not user_model:
            return {}
        
        return user_model.get_settings()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a specific setting.
        
        Args:
            key: The setting key to retrieve
            default: Default value if setting is not found
            
        Returns:
            The setting value or default
        """
        user_model = self.get_model('user')
        if not user_model:
            return default
        
        return user_model.get_setting(key, default)
    
    def reset_to_defaults(self):
        """Reset settings to default values."""
        user_model = self.get_model('user')
        if not user_model:
            self.publish_event('error:dialog', {
                'message': "Cannot reset settings: User model not available"
            })
            return
        
        # Get default settings
        default_settings = user_model.get_default_settings()
        
        # Update settings to defaults
        self.update_settings(default_settings)
        
        # Notify that settings have been reset
        self.publish_event('settings:reset_to_defaults', {})
    
    def add_recent_lookup(self, headword: str, target_lang: str, definition_lang: str) -> List[Dict[str, str]]:
        """
        Add a recent lookup to the history.
        
        Args:
            headword: The headword that was looked up
            target_lang: The target language of the lookup
            definition_lang: The definition language of the lookup
            
        Returns:
            List of recent lookups after update
        """
        user_model = self.get_model('user')
        if not user_model:
            return []
        
        recent_lookups = user_model.add_recent_lookup(headword, target_lang, definition_lang)
        
        # Notify that recent lookups have been updated
        self.publish_event('lookups:history_updated', {
            'recent_lookups': recent_lookups
        })
        
        return recent_lookups
    
    def get_recent_lookups(self) -> List[Dict[str, str]]:
        """
        Get the list of recent lookups.
        
        Returns:
            List of recent lookups
        """
        user_model = self.get_model('user')
        if not user_model:
            return []
        
        return user_model.get_recent_lookups()
    
    # Event handlers
    
    def _on_settings_dialog_requested(self, data: Optional[Dict[str, Any]] = None):
        """Handle settings dialog requested event."""
        parent_window = None
        if data and 'parent_window' in data:
            parent_window = data['parent_window']
            
        self.show_settings_dialog(parent_window)
    
    def _on_settings_update_requested(self, data: Optional[Dict[str, Any]] = None):
        """Handle settings update requested event."""
        if not data:
            return
            
        settings = data.get('settings', {})
        if settings:
            self.update_settings(settings)
    
    def _on_text_scale_changed(self, data: Optional[Dict[str, Any]] = None):
        """Handle text scale changed event."""
        if not data:
            return
            
        scale_factor = data.get('scale_factor')
        if scale_factor is not None:
            self.update_settings({'text_scale_factor': scale_factor})
    
    def _on_language_changed(self, data: Optional[Dict[str, Any]] = None):
        """Handle language changed event."""
        if not data:
            return
            
        settings = {}
        if 'target_language' in data:
            settings['target_language'] = data['target_language']
            
        if 'source_language' in data:
            settings['source_language'] = data['source_language']
            
        if 'definition_language' in data:
            settings['definition_language'] = data['definition_language']
            
        if settings:
            self.update_settings(settings)
    
    def _on_anki_config_requested(self, data: Optional[Dict[str, Any]] = None):
        """Handle Anki configuration dialog requested event."""
        # This will be implemented with the AnkiConfigView
        self.publish_event('anki:config_dialog_requested', data or {})
    
    def _on_anki_config_updated(self, data: Optional[Dict[str, Any]] = None):
        """Handle Anki configuration updated event."""
        if not data:
            return
            
        anki_settings = {}
        anki_keys = ['anki_enabled', 'anki_url', 'default_deck', 'default_note_type', 'note_types', 'auto_export', 'skip_confirmation', 'tags']
        
        for key in anki_keys:
            if key in data:
                anki_settings[key] = data[key]
                
        if anki_settings:
            self.update_settings(anki_settings)