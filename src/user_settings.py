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
        # Set default definition language
        default_definition_lang = 'English'
        
        return {
            'target_language': 'Czech',  # Language being learned
            'source_language': default_definition_lang,  # Base language of the learner (same as definition language)
            'definition_language': default_definition_lang,  # Language for definitions
            
            # UI settings
            'text_scale_factor': 1.0,  # Default scale factor for text (1.0 = 100%)
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
        # If definition_language is being updated, ensure source_language matches
        if 'definition_language' in new_settings and 'source_language' not in new_settings:
            new_settings['source_language'] = new_settings['definition_language']
        # If source_language is being updated, ensure definition_language matches
        elif 'source_language' in new_settings and 'definition_language' not in new_settings:
            new_settings['definition_language'] = new_settings['source_language']
            
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
    
    def add_recent_lookup(self, headword, target_lang, definition_lang):
        """Add a word to the recent lookups list, maintaining max 5 items"""
        # Get current recent lookups
        recent_lookups = self.settings.get('recent_lookups', [])
        
        # Create lookup entry with headword and language information
        lookup_entry = {
            'headword': headword,
            'target_language': target_lang,
            'definition_language': definition_lang
        }
        
        # Remove this entry if it already exists in the list (to avoid duplicates)
        recent_lookups = [entry for entry in recent_lookups 
                         if not (entry.get('headword') == headword and 
                                entry.get('target_language') == target_lang and
                                entry.get('definition_language') == definition_lang)]
        
        # Add the new entry at the beginning of the list
        recent_lookups.insert(0, lookup_entry)
        
        # Keep only the 5 most recent lookups
        recent_lookups = recent_lookups[:5]
        
        # Update settings and save to file
        self.settings['recent_lookups'] = recent_lookups
        self.save_settings()
        
        return recent_lookups
        
    def get_recent_lookups(self):
        """Get the list of recent lookups"""
        return self.settings.get('recent_lookups', [])