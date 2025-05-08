"""
Tests for the UserModel class.

This module contains tests for the UserModel which handles user settings and preferences.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch

from src.models.user_model import UserModel

class TestUserModel:
    """Tests for the UserModel class."""
    
    def test_init_with_existing_settings(self, user_model, temp_settings_path):
        """Test initialization with existing settings file."""
        # The user_model fixture should already be initialized with a temporary settings file
        assert user_model.settings_file == temp_settings_path
        assert isinstance(user_model.settings, dict)
        
        # Write some settings to the file
        test_settings = {
            'target_language': 'Spanish',
            'source_language': 'German',
            'definition_language': 'German',
            'theme': 'dark'
        }
        
        with open(temp_settings_path, 'w', encoding='utf-8') as f:
            json.dump(test_settings, f)
        
        # Create a new model that should load these settings
        new_model = UserModel(settings_file=temp_settings_path)
        
        # Verify settings were loaded
        assert new_model.settings['target_language'] == 'Spanish'
        assert new_model.settings['source_language'] == 'German'
        assert new_model.settings['theme'] == 'dark'
    
    def test_get_default_settings(self, user_model):
        """Test retrieving default settings."""
        defaults = user_model.get_default_settings()
        
        # Check that required keys are present
        assert 'target_language' in defaults
        assert 'source_language' in defaults
        assert 'definition_language' in defaults
        assert 'text_scale_factor' in defaults
        assert 'theme' in defaults
        assert 'anki_enabled' in defaults
        
        # Check default values
        assert defaults['target_language'] == 'Czech'
        assert defaults['source_language'] == 'English'
        assert defaults['definition_language'] == 'English'
        assert defaults['theme'] == 'system'
        assert defaults['text_scale_factor'] == 1.0
    
    def test_save_settings(self, user_model, event_bus):
        """Test saving settings to file."""
        # Setup event spy
        event_spy = MagicMock()
        event_bus.subscribe('settings:saved', event_spy)
        
        # Modify a setting
        user_model.settings['theme'] = 'dark'
        
        # Save settings
        result = user_model.save_settings()
        assert result is True
        
        # Verify event was published
        assert event_spy.called
        call_args = event_spy.call_args[0][0]
        assert 'file' in call_args
        assert 'timestamp' in call_args
        
        # Verify file was actually written
        with open(user_model.settings_file, 'r', encoding='utf-8') as f:
            loaded_settings = json.load(f)
            assert loaded_settings['theme'] == 'dark'
    
    def test_save_settings_error(self, user_model, event_bus):
        """Test handling save errors."""
        # Setup error spy
        error_spy = MagicMock()
        event_bus.subscribe('error:settings', error_spy)
        
        # Create a mock that raises an exception when writing
        with patch('builtins.open', side_effect=IOError("Test write error")):
            result = user_model.save_settings()
            
            # Should return False on error
            assert result is False
            
            # Should publish error event
            assert error_spy.called
            call_args = error_spy.call_args[0][0]
            assert 'message' in call_args
            assert 'Test write error' in call_args['message']
    
    def test_get_settings(self, user_model):
        """Test retrieving complete settings."""
        # Modify settings
        user_model.settings['target_language'] = 'Spanish'
        
        # Get settings
        settings = user_model.get_settings()
        
        # Verify settings are returned correctly
        assert settings['target_language'] == 'Spanish'
        
        # Verify that a copy is returned (so original isn't modified)
        settings['target_language'] = 'Italian'
        assert user_model.settings['target_language'] == 'Spanish'
    
    def test_update_settings(self, user_model, event_bus):
        """Test updating multiple settings."""
        # Setup event spy
        event_spy = MagicMock()
        event_bus.subscribe('settings:updated', event_spy)
        
        # Update multiple settings
        new_settings = {
            'target_language': 'French',
            'theme': 'dark',
            'text_scale_factor': 1.2
        }
        
        result = user_model.update_settings(new_settings)
        assert result is True
        
        # Verify settings were updated
        assert user_model.settings['target_language'] == 'French'
        assert user_model.settings['theme'] == 'dark'
        assert user_model.settings['text_scale_factor'] == 1.2
        
        # Verify event was published
        assert event_spy.called
        call_args = event_spy.call_args[0][0]
        assert 'changed_settings' in call_args
        assert len(call_args['changed_settings']) == 3
    
    def test_language_consistency(self, user_model):
        """Test that definition_language follows source_language by default."""
        # Update source language only
        user_model.update_settings({'source_language': 'German'})
        
        # Definition language should be updated to match
        assert user_model.settings['definition_language'] == 'German'
        
        # Update definition language only
        user_model.update_settings({'definition_language': 'French'})
        
        # Source language should be updated to match
        assert user_model.settings['source_language'] == 'French'
    
    def test_get_setting(self, user_model):
        """Test retrieving a specific setting."""
        # Set up test settings
        user_model.settings['test_key'] = 'test_value'
        user_model.settings['nested'] = {
            'level1': {
                'level2': 'nested_value'
            }
        }
        
        # Test getting simple value
        assert user_model.get_setting('test_key') == 'test_value'
        
        # Test getting non-existent key with default
        assert user_model.get_setting('nonexistent', 'default') == 'default'
        
        # Test getting nested value with dot notation
        assert user_model.get_setting('nested.level1.level2') == 'nested_value'
        
        # Test getting non-existent nested key
        assert user_model.get_setting('nested.nonexistent', 'default') == 'default'
    
    def test_set_setting(self, user_model, event_bus):
        """Test setting a specific setting value."""
        # Setup event spy
        event_spy = MagicMock()
        event_bus.subscribe('settings:updated', event_spy)
        
        # Set a simple value
        result = user_model.set_setting('theme', 'dark')
        assert result is True
        assert user_model.settings['theme'] == 'dark'
        
        # Set a nested value
        result = user_model.set_setting('note_types.Example-Based.deck', 'My Custom Deck')
        assert result is True
        assert user_model.settings['note_types']['Example-Based']['deck'] == 'My Custom Deck'
        
        # Create a new nested path
        result = user_model.set_setting('new_category.subcategory.item', 'new_value')
        assert result is True
        assert user_model.settings['new_category']['subcategory']['item'] == 'new_value'
        
        # Verify events were published (3 times)
        assert event_spy.call_count == 3
    
    def test_get_template_replacements(self, user_model):
        """Test getting template replacements."""
        # Set up test settings
        user_model.settings['target_language'] = 'Spanish'
        user_model.settings['source_language'] = 'German'
        user_model.settings['definition_language'] = 'German'
        
        # Get template replacements
        replacements = user_model.get_template_replacements()
        
        # Check mapping
        assert replacements['TARGET_LANGUAGE'] == 'Spanish'
        assert replacements['SOURCE_LANGUAGE'] == 'German'
        assert replacements['BASE_LANGUAGE'] == 'German'
        assert replacements['DEFINITION_LANGUAGE'] == 'German'
    
    def test_recent_lookups(self, user_model, event_bus):
        """Test managing recent lookups."""
        # Setup event spy
        event_spy = MagicMock()
        event_bus.subscribe('recent_lookups:updated', event_spy)
        
        # Add a lookup
        lookups = user_model.add_recent_lookup('apple', 'Spanish', 'English')
        assert len(lookups) == 1
        assert lookups[0]['headword'] == 'apple'
        assert lookups[0]['target_language'] == 'Spanish'
        
        # Add several more lookups
        user_model.add_recent_lookup('banana', 'Spanish', 'English')
        user_model.add_recent_lookup('orange', 'Spanish', 'English')
        user_model.add_recent_lookup('grape', 'Spanish', 'English')
        user_model.add_recent_lookup('melon', 'Spanish', 'English')
        
        # Add one more to test max limit (default is 5)
        lookups = user_model.add_recent_lookup('pear', 'Spanish', 'English')
        
        # Should still have 5 items, with 'apple' removed (oldest)
        assert len(lookups) == 5
        assert 'apple' not in [item['headword'] for item in lookups]
        assert lookups[0]['headword'] == 'pear'  # Most recent first
        
        # Test getting recent lookups
        assert len(user_model.get_recent_lookups()) == 5
        
        # Test clearing recent lookups
        clear_spy = MagicMock()
        event_bus.subscribe('recent_lookups:cleared', clear_spy)
        
        result = user_model.clear_recent_lookups()
        assert result is True
        assert len(user_model.get_recent_lookups()) == 0
        assert clear_spy.called
    
    def test_custom_languages(self, user_model, event_bus):
        """Test managing custom languages."""
        # Setup event spy
        event_spy = MagicMock()
        event_bus.subscribe('custom_languages:updated', event_spy)
        
        # Add a custom language
        result = user_model.add_custom_language('Esperanto')
        assert result is True
        
        # Get custom languages
        languages = user_model.get_custom_languages()
        assert 'Esperanto' in languages
        
        # Add same language again (should not duplicate)
        result = user_model.add_custom_language('Esperanto')
        assert result is True
        languages = user_model.get_custom_languages()
        assert languages.count('Esperanto') == 1
        
        # Add another language
        result = user_model.add_custom_language('Klingon')
        assert result is True
        languages = user_model.get_custom_languages()
        assert 'Klingon' in languages
        assert len(languages) == 2
        
        # Verify event was published
        assert event_spy.call_count == 2  # Called twice for the two successful additions
    
    def test_change_callbacks(self, user_model):
        """Test setting change callbacks."""
        # Setup a callback
        callback_mock = MagicMock()
        user_model.register_change_callback('theme', callback_mock)
        
        # Change the setting
        user_model.set_setting('theme', 'dark')
        
        # Verify callback was called
        callback_mock.assert_called_once_with('dark')
        
        # Test unregistering callback
        result = user_model.unregister_change_callback('theme', callback_mock)
        assert result is True
        
        # Change setting again
        callback_mock.reset_mock()
        user_model.set_setting('theme', 'light')
        
        # Callback should not be called
        assert not callback_mock.called
    
    def test_multiple_callbacks(self, user_model, event_bus):
        """Test multiple callbacks for the same setting."""
        # Setup multiple callbacks
        callback1 = MagicMock()
        callback2 = MagicMock()
        
        user_model.register_change_callback('theme', callback1)
        user_model.register_change_callback('theme', callback2)
        
        # Setup error spy
        error_spy = MagicMock()
        event_bus.subscribe('error:callback', error_spy)
        
        # Create a failing callback
        def failing_callback(value):
            raise ValueError("Test callback error")
            
        user_model.register_change_callback('theme', failing_callback)
        
        # Change the setting
        user_model.set_setting('theme', 'dark')
        
        # Verify all callbacks were called
        callback1.assert_called_once_with('dark')
        callback2.assert_called_once_with('dark')
        
        # Verify error was published for failing callback
        assert error_spy.called
        call_args = error_spy.call_args[0][0]
        assert 'message' in call_args
        assert 'Test callback error' in call_args['message']