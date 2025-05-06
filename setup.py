#!/usr/bin/env python3
import os
import sys
import json
import getpass
import re
from pathlib import Path

def create_directory(dir_path):
    """Create directory if it doesn't exist."""
    try:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✓ Ensured directory exists: {dir_path}")
        return True
    except Exception as e:
        print(f"✗ Error creating directory {dir_path}: {str(e)}")
        return False

def save_api_key(api_key, filename="api_key.txt"):
    """Save API key to file."""
    try:
        with open(filename, 'w') as f:
            f.write(api_key.strip())
        
        # Set appropriate permissions (readable only by the user)
        os.chmod(filename, 0o600)
        print(f"✓ API key saved to {filename}")
        return True
    except Exception as e:
        print(f"✗ Error saving API key: {str(e)}")
        return False

def validate_api_key(api_key):
    """Basic validation to ensure API key isn't empty."""
    if not api_key or len(api_key.strip()) < 10:
        return False
    return True

def create_default_user_settings():
    """Create default user_settings.json if it doesn't exist."""
    settings_file = "user_settings.json"
    
    if os.path.exists(settings_file):
        print(f"✓ User settings file already exists: {settings_file}")
        return True
    
    default_settings = {
        'target_language': 'Czech',
        'source_language': 'English',
        'definition_language': 'English',
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
        'custom_languages': [],
        'removed_languages': []
    }
    
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, indent=2)
        print(f"✓ Created default user settings file: {settings_file}")
        return True
    except Exception as e:
        print(f"✗ Error creating user settings file: {str(e)}")
        return False

def test_dependencies():
    """Test if required dependencies are installed."""
    try:
        import openai
        import requests
        import tkinter
        try:
            import pyperclip
            print("✓ All dependencies are installed")
            return True
        except ImportError:
            print("⚠ pyperclip is not installed. Clipboard monitoring will not work.")
            return True
    except ImportError as e:
        missing_package = str(e).split("'")[1]
        print(f"✗ Missing dependency: {missing_package}")
        print("Please run: pip install -r requirements.txt")
        return False

def main():
    """Main setup function."""
    print("=" * 60)
    print("DeepDict Setup")
    print("=" * 60)
    
    # Create required directories
    dirs_to_create = ["data", "config"]
    dirs_created = all(create_directory(d) for d in dirs_to_create)
    
    if not dirs_created:
        print("Failed to create required directories. Setup cannot continue.")
        sys.exit(1)
    
    # Test dependencies
    if not test_dependencies():
        print("\nPlease install required dependencies and run setup again.")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)
    
    # API Key setup
    print("\nAPI Key Setup")
    print("-" * 60)
    print("You need a DeepSeek API key to use this application.")
    print("Visit: https://platform.deepseek.com/ to get your API key.")
    
    # Check if API key file exists already
    api_key_file = "api_key.txt"
    if os.path.exists(api_key_file):
        overwrite = input(f"API key file already exists. Overwrite? (y/n): ").lower() == 'y'
        if not overwrite:
            print("Keeping existing API key.")
        else:
            api_key = getpass.getpass("Enter your DeepSeek API key: ")
            
            if validate_api_key(api_key):
                save_api_key(api_key, api_key_file)
            else:
                print("Invalid API key format. Please enter a valid key.")
                sys.exit(1)
    else:
        api_key = getpass.getpass("Enter your DeepSeek API key: ")
        
        if validate_api_key(api_key):
            save_api_key(api_key, api_key_file)
        else:
            print("Invalid API key format. Please enter a valid key.")
            sys.exit(1)
    
    # Create default user settings if needed
    create_default_user_settings()
    
    print("\nSetup Complete")
    print("=" * 60)
    print("You can now run the application using:")
    print("  - On Linux/macOS: ./scripts/launch_dictionary.sh")
    print("  - On Windows: scripts\\launch_dictionary.bat")
    print("=" * 60)

if __name__ == "__main__":
    main()