"""
Test configuration for DeepDict application tests.

This file contains pytest fixtures and configuration for running the test suite.
"""

import os
import sys
import pytest
from pathlib import Path

# Add the source directory to the path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

# Import application components for fixtures
from src.utils.event_bus import EventBus
from src.utils.error_handler import ErrorHandler
from src.models.user_model import UserModel
from src.models.dictionary_model import DictionaryModel
from src.services.request_service import RequestService

@pytest.fixture
def event_bus():
    """Fixture for creating a clean EventBus instance."""
    return EventBus()

@pytest.fixture
def error_handler(event_bus):
    """Fixture for creating an ErrorHandler instance."""
    return ErrorHandler(event_bus)

@pytest.fixture
def temp_db_path(tmpdir):
    """Fixture for creating a temporary database path."""
    return os.path.join(tmpdir, "test_db.sqlite")

@pytest.fixture
def temp_settings_path(tmpdir):
    """Fixture for creating a temporary settings file path."""
    return os.path.join(tmpdir, "test_settings.json")

@pytest.fixture
def mock_db_manager():
    """Fixture for creating a mock database manager."""
    class MockDatabaseManager:
        def __init__(self):
            self.entries = {}
            self.lemmas = {}
            self.languages = {
                'target_languages': ['Czech', 'Spanish', 'French'],
                'source_languages': ['English', 'German'],
                'definition_languages': ['English', 'German']
            }
            
        def get_entry_by_headword(self, headword, source_lang=None, target_lang=None, definition_lang=None):
            key = f"{headword}|{source_lang}|{target_lang}|{definition_lang}"
            return self.entries.get(key)
            
        def search_entries(self, search_term=None, source_lang=None, target_lang=None, definition_lang=None):
            results = []
            for key, entry in self.entries.items():
                headword = key.split('|')[0]
                if search_term and search_term.lower() not in headword.lower():
                    continue
                    
                entry_meta = entry.get('metadata', {})
                entry_target = entry_meta.get('target_language')
                entry_source = entry_meta.get('source_language')
                entry_def = entry_meta.get('definition_language')
                
                if target_lang and entry_target != target_lang:
                    continue
                    
                if source_lang and entry_source != source_lang:
                    continue
                    
                if definition_lang and entry_def != definition_lang:
                    continue
                    
                results.append(entry)
                
            return results
            
        def add_entry(self, entry):
            headword = entry.get('headword')
            metadata = entry.get('metadata', {})
            source_lang = metadata.get('source_language')
            target_lang = metadata.get('target_language')
            definition_lang = metadata.get('definition_language')
            
            key = f"{headword}|{source_lang}|{target_lang}|{definition_lang}"
            self.entries[key] = entry
            return len(self.entries)  # Simulate an ID
            
        def delete_entry(self, headword, source_lang=None, target_lang=None, definition_lang=None):
            key = f"{headword}|{source_lang}|{target_lang}|{definition_lang}"
            if key in self.entries:
                del self.entries[key]
                return True
            return False
            
        def get_all_languages(self):
            return self.languages
            
        def get_cached_lemma(self, word, target_language):
            key = f"{word}|{target_language}"
            return self.lemmas.get(key)
            
        def cache_lemma(self, word, lemma, target_language):
            key = f"{word}|{target_language}"
            self.lemmas[key] = lemma
            
    return MockDatabaseManager()

@pytest.fixture
def user_model(event_bus, temp_settings_path):
    """Fixture for creating a UserModel instance with temporary settings."""
    return UserModel(settings_file=temp_settings_path, event_bus=event_bus)

@pytest.fixture
def dictionary_model(event_bus, mock_db_manager):
    """Fixture for creating a DictionaryModel instance with mock database."""
    return DictionaryModel(mock_db_manager, event_bus=event_bus)

@pytest.fixture
def mock_dictionary_engine():
    """Fixture for creating a mock dictionary engine for the request service."""
    class MockDictionaryEngine:
        def __init__(self):
            self.responses = {
                'lemma': {},
                'entry': {},
                'regenerate': {},
                'validate_language': {}
            }
            
        def add_lemma_response(self, word, context, result):
            key = f"{word}|{context or ''}"
            self.responses['lemma'][key] = result
            
        def add_entry_response(self, word, target_lang, source_lang, context, result):
            key = f"{word}|{target_lang or ''}|{source_lang or ''}|{context or ''}"
            self.responses['entry'][key] = result
            
        def add_regenerate_response(self, headword, target_lang, source_lang, definition_lang, result):
            key = f"{headword}|{target_lang or ''}|{source_lang or ''}|{definition_lang or ''}"
            self.responses['regenerate'][key] = result
            
        def add_validate_language_response(self, language_name, result):
            self.responses['validate_language'][language_name] = result
            
        def get_lemma(self, word, sentence_context=None):
            key = f"{word}|{sentence_context or ''}"
            if key in self.responses['lemma']:
                return self.responses['lemma'][key]
            return word  # Default to returning the word itself
            
        def create_new_entry(self, word, target_lang=None, source_lang=None, sentence_context=None, variation_prompt=None):
            key = f"{word}|{target_lang or ''}|{source_lang or ''}|{sentence_context or ''}"
            if key in self.responses['entry']:
                return self.responses['entry'][key]
            
            # Create a basic entry if no specific response is defined
            return {
                "metadata": {
                    "source_language": source_lang or "English",
                    "target_language": target_lang or "Czech",
                    "definition_language": source_lang or "English"
                },
                "headword": word,
                "part_of_speech": "noun",
                "meanings": [
                    {
                        "definition": f"Test definition for {word}",
                        "examples": [
                            {
                                "sentence": f"Example sentence for {word}",
                                "translation": f"Translation of example for {word}"
                            }
                        ]
                    }
                ]
            }
            
        def regenerate_entry(self, headword, target_lang=None, source_lang=None, definition_lang=None, variation_seed=None):
            key = f"{headword}|{target_lang or ''}|{source_lang or ''}|{definition_lang or ''}"
            if key in self.responses['regenerate']:
                return self.responses['regenerate'][key]
                
            # Create a basic regenerated entry if no specific response is defined
            return {
                "metadata": {
                    "source_language": source_lang or "English",
                    "target_language": target_lang or "Czech",
                    "definition_language": definition_lang or "English"
                },
                "headword": headword,
                "part_of_speech": "noun",
                "meanings": [
                    {
                        "definition": f"Regenerated definition for {headword}",
                        "examples": [
                            {
                                "sentence": f"Regenerated example sentence for {headword}",
                                "translation": f"Regenerated translation of example for {headword}"
                            }
                        ]
                    }
                ]
            }
            
        def validate_language(self, language_name):
            if language_name in self.responses['validate_language']:
                return self.responses['validate_language'][language_name]
                
            # Create a basic validation result if no specific response is defined
            return {
                "standardized_name": language_name,
                "display_name": language_name
            }
            
    return MockDictionaryEngine()

@pytest.fixture
def request_service(event_bus, mock_dictionary_engine):
    """Fixture for creating a RequestService instance with mock dictionary engine."""
    return RequestService(dictionary_engine=mock_dictionary_engine, event_bus=event_bus)