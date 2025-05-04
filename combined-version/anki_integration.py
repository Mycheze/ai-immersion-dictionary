import json
import requests
from typing import Dict, List, Any, Optional, Callable, Union
import uuid

class AnkiConnector:
    """
    Connector for the Anki Connect API.
    
    Provides methods to interact with Anki through the AnkiConnect addon.
    Requires the AnkiConnect addon to be installed in Anki:
    https://ankiweb.net/shared/info/2055492159
    """
    
    def __init__(self, url: str = "http://localhost:8765"):
        """
        Initialize the AnkiConnect connector.
        
        Args:
            url (str): The URL where AnkiConnect is running. Default: http://localhost:8765
        """
        self.url = url
    
    def request(self, action: str, **params) -> Dict[str, Any]:
        """
        Send a request to the Anki Connect API.
        
        Args:
            action (str): The action to perform
            **params: Additional parameters for the action
            
        Returns:
            Dict: The response from AnkiConnect
            
        Raises:
            ConnectionError: If the connection to AnkiConnect fails
            Exception: If the request fails or returns an error
        """
        request_data = {
            "action": action,
            "version": 6,
            "params": params
        }
        
        print(f"Sending request to AnkiConnect: {action} with params: {params}")
        
        try:
            response = requests.post(self.url, json=request_data)
            
            # Print response status and content for debugging
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text[:100]}...")  # Print first 100 chars
            
            response.raise_for_status()
            
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {response.text}")
                raise Exception(f"Invalid JSON response from AnkiConnect: {str(e)}")
            
            # AnkiConnect returns {"result": data, "error": null} on success
            # Only raise an error if error field exists AND is not null
            if 'error' in result and result['error'] is not None:
                raise Exception(f"AnkiConnect error: {result['error']}")
                
            # Make sure result field exists
            if 'result' not in result:
                raise Exception(f"Unexpected response format from AnkiConnect: {result}")
                
            return result
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Failed to connect to AnkiConnect at {self.url}. Is Anki running with AnkiConnect addon installed?")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request to AnkiConnect failed: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        Test the connection to AnkiConnect.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            response = requests.post(self.url, json={
                "action": "version",
                "version": 6
            })
            
            if response.status_code == 200:
                print(f"Successfully connected to Anki Connect. Response: {response.text}")
                try:
                    result = response.json()
                    if 'result' in result:
                        print(f"Anki Connect version: {result['result']}")
                        return True
                except:
                    pass
                    
            print(f"Connected to Anki Connect but got unexpected response: {response.text}")
            return False
        except ConnectionError as e:
            print(f"Connection error when testing Anki Connect: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error when testing Anki Connect: {str(e)}")
            return False
    
    def list_decks(self) -> List[str]:
        """
        Get a list of all decks in Anki.
        
        Returns:
            List[str]: List of deck names
            
        Raises:
            Exception: If the request fails
        """
        result = self.request("deckNames")
        return result.get('result', [])
    
    def list_note_types(self) -> List[str]:
        """
        Get a list of all note types (models) in Anki.
        
        Returns:
            List[str]: List of note type names
            
        Raises:
            Exception: If the request fails
        """
        result = self.request("modelNames")
        return result.get('result', [])
    
    def get_note_type_fields(self, note_type: str) -> List[str]:
        """
        Get a list of fields for a specific note type.
        
        Args:
            note_type (str): The name of the note type
            
        Returns:
            List[str]: List of field names
            
        Raises:
            Exception: If the request fails
        """
        result = self.request("modelFieldNames", modelName=note_type)
        return result.get('result', [])
    
    def add_note(self, deck_name: str, model_name: str, fields: Dict[str, str], tags: List[str] = None) -> int:
        """
        Add a note to a deck.
        
        Args:
            deck_name (str): The name of the deck
            model_name (str): The name of the note type
            fields (Dict[str, str]): The fields of the note (field_name -> value)
            tags (List[str], optional): List of tags to apply to the note
            
        Returns:
            int: The ID of the created note, or None if creation failed
            
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
        
        result = self.request("addNote", note=note_data)
        return result.get('result')


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
            empty_field_config (Dict): Configuration for empty field handling
                Format: {field_name: {"action": "skip|default|placeholder|error", "default": "value"}}
        """
        self.config = empty_field_config or {}
    
    def process_field(self, field_name: str, value: Optional[str]) -> Optional[str]:
        """
        Process a field value based on configuration.
        
        Args:
            field_name (str): The name of the field
            value (str): The value of the field (may be None or empty)
            
        Returns:
            str: The processed value, or None if the field should be skipped
            
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
            field_mappings (Dict[str, str]): Mapping of Anki field names to dictionary entry paths
            empty_field_handling (Dict, optional): Configuration for empty field handling
        """
        self.field_mappings = field_mappings
        self.empty_field_handler = EmptyFieldHandler(empty_field_handling)
    
    def extract_field_data(self, entry: Dict[str, Any], field_path: str) -> Optional[str]:
        """
        Extract data from an entry using dot notation path.
        
        Args:
            entry (Dict): The dictionary entry
            field_path (str): The path to the data (e.g., "headword", "meanings.0.definition")
            
        Returns:
            str: The extracted data, or None if not found
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
            entry (Dict): The dictionary entry
            
        Returns:
            Dict[str, str]: The mapped Anki fields
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


class AnkiExporter:
    """
    Exports dictionary entries to Anki.
    
    Handles the mapping and export of dictionary entries to Anki notes.
    """
    
    def __init__(self, anki_connector: AnkiConnector, field_mapper: AnkiFieldMapper, settings: Dict[str, Any]):
        """
        Initialize the Anki exporter.
        
        Args:
            anki_connector (AnkiConnector): The Anki connector
            field_mapper (AnkiFieldMapper): The field mapper
            settings (Dict): Application settings
        """
        self.anki_connector = anki_connector
        self.field_mapper = field_mapper
        self.settings = settings
    
    def export_entry(self, entry: Dict[str, Any], note_type: Optional[str] = None) -> int:
        """
        Export a dictionary entry to Anki.
        
        Args:
            entry (Dict): The dictionary entry
            note_type (str, optional): The note type to use. If None, use the default from settings.
            
        Returns:
            int: The ID of the created note
            
        Raises:
            ConnectionError: If the connection to AnkiConnect fails
            ValueError: If required fields are missing
            Exception: If the export fails
        """
        # Check connection
        if not self.anki_connector.test_connection():
            raise ConnectionError("Could not connect to Anki. Make sure Anki is running with AnkiConnect addon installed.")
            
        # Get note type
        if not note_type:
            note_type = self.settings.get('default_note_type')
            
        if not note_type:
            raise ValueError("No note type specified and no default note type in settings.")
            
        # Get note type configuration
        note_config = self.settings.get('note_types', {}).get(note_type, {})
        
        # Get deck
        deck_name = note_config.get('deck', self.settings.get('default_deck'))
        if not deck_name:
            raise ValueError("No deck specified for note type and no default deck in settings.")
            
        # Map fields
        fields = self.field_mapper.map_entry_to_fields(entry)
        
        # Get tags
        tags = self.settings.get('tags', [])
        
        # Add source and target language tags
        if 'metadata' in entry:
            source_lang = entry['metadata'].get('source_language')
            target_lang = entry['metadata'].get('target_language')
            
            if source_lang:
                tags.append(f"source:{source_lang}")
            if target_lang:
                tags.append(f"target:{target_lang}")
                
        # Add note to Anki
        try:
            note_id = self.anki_connector.add_note(deck_name, note_type, fields, tags)
            return note_id
        except Exception as e:
            raise Exception(f"Failed to add note to Anki: {str(e)}")