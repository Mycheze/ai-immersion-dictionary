import os
import json

class UserSettings:
    """
    Manages persistent user settings for the dictionary application
    """
    
    def __init__(self, settings_file='user_settings.json'):
        """Initialize user settings manager"""
        self.settings_file = settings_file
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from file if it exists"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load settings file, using defaults. Error: {e}")
                return self.get_default_settings()
        else:
            return self.get_default_settings()
    
    def get_default_settings(self):
        """Return default settings"""
        return {
            'target_language': 'Czech',  # Language being learned
            'source_language': 'English',  # Base language of the learner
            'definition_language': 'English',  # Language for definitions
            
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
            'tags': ['AI-Dictionary']
        }
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            # Ensure directory exists if settings file is in a subdirectory
            settings_dir = os.path.dirname(self.settings_file)
            if settings_dir and not os.path.exists(settings_dir):
                os.makedirs(settings_dir, exist_ok=True)
                print(f"Created settings directory: {settings_dir}")
                
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {str(e)}")
            return False
    
    def get_settings(self):
        """Get the current settings"""
        return self.settings
    
    def update_settings(self, new_settings):
        """Update settings with new values"""
        self.settings.update(new_settings)
        self.save_settings()
    
    def get_setting(self, key, default=None):
        """Get a specific setting value"""
        return self.settings.get(key, default)
    
    def get_template_replacements(self):
        """Get settings in a format suitable for template replacement"""
        # Convert keys to the [KEY] format expected by the prompts
        replacements = {}
        
        # Map our settings to the template format
        replacements['TARGET_LANGUAGE'] = self.settings.get('target_language', 'Czech')
        replacements['SOURCE_LANGUAGE'] = self.settings.get('source_language', 'English')
        replacements['BASE_LANGUAGE'] = self.settings.get('source_language', 'English')  # Alias for SOURCE_LANGUAGE
        replacements['DEFINITION_LANGUAGE'] = self.settings.get('definition_language', 'English')
        
        return replacements