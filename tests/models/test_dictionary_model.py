"""
Tests for the DictionaryModel class.

This module contains tests for the DictionaryModel which handles
dictionary entry operations.
"""

import pytest
import json
from unittest.mock import MagicMock

from src.models.dictionary_model import DictionaryModel
from src.utils.type_definitions import DictionaryEntry

class TestDictionaryModel:
    """Tests for the DictionaryModel class."""
    
    def test_get_entry_by_headword(self, dictionary_model, mock_db_manager):
        """Test retrieving an entry by headword."""
        # Setup
        test_entry = {
            "headword": "test",
            "metadata": {
                "source_language": "English",
                "target_language": "Czech",
                "definition_language": "English"
            },
            "meanings": [
                {
                    "definition": "A test definition",
                    "examples": [
                        {
                            "sentence": "This is a test sentence.",
                            "translation": "To je testovací věta."
                        }
                    ]
                }
            ]
        }
        
        # Add the entry to the mock DB
        mock_db_manager.add_entry(test_entry)
        
        # Test
        result = dictionary_model.get_entry_by_headword("test", "Czech", "English", "English")
        
        # Verify
        assert result is not None
        assert result["headword"] == "test"
        assert result["metadata"]["target_language"] == "Czech"
        
        # Test with different parameters
        result2 = dictionary_model.get_entry_by_headword("test", "Spanish")
        assert result2 is None  # Should not find the entry with different parameters
    
    def test_search_entries(self, dictionary_model, mock_db_manager, event_bus):
        """Test searching for entries using filters."""
        # Setup
        event_spy = MagicMock()
        event_bus.subscribe('search:completed', event_spy)
        
        entries = [
            {
                "headword": "apple",
                "metadata": {
                    "source_language": "English",
                    "target_language": "Czech",
                    "definition_language": "English"
                },
                "meanings": [{"definition": "A fruit"}]
            },
            {
                "headword": "banana",
                "metadata": {
                    "source_language": "English",
                    "target_language": "Czech",
                    "definition_language": "English"
                },
                "meanings": [{"definition": "A yellow fruit"}]
            },
            {
                "headword": "orange",
                "metadata": {
                    "source_language": "English",
                    "target_language": "Spanish",
                    "definition_language": "English"
                },
                "meanings": [{"definition": "A citrus fruit"}]
            }
        ]
        
        # Add entries to the mock DB
        for entry in entries:
            mock_db_manager.add_entry(entry)
        
        # Test with no filters
        filters = {"search_term": ""}
        results = dictionary_model.search_entries(filters)
        assert len(results) == 3
        
        # Test with search term
        filters = {"search_term": "apple"}
        results = dictionary_model.search_entries(filters)
        assert len(results) == 1
        assert results[0]["headword"] == "apple"
        
        # Test with language filter
        filters = {
            "search_term": "",
            "target_language": "Czech"
        }
        results = dictionary_model.search_entries(filters)
        assert len(results) == 2
        
        # Verify event was published
        assert event_spy.called
        call_args = event_spy.call_args[0][0]
        assert call_args["search_term"] == ""
        assert call_args["count"] == 2
    
    def test_save_entry(self, dictionary_model, mock_db_manager, event_bus):
        """Test saving an entry."""
        # Setup
        event_spy = MagicMock()
        event_bus.subscribe('entry:saved', event_spy)
        
        # Test with valid entry
        entry = {
            "headword": "valid",
            "metadata": {
                "source_language": "English",
                "target_language": "French",
                "definition_language": "English"
            },
            "meanings": [
                {
                    "definition": "Valid entry definition",
                    "examples": []
                }
            ]
        }
        
        result = dictionary_model.save_entry(entry)
        assert result is not None
        assert result > 0
        
        # Test with invalid entry
        invalid_entry = {
            "headword": "invalid",
            # Missing required metadata
            "meanings": []  # No valid meanings
        }
        
        error_spy = MagicMock()
        event_bus.subscribe('error:validation', error_spy)
        
        result = dictionary_model.save_entry(invalid_entry)
        assert result is None
        assert error_spy.called
        
        # Verify save event was published
        assert event_spy.called
        call_args = event_spy.call_args[0][0]
        assert call_args["headword"] == "valid"
        assert call_args["target_language"] == "French"
    
    def test_delete_entry(self, dictionary_model, mock_db_manager, event_bus):
        """Test deleting an entry."""
        # Setup
        entry = {
            "headword": "delete_me",
            "metadata": {
                "source_language": "English",
                "target_language": "Czech",
                "definition_language": "English"
            },
            "meanings": [{"definition": "Entry to delete"}]
        }
        
        mock_db_manager.add_entry(entry)
        
        event_spy = MagicMock()
        event_bus.subscribe('entry:deleted', event_spy)
        
        # Test delete
        result = dictionary_model.delete_entry("delete_me", "Czech", "English", "English")
        assert result is True
        
        # Verify entry was deleted
        result = dictionary_model.get_entry_by_headword("delete_me", "Czech", "English", "English")
        assert result is None
        
        # Verify event was published
        assert event_spy.called
        call_args = event_spy.call_args[0][0]
        assert call_args["headword"] == "delete_me"
        
        # Test deleting non-existent entry
        result = dictionary_model.delete_entry("nonexistent")
        assert result is False
    
    def test_parse_entry_json(self, dictionary_model, event_bus):
        """Test parsing entry JSON."""
        # Setup
        error_spy = MagicMock()
        event_bus.subscribe('error:parsing', error_spy)
        
        # Test with valid JSON
        valid_json = json.dumps({
            "headword": "json_test",
            "metadata": {
                "source_language": "English",
                "target_language": "Czech",
                "definition_language": "English"
            },
            "meanings": [
                {
                    "definition": "A test of JSON parsing",
                    "examples": []
                }
            ]
        })
        
        result = dictionary_model.parse_entry_json(valid_json)
        assert result is not None
        assert result["headword"] == "json_test"
        
        # Test with invalid JSON
        invalid_json = "{ this is not valid JSON }"
        result = dictionary_model.parse_entry_json(invalid_json)
        assert result is None
        assert error_spy.called
        
        # Test with valid JSON but invalid entry structure
        valid_json_invalid_structure = json.dumps({
            "headword": "invalid_structure",
            # Missing required metadata
            "meanings": []
        })
        
        validation_spy = MagicMock()
        event_bus.subscribe('error:validation', validation_spy)
        
        result = dictionary_model.parse_entry_json(valid_json_invalid_structure)
        assert result is None
        assert validation_spy.called
    
    def test_format_entry_json(self, dictionary_model, event_bus):
        """Test formatting entry as JSON."""
        # Setup
        entry = {
            "headword": "format_test",
            "metadata": {
                "source_language": "English",
                "target_language": "Czech",
                "definition_language": "English"
            },
            "meanings": [
                {
                    "definition": "A test of JSON formatting",
                    "examples": []
                }
            ]
        }
        
        # Test JSON formatting
        result = dictionary_model.format_entry_json(entry)
        assert "format_test" in result
        assert "Czech" in result
        
        # Parse the result back to verify format
        parsed = json.loads(result)
        assert parsed["headword"] == "format_test"
        
        # Test with indent parameter
        result_indented = dictionary_model.format_entry_json(entry, indent=4)
        assert len(result_indented) > len(result)  # Should have more whitespace
    
    def test_cache_operations(self, dictionary_model, mock_db_manager):
        """Test entry caching operations."""
        # Setup
        test_entry = {
            "headword": "cache_test",
            "metadata": {
                "source_language": "English",
                "target_language": "Czech",
                "definition_language": "English"
            },
            "meanings": [{"definition": "A test entry for cache"}]
        }
        
        mock_db_manager.add_entry(test_entry)
        
        # First retrieval - should come from DB
        db_spy = MagicMock(wraps=mock_db_manager.get_entry_by_headword)
        mock_db_manager.get_entry_by_headword = db_spy
        
        result1 = dictionary_model.get_entry_by_headword("cache_test", "Czech", "English", "English")
        assert result1 is not None
        assert db_spy.called
        db_spy.reset_mock()
        
        # Second retrieval - should come from cache
        result2 = dictionary_model.get_entry_by_headword("cache_test", "Czech", "English", "English")
        assert result2 is not None
        assert not db_spy.called  # DB should not be called again
        
        # Clear cache
        dictionary_model.clear_cache()
        
        # After clearing, should hit DB again
        result3 = dictionary_model.get_entry_by_headword("cache_test", "Czech", "English", "English")
        assert result3 is not None
        assert db_spy.called
    
    def test_cache_eviction(self, dictionary_model, mock_db_manager):
        """Test LRU cache eviction."""
        # Override max cache size for testing
        dictionary_model.max_cache_size = 2
        
        # Create test entries
        entries = [
            {
                "headword": f"cache{i}",
                "metadata": {
                    "source_language": "English",
                    "target_language": "Czech",
                    "definition_language": "English"
                },
                "meanings": [{"definition": f"Cache test entry {i}"}]
            }
            for i in range(3)
        ]
        
        for entry in entries:
            mock_db_manager.add_entry(entry)
        
        # Access entries to populate cache
        for i in range(3):
            dictionary_model.get_entry_by_headword(f"cache{i}", "Czech", "English", "English")
        
        # Due to LRU policy, cache0 should be evicted, and only cache1 and cache2 remain
        assert dictionary_model._get_cache_key("cache0", "Czech", "English", "English") not in dictionary_model.cached_entries
        assert dictionary_model._get_cache_key("cache1", "Czech", "English", "English") in dictionary_model.cached_entries
        assert dictionary_model._get_cache_key("cache2", "Czech", "English", "English") in dictionary_model.cached_entries
        
        # Access cache1 again to update its position in LRU
        dictionary_model.get_entry_by_headword("cache1", "Czech", "English", "English")
        
        # Add another entry - cache2 should be evicted
        dictionary_model.get_entry_by_headword("cache0", "Czech", "English", "English")
        
        assert dictionary_model._get_cache_key("cache0", "Czech", "English", "English") in dictionary_model.cached_entries
        assert dictionary_model._get_cache_key("cache1", "Czech", "English", "English") in dictionary_model.cached_entries
        assert dictionary_model._get_cache_key("cache2", "Czech", "English", "English") not in dictionary_model.cached_entries
    
    def test_get_all_languages(self, dictionary_model, mock_db_manager):
        """Test retrieving all languages."""
        # The mock_db_manager fixture already has sample languages
        
        languages = dictionary_model.get_all_languages()
        
        assert "target_languages" in languages
        assert "source_languages" in languages
        assert "definition_languages" in languages
        
        assert "Czech" in languages["target_languages"]
        assert "English" in languages["source_languages"]