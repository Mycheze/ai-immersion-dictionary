"""
Tests for the AnkiModel class.

This module contains tests for the AnkiModel which provides Anki flashcard integration.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from src.models.anki_model import AnkiModel

class TestAnkiModel:
    """Tests for the AnkiModel class."""
    
    @pytest.fixture
    def anki_model(self, event_bus):
        """Create an AnkiModel instance with mock event bus."""
        return AnkiModel(event_bus=event_bus)
    
    @pytest.fixture
    def sample_entry(self):
        """Create a sample dictionary entry for testing."""
        return {
            "headword": "jablko",
            "part_of_speech": "noun",
            "metadata": {
                "source_language": "English",
                "target_language": "Czech",
                "definition_language": "English"
            },
            "meanings": [
                {
                    "definition": "a round fruit with red, yellow, or green skin and firm white flesh",
                    "examples": [
                        {
                            "sentence": "Jedno jablko denně.",
                            "translation": "An apple a day."
                        },
                        {
                            "sentence": "Koupil jsem červené jablko.",
                            "translation": "I bought a red apple."
                        }
                    ]
                },
                {
                    "definition": "the tree which bears apples",
                    "examples": [
                        {
                            "sentence": "Zasadil jsem jablko na zahradě.",
                            "translation": "I planted an apple tree in the garden."
                        }
                    ]
                }
            ]
        }
    
    def test_init(self, anki_model):
        """Test the initialization of the AnkiModel."""
        assert anki_model.anki_url == 'http://localhost:8765'
        assert anki_model.connection_status == 'disconnected'
        assert anki_model.last_error is None
    
    @patch('urllib.request.urlopen')
    def test_test_connection_success(self, mock_urlopen, anki_model, event_bus):
        """Test successful connection to Anki."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"result": 6, "error": None}).encode('utf-8')
        mock_urlopen.return_value = mock_response
        
        # Setup event spy
        connect_spy = MagicMock()
        event_bus.subscribe('anki:connected', connect_spy)
        
        # Test connection
        result = anki_model.test_connection()
        
        # Verify results
        assert result is True
        assert anki_model.connection_status == 'connected'
        
        # Verify event was published
        assert connect_spy.called
        call_args = connect_spy.call_args[0][0]
        assert call_args['version'] == 6
    
    @patch('urllib.request.urlopen')
    def test_test_connection_error(self, mock_urlopen, anki_model, event_bus):
        """Test connection error handling."""
        # Setup mock response to raise an exception
        mock_urlopen.side_effect = Exception("Test connection error")
        
        # Setup error spy
        error_spy = MagicMock()
        event_bus.subscribe('error:anki', error_spy)
        
        # Test connection
        result = anki_model.test_connection()
        
        # Verify results
        assert result is False
        assert anki_model.connection_status == 'error'
        assert anki_model.last_error == "Test connection error"
        
        # Verify error event was published
        assert error_spy.called
        call_args = error_spy.call_args[0][0]
        assert "Test connection error" in call_args['message']
    
    @patch('urllib.request.urlopen')
    def test_get_decks(self, mock_urlopen, anki_model):
        """Test retrieving list of Anki decks."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "result": ["Default", "Czech", "Spanish"],
            "error": None
        }).encode('utf-8')
        mock_urlopen.return_value = mock_response
        
        # Get decks
        decks = anki_model.get_decks()
        
        # Verify results
        assert len(decks) == 3
        assert "Czech" in decks
        assert "Spanish" in decks
    
    @patch('urllib.request.urlopen')
    def test_get_note_types(self, mock_urlopen, anki_model):
        """Test retrieving list of Anki note types."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "result": ["Basic", "Cloze", "Language-Learning"],
            "error": None
        }).encode('utf-8')
        mock_urlopen.return_value = mock_response
        
        # Get note types
        note_types = anki_model.get_note_types()
        
        # Verify results
        assert len(note_types) == 3
        assert "Basic" in note_types
        assert "Language-Learning" in note_types
    
    @patch('urllib.request.urlopen')
    def test_get_field_names(self, mock_urlopen, anki_model):
        """Test retrieving field names for a note type."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "result": ["Front", "Back", "Examples", "Tags"],
            "error": None
        }).encode('utf-8')
        mock_urlopen.return_value = mock_response
        
        # Get field names
        fields = anki_model.get_field_names("Basic")
        
        # Verify results
        assert len(fields) == 4
        assert "Front" in fields
        assert "Back" in fields
        assert "Examples" in fields
    
    def test_get_value_from_path(self, anki_model, sample_entry):
        """Test extracting values from nested dictionaries using path notation."""
        # Test simple top-level key
        headword = anki_model._get_value_from_path(sample_entry, "headword")
        assert headword == "jablko"
        
        # Test nested key
        target_lang = anki_model._get_value_from_path(sample_entry, "metadata.target_language")
        assert target_lang == "Czech"
        
        # Test array index
        first_definition = anki_model._get_value_from_path(sample_entry, "meanings.0.definition")
        assert "round fruit" in first_definition
        
        # Test deeper nesting with array indices
        first_example = anki_model._get_value_from_path(sample_entry, "meanings.0.examples.0.sentence")
        assert first_example == "Jedno jablko denně."
        
        # Test non-existent path
        nonexistent = anki_model._get_value_from_path(sample_entry, "nonexistent.path")
        assert nonexistent is None
        
        # Test invalid array index
        invalid_index = anki_model._get_value_from_path(sample_entry, "meanings.99.definition")
        assert invalid_index is None
    
    def test_map_entry_to_fields(self, anki_model, sample_entry):
        """Test mapping dictionary entry data to Anki fields."""
        # Define field mappings
        field_mappings = {
            "Word": "headword",
            "Definition": "meanings.0.definition",
            "Example": "meanings.0.examples.0.sentence",
            "Translation": "meanings.0.examples.0.translation",
            "Language": "metadata.target_language",
            "PartOfSpeech": "part_of_speech"
        }
        
        # Map entry to fields
        fields = anki_model._map_entry_to_fields(sample_entry, field_mappings)
        
        # Verify mapping
        assert fields["Word"] == "jablko"
        assert "round fruit" in fields["Definition"]
        assert fields["Example"] == "Jedno jablko denně."
        assert fields["Translation"] == "An apple a day."
        assert fields["Language"] == "Czech"
        assert fields["PartOfSpeech"] == "noun"
        
        # Test nonexistent mapping (should return empty string)
        field_mappings["NonExistent"] = "nonexistent.path"
        fields = anki_model._map_entry_to_fields(sample_entry, field_mappings)
        assert fields["NonExistent"] == ""
    
    @patch.object(AnkiModel, '_invoke')
    def test_create_note(self, mock_invoke, anki_model, sample_entry, event_bus):
        """Test creating a new Anki note from a dictionary entry."""
        # Setup mock response
        mock_invoke.return_value = 12345  # Note ID
        
        # Setup event spy
        note_added_spy = MagicMock()
        event_bus.subscribe('anki:note_added', note_added_spy)
        
        # Define field mappings
        field_mappings = {
            "Word": "headword",
            "Definition": "meanings.0.definition",
            "Example": "meanings.0.examples.0.sentence",
            "Translation": "meanings.0.examples.0.translation"
        }
        
        # Create note
        result = anki_model.create_note(
            sample_entry,
            "Czech Vocabulary",
            "Basic",
            field_mappings,
            tags=["dictionary", "Czech"]
        )
        
        # Verify result
        assert result == 12345
        
        # Verify addNote was called with correct parameters
        mock_invoke.assert_called_with('addNote', {
            'note': {
                'deckName': "Czech Vocabulary",
                'modelName': "Basic",
                'fields': {
                    "Word": "jablko",
                    "Definition": "a round fruit with red, yellow, or green skin and firm white flesh",
                    "Example": "Jedno jablko denně.",
                    "Translation": "An apple a day."
                },
                'tags': ["dictionary", "Czech"]
            }
        })
        
        # Verify event was published
        assert note_added_spy.called
        call_args = note_added_spy.call_args[0][0]
        assert call_args['note_id'] == 12345
        assert call_args['headword'] == "jablko"
        assert call_args['deck'] == "Czech Vocabulary"
    
    @patch.object(AnkiModel, '_check_duplicate')
    @patch.object(AnkiModel, '_invoke')
    def test_create_note_duplicate(self, mock_invoke, mock_check_duplicate, anki_model, sample_entry, event_bus):
        """Test handling duplicate notes."""
        # Setup mock responses
        mock_check_duplicate.return_value = True
        
        # Setup event spy
        duplicate_spy = MagicMock()
        event_bus.subscribe('anki:duplicate', duplicate_spy)
        
        # Define field mappings
        field_mappings = {
            "Word": "headword",
            "Definition": "meanings.0.definition"
        }
        
        # Try to create a duplicate note
        result = anki_model.create_note(
            sample_entry,
            "Czech Vocabulary",
            "Basic",
            field_mappings
        )
        
        # Verify result
        assert result is False
        
        # Verify addNote was not called
        mock_invoke.assert_not_called()
        
        # Verify duplicate event was published
        assert duplicate_spy.called
        call_args = duplicate_spy.call_args[0][0]
        assert call_args['headword'] == "jablko"
    
    @patch.object(AnkiModel, 'create_note')
    def test_create_note_from_example(self, mock_create_note, anki_model, sample_entry):
        """Test creating a note from a specific example in an entry."""
        # Setup mock response
        mock_create_note.return_value = 67890
        
        # Define field mappings
        field_mappings = {
            "Word": "headword",
            "Definition": "selected_meaning.definition",
            "Example": "selected_example.sentence",
            "Translation": "selected_example.translation"
        }
        
        # Create note from a specific example
        result = anki_model.create_note_from_example(
            sample_entry,
            meaning_index=0,
            example_index=1,  # Second example in first meaning
            deck_name="Czech Vocabulary",
            note_type="Basic",
            field_mappings=field_mappings
        )
        
        # Verify result
        assert result == 67890
        
        # Verify create_note was called with enriched entry
        call_args = mock_create_note.call_args[0]
        enriched_entry = call_args[0]
        
        # Check that the entry contains the selected meaning and example
        assert enriched_entry['headword'] == "jablko"
        assert "round fruit" in enriched_entry['selected_meaning']['definition']
        assert enriched_entry['selected_example']['sentence'] == "Koupil jsem červené jablko."
        assert enriched_entry['selected_example']['translation'] == "I bought a red apple."
    
    @patch.object(AnkiModel, 'create_note')
    def test_create_note_from_example_invalid_indices(self, mock_create_note, anki_model, sample_entry, event_bus):
        """Test error handling with invalid meaning or example indices."""
        # Setup error spy
        error_spy = MagicMock()
        event_bus.subscribe('error:anki', error_spy)
        
        # Test invalid meaning index
        result = anki_model.create_note_from_example(
            sample_entry,
            meaning_index=99,  # Invalid index
            example_index=0,
            deck_name="Czech Vocabulary",
            note_type="Basic",
            field_mappings={}
        )
        
        # Verify result
        assert result is False
        
        # Verify create_note was not called
        mock_create_note.assert_not_called()
        
        # Verify error was published
        assert error_spy.called
        call_args = error_spy.call_args[0][0]
        assert "Invalid meaning index" in call_args['message']
        
        # Reset mocks
        error_spy.reset_mock()
        
        # Test invalid example index
        result = anki_model.create_note_from_example(
            sample_entry,
            meaning_index=0,
            example_index=99,  # Invalid index
            deck_name="Czech Vocabulary",
            note_type="Basic",
            field_mappings={}
        )
        
        # Verify result
        assert result is False
        
        # Verify error was published
        assert error_spy.called
        call_args = error_spy.call_args[0][0]
        assert "Invalid example index" in call_args['message']
    
    def test_get_status(self, anki_model):
        """Test getting Anki connection status."""
        # Test disconnected status
        status = anki_model.get_status()
        assert status['connected'] is False
        assert status['status'] == 'disconnected'
        
        # Test error status
        anki_model.connection_status = 'error'
        anki_model.last_error = "Test error message"
        
        status = anki_model.get_status()
        assert status['connected'] is False
        assert status['status'] == 'error'
        assert status['last_error'] == "Test error message"
        
        # Test connected status with version
        anki_model.connection_status = 'connected'
        
        with patch.object(anki_model, '_invoke', return_value=6):
            status = anki_model.get_status()
            assert status['connected'] is True
            assert status['status'] == 'connected'
            assert status['version'] == 6