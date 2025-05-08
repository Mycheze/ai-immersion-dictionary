"""
User Model

This module provides the data model for user settings and preferences,
including persistence, retrieval, and event notifications for changes.
"""

import os
import json
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime

class UserModel:
    """
    Model for user settings and preferences.
    
    This class encapsulates all user data operations, providing a clean interface
    for working with user settings and maintaining user state across sessions.
    
    Attributes:
        settings_file: Path to the settings file
        settings: Dictionary of user settings
        event_bus: Event system for model-related notifications
        change_callbacks: Callbacks for specific setting changes
    """
    
    def __init__(self, settings_file='user_settings.json', event_bus=None):
        """
        Initialize the user model.
        
        Args:
            settings_file: Path to the settings file
            event_bus: Optional event bus for notifications
        """
        self.settings_file = settings_file
        self.event_bus = event_bus
        self.settings = self.load_settings()
        self.change_callbacks: Dict[str, List[Callable]] = {}
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Load settings from file or create defaults if file doesn't exist.
        
        Returns:
            Dictionary of user settings
        """
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                if self.event_bus:
                    self.event_bus.publish('error:settings', {
                        'message': f"Could not load settings file, using defaults. Error: {e}",
                        'file': self.settings_file
                    })
                return self.get_default_settings()
        else:
            return self.get_default_settings()
    
    def get_default_settings(self) -> Dict[str, Any]:
        """
        Get default settings for a new user.
        
        Returns:
            Dictionary of default settings
        """
        # Set default definition language
        default_definition_lang = 'English'
        
        return {
            'target_language': 'Czech',  # Language being learned
            'source_language': default_definition_lang,  # Base language of the learner
            'definition_language': default_definition_lang,  # Language for definitions
            
            # UI settings
            'text_scale_factor': 1.0,  # Default scale factor for text (1.0 = 100%)
            'theme': 'system',  # system, light, dark
            'layout_mode': 'default',  # default, compact, expanded
            'show_phonetics': True,  # Show phonetic pronunciations
            'recent_lookups': [],  # List of 5 most recent lookups
            
            # Anki integration settings
            'anki_enabled': False,
            'anki_url': 'http://localhost:8765',
            'default_deck': 'Language Learning',
            'default_note_type': 'Example-Based',
            'note_types': {
                'Example-Based': {
                    'deck': 'Czech Examples',
                    'field_mappings': {
                        'Word': 'headword',
                        'Definition': 'selected_meaning.definition', 
                        'Example': 'selected_example.sentence',
                        'Translation': 'selected_example.translation'
                    },
                    'empty_field_handling': {
                        'Translation': {'action': 'default', 'default': '[No translation]'},
                        'Grammar': {'action': 'skip'}
                    }
                }
            },
            'auto_export': False,
            'skip_confirmation': False,
            'tags': ['AI-Dictionary'],
            
            # Custom languages added by the user
            'custom_languages': []
        }
    
    def save_settings(self) -> bool:
        """
        Save current settings to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists if settings file is in a subdirectory
            settings_dir = os.path.dirname(self.settings_file)
            if settings_dir and not os.path.exists(settings_dir):
                os.makedirs(settings_dir, exist_ok=True)
                
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
                
            # Notify of successful save if event bus exists
            if self.event_bus:
                self.event_bus.publish('settings:saved', {
                    'file': self.settings_file,
                    'timestamp': datetime.now().isoformat()
                })
                
            return True
            
        except Exception as e:
            # Notify of error if event bus exists
            if self.event_bus:
                self.event_bus.publish('error:settings', {
                    'message': f"Error saving settings: {str(e)}",
                    'file': self.settings_file
                })
            return False
    
    def get_settings(self) -> Dict[str, Any]:
        """
        Get the complete settings dictionary.
        
        Returns:
            Dictionary of all user settings
        """
        return self.settings.copy()
    
    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """
        Update settings with new values and save to file.
        
        Args:
            new_settings: Dictionary of settings to update
            
        Returns:
            True if successful, False otherwise
        """
        # Track changed settings for notifications
        changed_settings = {}
        
        # Special handling for language settings to maintain consistency
        if 'definition_language' in new_settings and 'source_language' not in new_settings:
            new_settings['source_language'] = new_settings['definition_language']
        elif 'source_language' in new_settings and 'definition_language' not in new_settings:
            new_settings['definition_language'] = new_settings['source_language']
        
        # Update settings
        for key, value in new_settings.items():
            if key not in self.settings or self.settings[key] != value:
                changed_settings[key] = value
                self.settings[key] = value
        
        # Save settings to file
        success = self.save_settings()
        
        # Notify of changes
        if success and changed_settings and self.event_bus:
            self.event_bus.publish('settings:updated', {
                'changed_settings': changed_settings
            })
            
            # Call specific callbacks for changed settings
            for key, value in changed_settings.items():
                self._notify_setting_change(key, value)
        
        return success
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a specific setting value.
        
        Args:
            key: The setting key to retrieve
            default: Default value if setting doesn't exist
            
        Returns:
            The setting value or default
        """
        # Handle nested keys with dot notation (e.g., 'note_types.Example-Based.deck')
        if '.' in key:
            parts = key.split('.')
            value = self.settings
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
                    
            return value
        else:
            return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """
        Set a specific setting value and save.
        
        Args:
            key: The setting key to set
            value: The value to set
            
        Returns:
            True if successful, False otherwise
        """
        # Handle nested keys with dot notation
        if '.' in key:
            parts = key.split('.')
            target = self.settings
            
            # Navigate to the containing object
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
                
            # Set the value
            last_key = parts[-1]
            old_value = target.get(last_key)
            target[last_key] = value
            
            changed = old_value != value
        else:
            old_value = self.settings.get(key)
            self.settings[key] = value
            changed = old_value != value
        
        # Save settings
        success = self.save_settings()
        
        # Notify of change if value actually changed
        if success and changed:
            if self.event_bus:
                self.event_bus.publish('settings:updated', {
                    'changed_settings': {key: value}
                })
            
            self._notify_setting_change(key, value)
            
        return success
    
    def get_template_replacements(self) -> Dict[str, str]:
        """
        Get settings in a format suitable for template replacement in prompts.
        
        Returns:
            Dictionary of template variables and their values
        """
        # Convert keys to the [KEY] format expected by the prompts
        replacements = {}
        
        # Map our settings to the template format
        replacements['TARGET_LANGUAGE'] = self.settings.get('target_language', 'Czech')
        replacements['SOURCE_LANGUAGE'] = self.settings.get('source_language', 'English')
        replacements['BASE_LANGUAGE'] = self.settings.get('source_language', 'English')
        replacements['DEFINITION_LANGUAGE'] = self.settings.get('definition_language', 'English')
        
        return replacements
    
    def add_recent_lookup(
        self, 
        headword: str, 
        target_lang: str, 
        definition_lang: str
    ) -> List[Dict[str, str]]:
        """
        Add a word to the recent lookups list, maintaining max 5 items.
        
        Args:
            headword: The word that was looked up
            target_lang: The target language
            definition_lang: The definition language
            
        Returns:
            Updated list of recent lookups
        """
        # Get current recent lookups
        recent_lookups = self.settings.get('recent_lookups', [])
        
        # Create lookup entry
        lookup_entry = {
            'headword': headword,
            'target_language': target_lang,
            'definition_language': definition_lang,
            'timestamp': datetime.now().isoformat()
        }
        
        # Remove this entry if it already exists (to avoid duplicates)
        recent_lookups = [
            entry for entry in recent_lookups 
            if not (
                entry.get('headword') == headword and 
                entry.get('target_language') == target_lang and
                entry.get('definition_language') == definition_lang
            )
        ]
        
        # Add the new entry at the beginning of the list
        recent_lookups.insert(0, lookup_entry)
        
        # Keep only the most recent lookups (configurable max)
        max_recent = self.settings.get('max_recent_items', 5)
        recent_lookups = recent_lookups[:max_recent]
        
        # Update settings and save to file
        self.settings['recent_lookups'] = recent_lookups
        self.save_settings()
        
        # Notify of change
        if self.event_bus:
            self.event_bus.publish('recent_lookups:updated', {
                'recent_lookups': recent_lookups
            })
        
        return recent_lookups
    
    def get_recent_lookups(self) -> List[Dict[str, str]]:
        """
        Get the list of recent lookups.
        
        Returns:
            List of recent lookup entries
        """
        return self.settings.get('recent_lookups', [])
    
    def clear_recent_lookups(self) -> bool:
        """
        Clear the recent lookups list.
        
        Returns:
            True if successful, False otherwise
        """
        self.settings['recent_lookups'] = []
        success = self.save_settings()
        
        if success and self.event_bus:
            self.event_bus.publish('recent_lookups:cleared', {})
            
        return success
    
    def add_custom_language(self, language_name: str) -> bool:
        """
        Add a custom language to the user's available languages.
        
        Args:
            language_name: The language name to add
            
        Returns:
            True if successful, False otherwise
        """
        # Get current custom languages
        custom_languages = self.settings.get('custom_languages', [])
        
        # Check if language already exists
        if language_name in custom_languages:
            return True
            
        # Add the language
        custom_languages.append(language_name)
        self.settings['custom_languages'] = custom_languages
        
        # Save settings
        success = self.save_settings()
        
        if success and self.event_bus:
            self.event_bus.publish('custom_languages:updated', {
                'custom_languages': custom_languages
            })
            
        return success
    
    def get_custom_languages(self) -> List[str]:
        """
        Get the list of custom languages.
        
        Returns:
            List of custom language names
        """
        return self.settings.get('custom_languages', [])
    
    def register_change_callback(self, setting_key: str, callback: Callable) -> None:
        """
        Register a callback for changes to a specific setting.
        
        Args:
            setting_key: The setting to monitor for changes
            callback: Function to call when the setting changes
        """
        if setting_key not in self.change_callbacks:
            self.change_callbacks[setting_key] = []
            
        if callback not in self.change_callbacks[setting_key]:
            self.change_callbacks[setting_key].append(callback)
    
    def unregister_change_callback(self, setting_key: str, callback: Callable) -> bool:
        """
        Unregister a setting change callback.
        
        Args:
            setting_key: The setting key
            callback: The callback to remove
            
        Returns:
            True if the callback was removed, False otherwise
        """
        if setting_key in self.change_callbacks and callback in self.change_callbacks[setting_key]:
            self.change_callbacks[setting_key].remove(callback)
            return True
        return False
    
    def _notify_setting_change(self, key: str, value: Any) -> None:
        """
        Notify registered callbacks about a setting change.
        
        Args:
            key: The setting that changed
            value: The new value
        """
        # Call registered callbacks for this setting
        if key in self.change_callbacks:
            for callback in self.change_callbacks[key]:
                try:
                    callback(value)
                except Exception as e:
                    if self.event_bus:
                        self.event_bus.publish('error:callback', {
                            'message': f"Error in setting change callback: {str(e)}",
                            'setting': key
                        })