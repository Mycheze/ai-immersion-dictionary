#!/usr/bin/env python3
import os
import sys
import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

# Import the app
from app import DictionaryApp
from settings_dialog import SettingsDialog
from user_settings import UserSettings

class TextScalingTest(unittest.TestCase):
    """Test case for text scaling functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test case"""
        # Create a root window for testing
        cls.root = tk.Tk()
        cls.root.withdraw()  # Hide the window during tests
        
        # Mock user settings to avoid file operations
        with patch('user_settings.UserSettings.load_settings') as mock_load:
            mock_load.return_value = {
                'target_language': 'Test',
                'source_language': 'English',
                'definition_language': 'English',
                'text_scale_factor': 1.0,
            }
            # Mock database manager and dictionary engine
            with patch('app.DatabaseManager') as mock_db:
                with patch('app.DictionaryEngine') as mock_engine:
                    cls.app = DictionaryApp(cls.root)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        cls.root.destroy()
    
    def test_settings_dialog_creation(self):
        """Test that the settings dialog can be created"""
        dialog = SettingsDialog(self.root, UserSettings())
        self.assertIsNotNone(dialog)
        dialog.destroy()
    
    def test_text_scale_setting(self):
        """Test that text scale factor can be set and retrieved"""
        user_settings = UserSettings()
        
        # Test default value
        self.assertEqual(user_settings.get_setting('text_scale_factor', None), 1.0)
        
        # Test updating the value
        user_settings.update_settings({'text_scale_factor': 1.2})
        self.assertEqual(user_settings.get_setting('text_scale_factor', None), 1.2)
    
    def test_apply_text_scaling(self):
        """Test that apply_text_scaling method updates fonts correctly"""
        # Get initial font sizes
        initial_headword_font = self.app.entry_display.tag_cget("headword", "font")
        
        # Mock user settings to test scaling
        self.app.user_settings.get_setting = MagicMock(return_value=1.5)
        
        # Apply text scaling
        self.app.apply_text_scaling(1.5)
        
        # Check that font sizes have been updated
        new_headword_font = self.app.entry_display.tag_cget("headword", "font")
        self.assertNotEqual(initial_headword_font, new_headword_font)
        
        # Font should now be larger
        # Note: Font is a tuple or string depending on platform, so check individually
        if isinstance(new_headword_font, tuple):
            self.assertEqual(int(new_headword_font[1]), 24)  # 16 * 1.5 = 24
        else:
            self.assertIn("24", new_headword_font)  # Font size should be in the string

if __name__ == '__main__':
    unittest.main()