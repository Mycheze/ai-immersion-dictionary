"""
Anki Service

This module provides a service for interacting with Anki through the AnkiConnect addon.
The service handles connection management, field mapping, and note export.
"""

import json
import requests
import time
from typing import Dict, List, Any, Optional, Callable, Union
import uuid

from .base_service import BaseService

class AnkiService(BaseService):
    """
    Service for integrating with Anki.
    
    This service provides a clean interface for interacting with Anki through
    the AnkiConnect addon, handling connection management, field mapping,
    and note export.
    
    Attributes:
        url: The URL where AnkiConnect is running
        field_mapper: The field mapper for dictionary entries
        empty_field_handler: Handler for empty fields
        retry_attempts: Number of times to retry failed requests
        retry_delay: Delay between retry attempts in seconds
        event_bus: Event system for service-related notifications
    """
    
    def __init__(
        self, 
        url: str = "http://localhost:8765", 
        retry_attempts: int = 3, 
        retry_delay: float = 1.0,
        event_bus=None
    ):
        """
        Initialize the Anki service.
        
        Args:
            url: The URL where AnkiConnect is running
            retry_attempts: Number of times to retry failed requests
            retry_delay: Delay between retry attempts in seconds
            event_bus: Optional event bus for notifications
        """
        self.url = url
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.connection_status = False
        
        # Default empty field handling
        self.empty_field_handler = EmptyFieldHandler()
        
        # Call parent initializer
        super().__init__(event_bus)
    
    def _initialize(self):
        """Initialize the Anki service."""
        # Test connection on startup
        self.connection_status = self.test_connection()
        
        if self.connection_status:
            self.publish_event('anki:connected', {
                'url': self.url
            })
        else:
            self.publish_event('anki:connection_failed', {
                'url': self.url
            })
    
    def request(self, action: str, **params) -> Dict[str, Any]:
        """
        Send a request to the Anki Connect API with retry logic.
        
        Args:
            action: The action to perform
            **params: Additional parameters for the action
            
        Returns:
            The response from AnkiConnect
            
        Raises:
            ConnectionError: If the connection to AnkiConnect fails
            Exception: If the request fails or returns an error
        """
        request_data = {
            "action": action,
            "version": 6,
            "params": params
        }
        
        self.publish_event('anki:request_start', {
            'action': action,
            'params': params
        })
        
        # Retry logic
        attempt = 0
        last_error = None
        
        while attempt < self.retry_attempts:
            attempt += 1
            
            try:
                response = requests.post(self.url, json=request_data, timeout=10)
                
                # Update connection status on successful request
                self.connection_status = True
                
                response.raise_for_status()
                
                try:
                    result = response.json()
                except json.JSONDecodeError as e:
                    self.publish_event('anki:error', {
                        'action': action,
                        'error': f"Invalid JSON response: {str(e)}",
                        'response': response.text[:1000]  # Limit response text size
                    })
                    raise Exception(f"Invalid JSON response from AnkiConnect: {str(e)}")
                
                # AnkiConnect returns {"result": data, "error": null} on success
                if 'error' in result and result['error'] is not None:
                    self.publish_event('anki:error', {
                        'action': action,
                        'error': result['error']
                    })
                    raise Exception(f"AnkiConnect error: {result['error']}")
                    
                # Make sure result field exists
                if 'result' not in result:
                    self.publish_event('anki:error', {
                        'action': action,
                        'error': "Missing 'result' field in response",
                        'response': result
                    })
                    raise Exception(f"Unexpected response format from AnkiConnect: {result}")
                
                # Success
                self.publish_event('anki:request_success', {
                    'action': action,
                    'result': result['result']
                })
                
                return result
                
            except requests.exceptions.ConnectionError as e:
                last_error = e
                self.connection_status = False
                
                self.publish_event('anki:connection_error', {
                    'action': action,
                    'attempt': attempt,
                    'error': str(e),
                    'retry': attempt < self.retry_attempts
                })
                
            except requests.exceptions.RequestException as e:
                last_error = e
                
                self.publish_event('anki:request_error', {
                    'action': action,
                    'attempt': attempt,
                    'error': str(e),
                    'retry': attempt < self.retry_attempts
                })
                
            except Exception as e:
                last_error = e
                
                self.publish_event('anki:error', {
                    'action': action,
                    'attempt': attempt,
                    'error': str(e),
                    'retry': attempt < self.retry_attempts
                })
            
            # Wait before retrying
            if attempt < self.retry_attempts:
                time.sleep(self.retry_delay)
        
        # If we reach here, all attempts failed
        raise ConnectionError(f"Failed to connect to AnkiConnect at {self.url} after {self.retry_attempts} attempts: {str(last_error)}")
    
    def test_connection(self) -> bool:
        """
        Test the connection to AnkiConnect.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = requests.post(
                self.url, 
                json={"action": "version", "version": 6},
                timeout=5
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if 'result' in result:
                        self.publish_event('anki:version', {
                            'version': result['result']
                        })
                        return True
                except:
                    pass
                    
            return False
            
        except Exception as e:
            self.publish_event('anki:connection_error', {
                'action': 'test_connection',
                'error': str(e)
            })
            return False
    
    def get_connection_status(self) -> bool:
        """
        Get the current connection status.
        
        Returns:
            True if connected, False otherwise
        """
        return self.connection_status
    
    def refresh_connection_status(self) -> bool:
        """
        Refresh the connection status.
        
        Returns:
            True if connected, False otherwise
        """
        self.connection_status = self.test_connection()
        
        if self.connection_status:
            self.publish_event('anki:connected', {
                'url': self.url
            })
        else:
            self.publish_event('anki:connection_failed', {
                'url': self.url
            })
            
        return self.connection_status
    
    def list_decks(self) -> List[str]:
        """
        Get a list of all decks in Anki.
        
        Returns:
            List of deck names
            
        Raises:
            Exception: If the request fails
        """
        try:
            result = self.request("deckNames")
            return result.get('result', [])
        except Exception as e:
            self.publish_event('anki:error', {
                'action': 'list_decks',
                'error': str(e)
            })
            return []
    
    def list_note_types(self) -> List[str]:
        """
        Get a list of all note types (models) in Anki.
        
        Returns:
            List of note type names
            
        Raises:
            Exception: If the request fails
        """
        try:
            result = self.request("modelNames")
            return result.get('result', [])
        except Exception as e:
            self.publish_event('anki:error', {
                'action': 'list_note_types',
                'error': str(e)
            })
            return []
    
    def get_note_type_fields(self, note_type: str) -> List[str]:
        """
        Get a list of fields for a specific note type.
        
        Args:
            note_type: The name of the note type
            
        Returns:
            List of field names
            
        Raises:
            Exception: If the request fails
        """
        try:
            result = self.request("modelFieldNames", modelName=note_type)
            return result.get('result', [])
        except Exception as e:
            self.publish_event('anki:error', {
                'action': 'get_note_type_fields',
                'error': str(e),
                'note_type': note_type
            })
            return []
    
    def add_note(
        self, 
        deck_name: str, 
        model_name: str, 
        fields: Dict[str, str], 
        tags: List[str] = None
    ) -> Optional[int]:
        """
        Add a note to a deck.
        
        Args:
            deck_name: The name of the deck
            model_name: The name of the note type
            fields: The fields of the note (field_name -> value)
            tags: List of tags to apply to the note
            
        Returns:
            The ID of the created note, or None if creation failed
            
        Raises:
            Exception: If the request fails
        """
        if tags is None:
            tags = []
            
        note_data = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": fields,
            "options": {
                "allowDuplicate": False
            },
            "tags": tags
        }
        
        try:
            result = self.request("addNote", note=note_data)
            note_id = result.get('result')
            
            if note_id:
                self.publish_event('anki:note_added', {
                    'note_id': note_id,
                    'deck_name': deck_name,
                    'model_name': model_name
                })
                
            return note_id
            
        except Exception as e:
            self.publish_event('anki:error', {
                'action': 'add_note',
                'error': str(e),
                'deck_name': deck_name,
                'model_name': model_name
            })
            return None
    
    def configure_field_mapping(self, field_mappings: Dict[str, str], empty_field_handling: Dict[str, Dict[str, Any]] = None):
        """
        Configure field mapping for dictionary entries.
        
        Args:
            field_mappings: Mapping of Anki field names to dictionary entry paths
            empty_field_handling: Configuration for empty field handling
        """
        self.field_mapper = AnkiFieldMapper(field_mappings, empty_field_handling)
        self.empty_field_handler = EmptyFieldHandler(empty_field_handling)
        
        self.publish_event('anki:field_mapping_configured', {
            'field_mappings': field_mappings
        })
    
    def export_entry(
        self, 
        entry: Dict[str, Any], 
        deck_name: str,
        note_type: str,
        tags: List[str] = None,
        field_mappings: Dict[str, str] = None
    ) -> Optional[int]:
        """
        Export a dictionary entry to Anki.
        
        Args:
            entry: The dictionary entry
            deck_name: The name of the Anki deck
            note_type: The note type to use
            tags: Optional list of tags to apply
            field_mappings: Optional field mappings (overrides configured mappings)
            
        Returns:
            The ID of the created note, or None if export failed
        """
        # Check connection
        if not self.connection_status and not self.refresh_connection_status():
            self.publish_event('anki:export_failed', {
                'reason': 'connection_error',
                'headword': entry.get('headword', '')
            })
            return None
        
        try:
            # Use provided field mappings or default
            mapper = self.field_mapper
            if field_mappings:
                mapper = AnkiFieldMapper(field_mappings)
            
            # Map entry to fields
            fields = mapper.map_entry_to_fields(entry)
            
            # Process tags
            if tags is None:
                tags = []
            else:
                tags = list(tags)  # Create a copy
            
            # Add source and target language tags
            if 'metadata' in entry:
                source_lang = entry['metadata'].get('source_language')
                target_lang = entry['metadata'].get('target_language')
                
                if source_lang and f"source:{source_lang}" not in tags:
                    tags.append(f"source:{source_lang}")
                    
                if target_lang and f"target:{target_lang}" not in tags:
                    tags.append(f"target:{target_lang}")
            
            # Add 'DeepDict' tag if not already present
            if 'DeepDict' not in tags:
                tags.append('DeepDict')
            
            # Add the note
            note_id = self.add_note(deck_name, note_type, fields, tags)
            
            if note_id:
                self.publish_event('anki:entry_exported', {
                    'headword': entry.get('headword', ''),
                    'note_id': note_id,
                    'deck_name': deck_name,
                    'note_type': note_type
                })
                
            return note_id
            
        except Exception as e:
            self.publish_event('anki:export_failed', {
                'headword': entry.get('headword', ''),
                'error': str(e)
            })
            return None
    
    def export_example(
        self, 
        entry: Dict[str, Any],
        example_index: int,
        meaning_index: int,
        deck_name: str,
        note_type: str,
        tags: List[str] = None,
        field_mappings: Dict[str, str] = None
    ) -> Optional[int]:
        """
        Export a specific example from an entry to Anki.
        
        Args:
            entry: The dictionary entry
            example_index: The index of the example within the meaning
            meaning_index: The index of the meaning within the entry
            deck_name: The name of the Anki deck
            note_type: The note type to use
            tags: Optional list of tags to apply
            field_mappings: Optional field mappings (overrides configured mappings)
            
        Returns:
            The ID of the created note, or None if export failed
        """
        try:
            # Create a modified entry with the selected example and meaning
            if 'meanings' not in entry or meaning_index >= len(entry['meanings']):
                self.publish_event('anki:export_failed', {
                    'headword': entry.get('headword', ''),
                    'reason': 'invalid_meaning_index'
                })
                return None
                
            meaning = entry['meanings'][meaning_index]
            
            if 'examples' not in meaning or example_index >= len(meaning['examples']):
                self.publish_event('anki:export_failed', {
                    'headword': entry.get('headword', ''),
                    'reason': 'invalid_example_index'
                })
                return None
                
            example = meaning['examples'][example_index]
            
            # Create a modified entry with selected meaning and example
            export_entry = entry.copy()
            export_entry['selected_meaning'] = meaning
            export_entry['selected_example'] = example
            export_entry['meaning_index'] = meaning_index
            export_entry['example_index'] = example_index
            
            # Export the modified entry
            return self.export_entry(export_entry, deck_name, note_type, tags, field_mappings)
            
        except Exception as e:
            self.publish_event('anki:export_failed', {
                'headword': entry.get('headword', ''),
                'error': str(e),
                'meaning_index': meaning_index,
                'example_index': example_index
            })
            return None
    
    def shutdown(self):
        """Clean up resources and shut down the service."""
        self.publish_event('anki:shutdown', {})


class EmptyFieldHandler:
    """
    Handler for empty fields in Anki note creation.
    
    Provides configurable actions for handling empty fields:
    - skip: Skip the field (don't include it)
    - default: Use a default value
    - placeholder: Use a placeholder value
    - error: Raise an error
    """
    
    ACTIONS = {
        "skip": lambda name, value, config: None,
        "default": lambda name, value, config: config.get("default", f"[No {name}]"),
        "placeholder": lambda name, value, config: f"[No {name}]",
        "error": lambda name, value, config: (_ for _ in ()).throw(ValueError(f"Field '{name}' is required but has no value"))
    }
    
    def __init__(self, empty_field_config: Dict[str, Dict[str, Any]] = None):
        """
        Initialize the empty field handler.
        
        Args:
            empty_field_config: Configuration for empty field handling
                Format: {field_name: {"action": "skip|default|placeholder|error", "default": "value"}}
        """
        self.config = empty_field_config or {}
    
    def process_field(self, field_name: str, value: Optional[str]) -> Optional[str]:
        """
        Process a field value based on configuration.
        
        Args:
            field_name: The name of the field
            value: The value of the field (may be None or empty)
            
        Returns:
            The processed value, or None if the field should be skipped
            
        Raises:
            ValueError: If action is "error" and the field is empty
        """
        # If value is not empty, return it as is
        if value:
            return value
            
        # Get the configuration for this field
        field_config = self.config.get(field_name, {"action": "placeholder"})
        action = field_config.get("action", "placeholder")
        
        # Get the handler for the action
        handler = self.ACTIONS.get(action)
        if not handler:
            # Default to placeholder if action is invalid
            handler = self.ACTIONS["placeholder"]
            
        return handler(field_name, value, field_config)


class AnkiFieldMapper:
    """
    Maps dictionary entry fields to Anki note fields using dot notation.
    
    Supports special paths like "selected_meaning.definition" to access nested data
    and paths starting with "selected_" for fields that are selected by the user.
    """
    
    def __init__(self, field_mappings: Dict[str, str], empty_field_handling: Dict[str, Dict[str, Any]] = None):
        """
        Initialize the field mapper.
        
        Args:
            field_mappings: Mapping of Anki field names to dictionary entry paths
            empty_field_handling: Configuration for empty field handling
        """
        self.field_mappings = field_mappings
        self.empty_field_handler = EmptyFieldHandler(empty_field_handling)
    
    def extract_field_data(self, entry: Dict[str, Any], field_path: str) -> Optional[str]:
        """
        Extract data from an entry using dot notation path.
        
        Args:
            entry: The dictionary entry
            field_path: The path to the data (e.g., "headword", "meanings.0.definition")
            
        Returns:
            The extracted data, or None if not found
        """
        if not field_path:
            return None
            
        # Handle direct field access
        if field_path in entry:
            return str(entry[field_path])
            
        # Split the path by dots
        parts = field_path.split('.')
        
        # Start with the entry
        current = entry
        
        # Follow the path
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            else:
                return None
                
        # Convert to string if not None
        return str(current) if current is not None else None
    
    def map_entry_to_fields(self, entry: Dict[str, Any]) -> Dict[str, str]:
        """
        Map a dictionary entry to Anki fields.
        
        Args:
            entry: The dictionary entry
            
        Returns:
            The mapped Anki fields
        """
        result = {}
        
        for anki_field, entry_path in self.field_mappings.items():
            # Extract the data
            value = self.extract_field_data(entry, entry_path)
            
            # Process empty fields
            processed_value = self.empty_field_handler.process_field(anki_field, value)
            
            # Add to result if not None (none means skip)
            if processed_value is not None:
                result[anki_field] = processed_value
                
        return result