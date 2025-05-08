"""
Anki Model

This module provides a model for Anki flashcard integration, handling the 
communication with Anki Connect and managing note creation and synchronization.
"""

import json
import urllib.request
import time
from typing import Dict, List, Any, Optional, Union, Tuple

from ..utils.type_definitions import DictionaryEntry, AnkiFieldMapping

class AnkiModel:
    """
    Model for Anki flashcard integration.
    
    This class encapsulates all Anki-related operations, providing a clean
    interface for creating and managing flashcards based on dictionary entries.
    
    Attributes:
        anki_url: URL for AnkiConnect API
        event_bus: Event system for model-related notifications
        connection_status: Current connection status with Anki
    """
    
    def __init__(self, anki_service=None, event_bus=None):
        """
        Initialize the Anki model.
        
        Args:
            anki_service: The Anki service for interacting with Anki
            event_bus: Optional event bus for notifications
        """
        self.anki_service = anki_service
        self.event_bus = event_bus
        self.last_error = None
    
    def test_connection(self) -> bool:
        """
        Test the connection to Anki.
        
        Returns:
            True if connected, False otherwise
        """
        if not self.anki_service:
            if self.event_bus:
                self.event_bus.publish('error:anki', {
                    'message': "Anki service not initialized"
                })
            return False
            
        # Use the AnkiService to test the connection
        return self.anki_service.refresh_connection_status()
    
    def get_decks(self) -> List[str]:
        """
        Get list of available Anki decks.
        
        Returns:
            List of deck names or empty list if failed
        """
        if not self.anki_service:
            if self.event_bus:
                self.event_bus.publish('error:anki', {
                    'message': "Anki service not initialized"
                })
            return []
            
        # Use the AnkiService to get the decks
        return self.anki_service.list_decks()
    
    def get_note_types(self) -> List[str]:
        """
        Get list of available Anki note types.
        
        Returns:
            List of note type names or empty list if failed
        """
        try:
            result = self._invoke('modelNames', {})
            if isinstance(result, list):
                return result
            else:
                if self.event_bus:
                    self.event_bus.publish('error:anki', {
                        'message': "Invalid response when requesting note types"
                    })
                return []
                
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:anki', {
                    'message': f"Failed to get note types: {str(e)}"
                })
            return []
    
    def get_field_names(self, note_type: str) -> List[str]:
        """
        Get field names for a specific note type.
        
        Args:
            note_type: The note type to get fields for
            
        Returns:
            List of field names or empty list if failed
        """
        try:
            result = self._invoke('modelFieldNames', {
                'modelName': note_type
            })
            
            if isinstance(result, list):
                return result
            else:
                if self.event_bus:
                    self.event_bus.publish('error:anki', {
                        'message': f"Invalid response when requesting field names for {note_type}"
                    })
                return []
                
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:anki', {
                    'message': f"Failed to get field names for {note_type}: {str(e)}"
                })
            return []
    
    def create_note(
        self, 
        entry: DictionaryEntry,
        deck_name: str,
        note_type: str,
        field_mappings: Dict[str, str],
        tags: List[str] = None,
        allow_duplicates: bool = False
    ) -> Union[int, bool]:
        """
        Create a new Anki note from a dictionary entry.
        
        Args:
            entry: The dictionary entry to create a note from
            deck_name: Name of the Anki deck to add the note to
            note_type: Type of Anki note to create
            field_mappings: Mapping of Anki fields to entry data paths
            tags: List of tags to add to the note
            allow_duplicates: Whether to allow duplicate notes
            
        Returns:
            Note ID if successful, False otherwise
        """
        try:
            # Map fields from entry to Anki fields
            fields = self._map_entry_to_fields(entry, field_mappings)
            
            # Prepare the note
            note = {
                'deckName': deck_name,
                'modelName': note_type,
                'fields': fields,
                'tags': tags or []
            }
            
            # Check for duplicates if needed
            if not allow_duplicates:
                is_duplicate = self._check_duplicate(note)
                if is_duplicate:
                    if self.event_bus:
                        self.event_bus.publish('anki:duplicate', {
                            'headword': entry.get('headword', ''),
                            'deck': deck_name
                        })
                    return False
            
            # Add the note
            result = self._invoke('addNote', {
                'note': note
            })
            
            if isinstance(result, int):
                # Notify of success if event bus exists
                if self.event_bus:
                    self.event_bus.publish('anki:note_added', {
                        'note_id': result,
                        'headword': entry.get('headword', ''),
                        'deck': deck_name
                    })
                    
                return result
            else:
                if self.event_bus:
                    self.event_bus.publish('error:anki', {
                        'message': f"Failed to add note for {entry.get('headword', '')}"
                    })
                return False
                
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:anki', {
                    'message': f"Error creating Anki note: {str(e)}"
                })
            return False
    
    def create_note_from_example(
        self,
        entry: DictionaryEntry,
        meaning_index: int,
        example_index: int,
        deck_name: str,
        note_type: str,
        field_mappings: Dict[str, str],
        tags: List[str] = None,
        allow_duplicates: bool = False
    ) -> Union[int, bool]:
        """
        Create a new Anki note from a specific example in a dictionary entry.
        
        Args:
            entry: The dictionary entry
            meaning_index: Index of the meaning to use
            example_index: Index of the example to use
            deck_name: Name of the Anki deck
            note_type: Type of Anki note
            field_mappings: Mapping of Anki fields to entry data paths
            tags: List of tags to add to the note
            allow_duplicates: Whether to allow duplicate notes
            
        Returns:
            Note ID if successful, False otherwise
        """
        try:
            # Extract the focused meaning and example
            meanings = entry.get('meanings', [])
            if meaning_index < 0 or meaning_index >= len(meanings):
                if self.event_bus:
                    self.event_bus.publish('error:anki', {
                        'message': f"Invalid meaning index: {meaning_index}"
                    })
                return False
                
            meaning = meanings[meaning_index]
            
            examples = meaning.get('examples', [])
            if example_index < 0 or example_index >= len(examples):
                if self.event_bus:
                    self.event_bus.publish('error:anki', {
                        'message': f"Invalid example index: {example_index}"
                    })
                return False
                
            example = examples[example_index]
            
            # Create enriched entry with selected meaning and example
            enriched_entry = entry.copy()
            enriched_entry['selected_meaning'] = meaning
            enriched_entry['selected_example'] = example
            
            # Now create the note with the enriched entry
            return self.create_note(
                enriched_entry,
                deck_name,
                note_type,
                field_mappings,
                tags,
                allow_duplicates
            )
            
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:anki', {
                    'message': f"Error creating Anki note from example: {str(e)}"
                })
            return False
    
    def _map_entry_to_fields(
        self, 
        entry: DictionaryEntry, 
        field_mappings: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Map dictionary entry data to Anki note fields.
        
        Args:
            entry: The dictionary entry
            field_mappings: Mapping of Anki fields to entry data paths
            
        Returns:
            Dictionary of Anki field name to field value
        """
        fields = {}
        
        for field_name, entry_path in field_mappings.items():
            # Get the value from the entry
            value = self._get_value_from_path(entry, entry_path)
            
            # Convert to string
            if value is None:
                value = ''
            elif not isinstance(value, str):
                value = str(value)
                
            fields[field_name] = value
            
        return fields
    
    def _get_value_from_path(self, data: Dict, path: str) -> Any:
        """
        Get a value from a nested dictionary using a dot-notation path.
        
        Args:
            data: The dictionary to extract from
            path: Path to the value (e.g. 'meanings.0.definition')
            
        Returns:
            The value at the path or None if not found
        """
        # Handle special case for array index notation
        if '.' in path:
            parts = path.split('.')
            current = data
            
            for part in parts:
                # Check if part is an array index
                if part.isdigit():
                    index = int(part)
                    if isinstance(current, list) and 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                else:
                    # Regular dictionary access
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return None
                        
            return current
        else:
            # Simple top-level key
            return data.get(path)
    
    def _check_duplicate(self, note: Dict[str, Any]) -> bool:
        """
        Check if a note would be a duplicate in Anki.
        
        Args:
            note: The note to check
            
        Returns:
            True if a duplicate exists, False otherwise
        """
        try:
            result = self._invoke('findNotes', {
                'query': f'deck:"{note["deckName"]}" '
            })
            
            # If no notes found, definitely not a duplicate
            if not result:
                return False
                
            # Get note info for all notes in the deck
            notes_info = self._invoke('notesInfo', {
                'notes': result
            })
            
            # Check each note
            if isinstance(notes_info, list):
                for existing_note in notes_info:
                    # Check if this note has the same content in the first field
                    # This is a simplistic duplicate check - could be improved
                    existing_fields = existing_note.get('fields', {})
                    for field_name, field_value in note['fields'].items():
                        if field_name in existing_fields:
                            existing_value = existing_fields[field_name].get('value', '')
                            if field_value == existing_value:
                                return True
                                
            return False
            
        except Exception as e:
            # Log error but don't fail - assume it's not a duplicate
            if self.event_bus:
                self.event_bus.publish('error:anki', {
                    'message': f"Error checking for duplicate note: {str(e)}"
                })
            return False
    
    def _invoke(self, action: str, params: Dict[str, Any]) -> Any:
        """
        Invoke an AnkiConnect API action.
        
        Args:
            action: The AnkiConnect action to invoke
            params: Parameters for the action
            
        Returns:
            The action result or raises an exception on error
        """
        request_data = json.dumps({
            'action': action,
            'params': params,
            'version': 6
        }).encode('utf-8')
        
        request = urllib.request.Request(
            self.anki_url,
            request_data,
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            response = urllib.request.urlopen(request, timeout=self.timeout)
            response_data = json.loads(response.read().decode('utf-8'))
            
            if response_data['error'] is not None:
                raise Exception(response_data['error'])
                
            return response_data['result']
            
        except urllib.error.URLError as e:
            raise Exception(f"Could not connect to Anki. Make sure Anki is running with AnkiConnect addon installed. Error: {str(e)}")
            
        except json.JSONDecodeError:
            raise Exception("Invalid response from Anki")
            
        except Exception as e:
            raise Exception(f"Error communicating with Anki: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current Anki connection status.
        
        Returns:
            Dictionary with status information
        """
        status = {
            'connected': self.connection_status == 'connected',
            'status': self.connection_status,
            'last_error': self.last_error
        }
        
        # Add version info if connected
        if self.connection_status == 'connected':
            try:
                version = self._invoke('version', {})
                status['version'] = version
            except:
                pass
                
        return status