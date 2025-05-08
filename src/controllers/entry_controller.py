"""
Entry Controller

This module provides the entry controller, which manages dictionary entry
operations such as displaying, regenerating, and exporting entries.
"""

from typing import Dict, Any, Optional, List, Tuple
import json

from .base_controller import BaseController

class EntryController(BaseController):
    """
    Controller for dictionary entry operations.
    
    This controller manages all entry-related operations, including displaying,
    regenerating, exporting, and deleting dictionary entries.
    
    Attributes:
        models: Dictionary of models accessible to the controller
        views: Dictionary of views accessible to the controller
        event_bus: Event system for controller-related notifications
        current_entry: Currently displayed dictionary entry
    """
    
    def __init__(self, models=None, views=None, event_bus=None):
        """
        Initialize the entry controller.
        
        Args:
            models: Dictionary of models accessible to the controller
            views: Dictionary of views accessible to the controller
            event_bus: Event system for controller-related notifications
        """
        super().__init__(models, views, event_bus)
        
        # Internal state
        self.current_entry = None
        self.current_headword = None
        self.focused_meaning_index = -1
        self.focused_example_index = -1
    
    def _register_event_handlers(self):
        """Register event handlers for the entry controller."""
        # Entry events
        self.register_event_handler('entry:displayed', self._on_entry_displayed)
        self.register_event_handler('entry:display_cleared', self._on_entry_display_cleared)
        self.register_event_handler('entry:meaning_focused', self._on_meaning_focused)
        self.register_event_handler('entry:example_focused', self._on_example_focused)
        
        # Action events
        self.register_event_handler('entry:regenerate_requested', self._on_regenerate_requested)
        self.register_event_handler('entry:export_requested', self._on_export_requested)
        self.register_event_handler('entry:export_example_requested', self._on_export_example_requested)
        self.register_event_handler('entry:delete_requested', self._on_delete_requested)
        self.register_event_handler('entry:copied', self._on_entry_copied)
    
    def display_entry(self, entry: Dict[str, Any]):
        """
        Display a dictionary entry.
        
        Args:
            entry: The dictionary entry to display
        """
        # Update internal state
        self.current_entry = entry
        self.current_headword = entry.get('headword', '')
        self.focused_meaning_index = -1
        self.focused_example_index = -1
        
        # Display in view
        entry_display = self.get_view('entry_display')
        if entry_display:
            entry_display.display_entry(entry)
            
        # Notify of entry display
        if self.event_bus:
            self.event_bus.publish('entry:displayed', {
                'headword': self.current_headword,
                'entry_id': entry.get('id')
            })
    
    def clear_display(self):
        """Clear the entry display."""
        # Reset internal state
        self.current_entry = None
        self.current_headword = None
        self.focused_meaning_index = -1
        self.focused_example_index = -1
        
        # Clear view
        entry_display = self.get_view('entry_display')
        if entry_display:
            entry_display.clear_display()
    
    def focus_meaning(self, meaning_index: int):
        """
        Focus a specific meaning in the entry.
        
        Args:
            meaning_index: Index of the meaning to focus
        """
        if not self.current_entry:
            return
            
        meanings = self.current_entry.get('meanings', [])
        if meaning_index < 0 or meaning_index >= len(meanings):
            return
            
        # Update internal state
        self.focused_meaning_index = meaning_index
        self.focused_example_index = -1
        
        # Update view
        entry_display = self.get_view('entry_display')
        if entry_display:
            entry_display.focus_meaning(meaning_index)
    
    def focus_example(self, meaning_index: int, example_index: int):
        """
        Focus a specific example in the entry.
        
        Args:
            meaning_index: Index of the meaning containing the example
            example_index: Index of the example to focus
        """
        if not self.current_entry:
            return
            
        meanings = self.current_entry.get('meanings', [])
        if meaning_index < 0 or meaning_index >= len(meanings):
            return
            
        examples = meanings[meaning_index].get('examples', [])
        if example_index < 0 or example_index >= len(examples):
            return
            
        # Update internal state
        self.focused_meaning_index = meaning_index
        self.focused_example_index = example_index
        
        # Update view
        entry_display = self.get_view('entry_display')
        if entry_display:
            entry_display.focus_example(meaning_index, example_index)
    
    def regenerate_entry(self):
        """Regenerate the current dictionary entry."""
        if not self.current_entry or not self.current_headword:
            self.log_warning("Attempted to regenerate entry with no current entry")
            return
            
        dictionary_model = self.get_model('dictionary')
        request_service = self.get_model('request_service')
        entry_display = self.get_view('entry_display')
        main_window = self.get_view('main_window')
        
        if not dictionary_model or not request_service:
            self.log_error("Missing required models for regeneration", 
                          has_dictionary_model=bool(dictionary_model),
                          has_request_service=bool(request_service))
            return
            
        # Log regeneration attempt
        self.log_info(f"Regenerating entry for '{self.current_headword}'", 
                     headword=self.current_headword)
            
        # Show loading state
        if entry_display:
            entry_display.set_loading_state(True)
            
        if main_window:
            main_window.set_status_message(f"Regenerating entry for '{self.current_headword}'...")
            
        try:
            # Get metadata from current entry
            metadata = self.current_entry.get('metadata', {})
            target_language = metadata.get('target_language')
            source_language = metadata.get('source_language')
            definition_language = metadata.get('definition_language')
            
            self.log_debug("Entry metadata retrieved", 
                          target_language=target_language,
                          source_language=source_language,
                          definition_language=definition_language)
            
            # Define success and error callbacks
            def on_regenerate_success(entry):
                self.log_debug("Regeneration callback received")
                
                # Handle the regenerated entry
                if not entry:
                    self.log_warning(f"Failed to regenerate entry for '{self.current_headword}' - no entry returned")
                    
                    if main_window:
                        main_window.set_status_message(f"Failed to regenerate entry for '{self.current_headword}'")
                        
                    # Reset loading state
                    if entry_display:
                        entry_display.set_loading_state(False)
                    return
                    
                # Save the entry to the database
                entry_id = dictionary_model.save_entry(entry)
                
                if entry_id:
                    self.log_info(f"Successfully regenerated entry for '{self.current_headword}'", 
                                 headword=self.current_headword,
                                 entry_id=entry_id)
                    
                    # Display the new entry
                    if entry_display:
                        entry_display.display_entry(entry)
                        
                    if main_window:
                        main_window.set_status_message(f"Regenerated entry for '{self.current_headword}'")
                        
                    # Update current entry
                    self.current_entry = entry
                    
                    # Notify of regeneration success
                    if self.event_bus:
                        self.event_bus.publish('entry:regenerated', {
                            'headword': self.current_headword,
                            'entry_id': entry_id
                        })
                else:
                    self.log_error(f"Failed to save regenerated entry for '{self.current_headword}'",
                                  headword=self.current_headword)
                    
                    if main_window:
                        main_window.set_status_message(f"Failed to save regenerated entry for '{self.current_headword}'")
                        
                # Reset loading state
                if entry_display:
                    entry_display.set_loading_state(False)
                    
            def on_regenerate_error(error):
                # Log the error
                self.log_error(f"Error regenerating entry for '{self.current_headword}'", 
                              exc_info=True,
                              error=str(error),
                              headword=self.current_headword)
                
                if self.event_bus:
                    self.event_bus.publish('error:regeneration', {
                        'message': f"Error regenerating entry: {error}",
                        'headword': self.current_headword
                    })
                    
                # Update UI
                if main_window:
                    main_window.set_status_message(f"Error regenerating entry: {error}")
                    
                # Reset loading state
                if entry_display:
                    entry_display.set_loading_state(False)
            
            self.log_debug("Submitting regeneration request to service")
                    
            # Request regeneration
            request_service.regenerate_entry(
                self.current_headword,
                target_language,
                source_language,
                definition_language,
                on_regenerate_success,
                on_regenerate_error
            )
                
        except Exception as e:
            # Handle unexpected errors
            self.log_error(f"Unexpected error regenerating entry for '{self.current_headword}'", 
                          exc_info=True,
                          error=str(e),
                          headword=self.current_headword)
            
            if self.event_bus:
                self.event_bus.publish('error:regeneration', {
                    'message': f"Error regenerating entry: {str(e)}"
                })
                
            if main_window:
                main_window.set_status_message(f"Error regenerating entry: {str(e)}")
                
            # Reset loading state
            if entry_display:
                entry_display.set_loading_state(False)
    
    def export_entry(self):
        """Export the current entry to Anki."""
        if not self.current_entry or not self.current_headword:
            return
            
        anki_model = self.get_model('anki')
        user_model = self.get_model('user')
        main_window = self.get_view('main_window')
        
        if not anki_model or not user_model:
            return
            
        try:
            # Check if Anki is enabled and connected
            anki_enabled = user_model.get_setting('anki_enabled', False)
            if not anki_enabled:
                if main_window:
                    main_window.set_status_message("Anki integration is not enabled")
                return
                
            # Test connection
            connected = anki_model.test_connection()
            if not connected:
                if main_window:
                    main_window.set_status_message("Cannot connect to Anki")
                    
                # Update Anki status in main window
                main_window.set_anki_status(False)
                return
                
            # TODO: Show Anki export dialog
            # For now, show a message
            if main_window:
                main_window.set_status_message("Anki export dialog not implemented yet")
                
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:anki_export', {
                    'message': f"Error exporting to Anki: {str(e)}"
                })
                
            if main_window:
                main_window.set_status_message(f"Error exporting to Anki: {str(e)}")
    
    def export_example(self, meaning_index: int, example_index: int):
        """
        Export a specific example to Anki.
        
        Args:
            meaning_index: Index of the meaning containing the example
            example_index: Index of the example to export
        """
        if not self.current_entry or not self.current_headword:
            return
            
        anki_model = self.get_model('anki')
        user_model = self.get_model('user')
        main_window = self.get_view('main_window')
        
        if not anki_model or not user_model:
            return
            
        try:
            # Check if Anki is enabled and connected
            anki_enabled = user_model.get_setting('anki_enabled', False)
            if not anki_enabled:
                if main_window:
                    main_window.set_status_message("Anki integration is not enabled")
                return
                
            # Test connection
            connected = anki_model.test_connection()
            if not connected:
                if main_window:
                    main_window.set_status_message("Cannot connect to Anki")
                    
                # Update Anki status in main window
                main_window.set_anki_status(False)
                return
                
            # Get meaning and example
            meanings = self.current_entry.get('meanings', [])
            if meaning_index < 0 or meaning_index >= len(meanings):
                return
                
            meaning = meanings[meaning_index]
            examples = meaning.get('examples', [])
            if example_index < 0 or example_index >= len(examples):
                return
                
            example = examples[example_index]
            
            # Get Anki settings
            deck_name = user_model.get_setting('default_deck', 'Language Learning')
            note_type = user_model.get_setting('default_note_type', 'Example-Based')
            
            note_types = user_model.get_setting('note_types', {})
            if note_type in note_types:
                note_config = note_types[note_type]
                field_mappings = note_config.get('field_mappings', {})
                deck_name = note_config.get('deck', deck_name)
            else:
                field_mappings = {
                    'Word': 'headword',
                    'Definition': 'selected_meaning.definition',
                    'Example': 'selected_example.sentence',
                    'Translation': 'selected_example.translation'
                }
                
            # Prepare enriched entry with selected meaning and example
            enriched_entry = self.current_entry.copy()
            enriched_entry['selected_meaning'] = meaning
            enriched_entry['selected_example'] = example
            
            # Add tags
            tags = user_model.get_setting('tags', ['AI-Dictionary'])
            
            # Create note
            note_id = anki_model.create_note(
                enriched_entry,
                deck_name,
                note_type,
                field_mappings,
                tags
            )
            
            # Show result
            if note_id:
                if main_window:
                    main_window.set_status_message(f"Example exported to Anki deck '{deck_name}'")
            else:
                if main_window:
                    main_window.set_status_message("Failed to export example to Anki")
                    
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:anki_export', {
                    'message': f"Error exporting to Anki: {str(e)}"
                })
                
            if main_window:
                main_window.set_status_message(f"Error exporting to Anki: {str(e)}")
    
    def delete_entry(self):
        """Delete the current dictionary entry."""
        if not self.current_entry or not self.current_headword:
            return
            
        dictionary_model = self.get_model('dictionary')
        main_window = self.get_view('main_window')
        
        if not dictionary_model:
            return
            
        try:
            # Get metadata from current entry
            metadata = self.current_entry.get('metadata', {})
            target_language = metadata.get('target_language')
            source_language = metadata.get('source_language')
            definition_language = metadata.get('definition_language')
            
            # Delete the entry
            success = dictionary_model.delete_entry(
                self.current_headword,
                target_language,
                source_language,
                definition_language
            )
            
            if success:
                # Clear display
                self.clear_display()
                
                if main_window:
                    main_window.set_status_message(f"Deleted entry for '{self.current_headword}'")
                    
                # Notify that entry was deleted
                if self.event_bus:
                    self.event_bus.publish('entry:deleted', {
                        'headword': self.current_headword
                    })
                    
                # Request filter refresh
                if self.event_bus:
                    self.event_bus.publish('search_filter:changed', {
                        'filter_text': ''  # Refresh all entries
                    })
            else:
                if main_window:
                    main_window.set_status_message(f"Failed to delete entry for '{self.current_headword}'")
                    
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:entry_deletion', {
                    'message': f"Error deleting entry: {str(e)}"
                })
                
            if main_window:
                main_window.set_status_message(f"Error deleting entry: {str(e)}")
    
    # Event handlers
    
    def _on_entry_displayed(self, data: Optional[Dict[str, Any]] = None):
        """Handle entry displayed event."""
        if not data:
            return
            
        # Extract entry data
        headword = data.get('headword', '')
        entry_id = data.get('entry_id')
        
        # Update internal state
        self.current_headword = headword
        # Note: We don't update current_entry here because we don't have the full entry
    
    def _on_entry_display_cleared(self, data: Optional[Dict[str, Any]] = None):
        """Handle entry display cleared event."""
        # Reset internal state
        self.current_entry = None
        self.current_headword = None
        self.focused_meaning_index = -1
        self.focused_example_index = -1
    
    def _on_meaning_focused(self, data: Optional[Dict[str, Any]] = None):
        """Handle meaning focused event."""
        if not data:
            return
            
        # Extract focus data
        meaning_index = data.get('meaning_index', -1)
        
        # Update internal state
        self.focused_meaning_index = meaning_index
        self.focused_example_index = -1
    
    def _on_example_focused(self, data: Optional[Dict[str, Any]] = None):
        """Handle example focused event."""
        if not data:
            return
            
        # Extract focus data
        meaning_index = data.get('meaning_index', -1)
        example_index = data.get('example_index', -1)
        
        # Update internal state
        self.focused_meaning_index = meaning_index
        self.focused_example_index = example_index
    
    def _on_regenerate_requested(self, data: Optional[Dict[str, Any]] = None):
        """Handle regenerate entry request event."""
        if not data:
            return
            
        # Extract entry data
        entry = data.get('entry')
        
        if entry:
            # Update current entry
            self.current_entry = entry
            self.current_headword = entry.get('headword', '')
            
        # Regenerate the entry
        self.regenerate_entry()
    
    def _on_export_requested(self, data: Optional[Dict[str, Any]] = None):
        """Handle export entry request event."""
        if not data:
            return
            
        # Extract entry data
        entry = data.get('entry')
        
        if entry:
            # Update current entry
            self.current_entry = entry
            self.current_headword = entry.get('headword', '')
            
        # Export the entry
        self.export_entry()
    
    def _on_export_example_requested(self, data: Optional[Dict[str, Any]] = None):
        """Handle export example request event."""
        if not data:
            return
            
        # Extract entry and example data
        entry = data.get('entry')
        meaning_index = data.get('meaning_index', -1)
        example_index = data.get('example_index', -1)
        
        if entry:
            # Update current entry
            self.current_entry = entry
            self.current_headword = entry.get('headword', '')
            
        # Export the example
        self.export_example(meaning_index, example_index)
    
    def _on_delete_requested(self, data: Optional[Dict[str, Any]] = None):
        """Handle delete entry request event."""
        if not data:
            return
            
        # Extract entry data
        entry = data.get('entry')
        
        if entry:
            # Update current entry
            self.current_entry = entry
            self.current_headword = entry.get('headword', '')
            
        # Delete the entry
        self.delete_entry()
    
    def _on_entry_copied(self, data: Optional[Dict[str, Any]] = None):
        """Handle entry copied event."""
        main_window = self.get_view('main_window')
        
        if main_window and data and 'headword' in data:
            headword = data.get('headword', '')
            main_window.set_status_message(f"Entry for '{headword}' copied to clipboard")