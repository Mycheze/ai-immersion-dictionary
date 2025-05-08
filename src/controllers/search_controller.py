"""
Search Controller

This module provides the search controller, which manages all search operations
including word lookup, filtering, history, and language selection.
"""

from typing import Dict, Any, Optional, List, Tuple

from .base_controller import BaseController

class SearchController(BaseController):
    """
    Controller for search operations.
    
    This controller manages all search-related operations, including word
    lookup, entry filtering, search history, and language selection.
    
    Attributes:
        models: Dictionary of models accessible to the controller
        views: Dictionary of views accessible to the controller
        event_bus: Event system for controller-related notifications
        filtered_entries: Currently filtered list of dictionary entries
    """
    
    def __init__(self, models=None, views=None, event_bus=None):
        """
        Initialize the search controller.
        
        Args:
            models: Dictionary of models accessible to the controller
            views: Dictionary of views accessible to the controller
            event_bus: Event system for controller-related notifications
        """
        super().__init__(models, views, event_bus)
        
        # Internal state
        self.filtered_entries = []
        self.current_search_term = ""
        self.current_filter_text = ""
        self.current_language_filters = {
            'target_language': None,
            'definition_language': None
        }
        
        # Initial data loading
        self._load_initial_data()
    
    def _register_event_handlers(self):
        """Register event handlers for the search controller."""
        # Search events
        self.register_event_handler('search:requested', self._on_search_requested)
        self.register_event_handler('headword:selected', self._on_headword_selected)
        self.register_event_handler('history:item_selected', self._on_history_item_selected)
        self.register_event_handler('history:clear_requested', self._on_clear_history_requested)
        
        # Context events
        self.register_event_handler('context:text_selected', self._on_context_text_selected)
        
        # Filter events
        self.register_event_handler('language_filter:changed', self._on_language_filter_changed)
        self.register_event_handler('search_filter:changed', self._on_search_filter_changed)
        
        # Clipboard events
        self.register_event_handler('clipboard:monitoring_changed', self._on_clipboard_monitoring_changed)
    
    def _load_initial_data(self):
        """Load initial data for the search controller."""
        # Load filtered entries based on current filters
        self._refresh_filtered_entries()
        
        # Update language filter with current settings
        self._apply_language_preferences()
    
    def _apply_language_preferences(self):
        """Apply language preferences from user settings."""
        user_model = self.get_model('user')
        language_filter = self.get_view('language_filter')
        
        if not user_model or not language_filter:
            return
            
        # Get preferred languages from user settings
        target_language = user_model.get_setting('target_language')
        definition_language = user_model.get_setting('definition_language')
        
        # Update language filter
        language_filter.set_language_filters(target_language, definition_language)
        
        # Update current filters
        self.current_language_filters = {
            'target_language': target_language,
            'definition_language': definition_language
        }
    
    def _refresh_filtered_entries(self):
        """Refresh the filtered entries list based on current filters."""
        dictionary_model = self.get_model('dictionary')
        language_filter = self.get_view('language_filter')
        main_window = self.get_view('main_window')
        async_service = self.get_model('async_service')
        
        if not dictionary_model or not language_filter or not async_service:
            return
            
        # Update UI to show loading state
        if main_window:
            main_window.set_status_message("Loading entries...")
            
        try:
            # Prepare search filters
            filters = {
                'search_term': self.current_filter_text,
                'target_language': self.current_language_filters.get('target_language'),
                'definition_language': self.current_language_filters.get('definition_language')
            }
            
            # Define callbacks
            def on_search_success(entries):
                # Update filtered entries
                self.filtered_entries = entries
                
                # Update language filter view with filtered entries
                language_filter.update_headword_list(self.filtered_entries)
                
                # Notify of filter update
                if self.event_bus:
                    self.event_bus.publish('search:filter_updated', {
                        'count': len(self.filtered_entries),
                        'filters': filters
                    })
                    
                # Update status message
                if main_window:
                    main_window.set_status_message(f"Found {len(entries)} entries")
            
            def on_search_error(error):
                # Notify of error
                if self.event_bus:
                    self.event_bus.publish('error:search', {
                        'message': f"Error filtering entries: {error}"
                    })
                    
                # Update status message
                if main_window:
                    main_window.set_status_message(f"Error loading entries: {error}")
            
            # Get filtered entries asynchronously
            dictionary_model.search_entries_async(
                filters,
                on_search_success,
                on_search_error
            )
                
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:search', {
                    'message': f"Error filtering entries: {str(e)}"
                })
                
            # Update status message
            if main_window:
                main_window.set_status_message(f"Error filtering entries: {str(e)}")
    
    def search_word(self, word: str, context: Optional[str] = None):
        """
        Search for a word in the dictionary.
        
        Args:
            word: Word to search for
            context: Optional context sentence
        """
        dictionary_model = self.get_model('dictionary')
        user_model = self.get_model('user')
        request_service = self.get_model('request_service')
        entry_display = self.get_view('entry_display')
        main_window = self.get_view('main_window')
        
        if not dictionary_model or not user_model or not request_service:
            return
            
        # Save search term
        self.current_search_term = word
        
        # Update views to show loading state
        if entry_display:
            entry_display.set_loading_state(True)
            
        if main_window:
            main_window.set_status_message(f"Searching for '{word}'...")
            
        try:
            # Get language settings
            target_language = self.current_language_filters.get('target_language')
            definition_language = self.current_language_filters.get('definition_language')
            
            if not target_language:
                target_language = user_model.get_setting('target_language')
                
            if not definition_language:
                definition_language = user_model.get_setting('definition_language')
                
            # Define callbacks for entry lookup
            def on_entry_found(entry):
                if entry:
                    # Entry exists, display it
                    if entry_display:
                        entry_display.display_entry(entry)
                        
                    if main_window:
                        main_window.set_status_message(f"Found existing entry for '{word}'")
                        
                    # Add to recent lookups
                    user_model.add_recent_lookup(word, target_language, definition_language)
                    
                    # Update search history in view
                    search_panel = self.get_view('search_panel')
                    if search_panel:
                        search_panel.update_history_list(user_model.get_recent_lookups())
                        
                    # Reset loading state since we're done
                    if entry_display:
                        entry_display.set_loading_state(False)
                else:
                    # Entry doesn't exist, need to create it
                    if main_window:
                        main_window.set_status_message(f"Creating new entry for '{word}'...")
                        
                    # Start with lemmatization request
                    self._start_lemmatization(word, context, target_language, definition_language)
            
            def on_entry_error(error):
                if main_window:
                    main_window.set_status_message(f"Error looking up '{word}': {error}")
                    
                # Reset loading state
                if entry_display:
                    entry_display.set_loading_state(False)
                    
                if self.event_bus:
                    self.event_bus.publish('error:search', {
                        'message': f"Error looking up word: {error}"
                    })
            
            # Check if entry already exists in database (asynchronously)
            dictionary_model.get_entry_by_headword_async(
                word, 
                target_language, 
                definition_language, 
                definition_language,
                on_entry_found,
                on_entry_error
            )
                
        except Exception as e:
            # Handle error
            if self.event_bus:
                self.event_bus.publish('error:search', {
                    'message': f"Error searching for word: {str(e)}"
                })
                
            if main_window:
                main_window.set_status_message(f"Error searching for '{word}': {str(e)}")
                
            # Reset loading state on error
            if entry_display:
                entry_display.set_loading_state(False)
    
    def _start_lemmatization(
        self, 
        word: str, 
        context: Optional[str],
        target_language: str,
        definition_language: str
    ):
        """
        Start the lemmatization process for a word.
        
        Args:
            word: Word to lemmatize
            context: Optional context sentence
            target_language: Target language
            definition_language: Definition language
        """
        request_service = self.get_model('request_service')
        main_window = self.get_view('main_window')
        
        if not request_service:
            return
            
        # Update status
        if main_window:
            main_window.set_status_message(f"Getting lemma for '{word}'...")
            
        # Define success and error callbacks
        def on_lemma_success(lemma):
            # Proceed to entry creation with the lemmatized word
            self._start_entry_creation(lemma, context, target_language, definition_language)
            
        def on_lemma_error(error):
            # Log the error
            if self.event_bus:
                self.event_bus.publish('error:lemmatization', {
                    'message': f"Error getting lemma: {error}",
                    'word': word
                })
                
            # Continue with the original word if lemmatization fails
            self._start_entry_creation(word, context, target_language, definition_language)
            
        # Request lemmatization
        request_service.get_lemma(word, context, on_lemma_success, on_lemma_error)
    
    def _start_entry_creation(
        self, 
        word: str, 
        context: Optional[str],
        target_language: str,
        definition_language: str
    ):
        """
        Start the entry creation process.
        
        Args:
            word: Word to create entry for (lemmatized)
            context: Optional context sentence
            target_language: Target language
            definition_language: Definition language
        """
        request_service = self.get_model('request_service')
        user_model = self.get_model('user')
        main_window = self.get_view('main_window')
        
        if not request_service or not user_model:
            return
            
        # Update status
        if main_window:
            main_window.set_status_message(f"Creating dictionary entry for '{word}'...")
            
        # Define success and error callbacks
        def on_entry_success(entry):
            # Process the new entry
            self._handle_new_entry(entry, word, target_language, definition_language)
            
        def on_entry_error(error):
            # Log the error
            if self.event_bus:
                self.event_bus.publish('error:entry_creation', {
                    'message': f"Error creating entry: {error}",
                    'word': word
                })
                
            # Update UI
            if main_window:
                main_window.set_status_message(f"Error creating entry for '{word}': {error}")
                
            # Reset loading state
            entry_display = self.get_view('entry_display')
            if entry_display:
                entry_display.set_loading_state(False)
                
        # Request entry creation
        request_service.create_entry(
            word, 
            target_language, 
            definition_language, 
            context,
            on_entry_success,
            on_entry_error
        )
    
    def _handle_new_entry(
        self, 
        entry: Dict[str, Any],
        word: str,
        target_language: str,
        definition_language: str
    ):
        """
        Handle a newly created dictionary entry.
        
        Args:
            entry: The new dictionary entry
            word: The word that was looked up
            target_language: Target language
            definition_language: Definition language
        """
        dictionary_model = self.get_model('dictionary')
        user_model = self.get_model('user')
        entry_display = self.get_view('entry_display')
        main_window = self.get_view('main_window')
        
        if not dictionary_model or not user_model:
            return
            
        try:
            # Check if we got a valid entry
            if not entry:
                if main_window:
                    main_window.set_status_message(f"Failed to create entry for '{word}'")
                return
                
            # Define callbacks for saving entry
            def on_save_success(entry_id):
                if entry_id:
                    # Display the new entry
                    if entry_display:
                        entry_display.display_entry(entry)
                        
                    if main_window:
                        main_window.set_status_message(f"Created new entry for '{word}'")
                        
                    # Add to recent lookups
                    user_model.add_recent_lookup(word, target_language, definition_language)
                    
                    # Update search history in view
                    search_panel = self.get_view('search_panel')
                    if search_panel:
                        search_panel.update_history_list(user_model.get_recent_lookups())
                        
                    # Refresh filtered entries
                    self._refresh_filtered_entries()
                else:
                    if main_window:
                        main_window.set_status_message(f"Failed to save entry for '{word}'")
            
            def on_save_error(error):
                if main_window:
                    main_window.set_status_message(f"Error saving entry for '{word}': {error}")
                    
                if self.event_bus:
                    self.event_bus.publish('error:entry_saving', {
                        'message': f"Error saving entry: {error}",
                        'word': word
                    })
            
            # Save to database asynchronously
            dictionary_model.save_entry_async(entry, on_save_success, on_save_error)
                    
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:entry_processing', {
                    'message': f"Error processing new entry: {str(e)}"
                })
                
            if main_window:
                main_window.set_status_message(f"Error processing entry: {str(e)}")
                
        finally:
            # Reset loading state
            if entry_display:
                entry_display.set_loading_state(False)
    
    def select_headword(self, headword: str):
        """
        Select and display a headword from the filtered list.
        
        Args:
            headword: Headword to select
        """
        dictionary_model = self.get_model('dictionary')
        entry_display = self.get_view('entry_display')
        main_window = self.get_view('main_window')
        
        if not dictionary_model or not entry_display:
            return
            
        try:
            # Update views to show loading state
            entry_display.set_loading_state(True)
            
            if main_window:
                main_window.set_status_message(f"Loading entry for '{headword}'...")
                
            # Get language filters
            target_language = self.current_language_filters.get('target_language')
            definition_language = self.current_language_filters.get('definition_language')
            
            # Define callbacks for entry lookup
            def on_entry_found(entry):
                if entry:
                    # Display the entry
                    entry_display.display_entry(entry)
                    
                    if main_window:
                        main_window.set_status_message(f"Loaded entry for '{headword}'")
                else:
                    if main_window:
                        main_window.set_status_message(f"Entry not found for '{headword}'")
                        
                # Reset loading state
                entry_display.set_loading_state(False)
            
            def on_entry_error(error):
                if main_window:
                    main_window.set_status_message(f"Error loading entry for '{headword}': {error}")
                    
                if self.event_bus:
                    self.event_bus.publish('error:entry_selection', {
                        'message': f"Error loading entry: {error}",
                        'headword': headword
                    })
                    
                # Reset loading state
                entry_display.set_loading_state(False)
            
            # Get the entry asynchronously
            dictionary_model.get_entry_by_headword_async(
                headword, 
                target_language, 
                None, 
                definition_language,
                on_entry_found,
                on_entry_error
            )
                    
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:entry_selection', {
                    'message': f"Error selecting entry: {str(e)}"
                })
                
            if main_window:
                main_window.set_status_message(f"Error loading entry for '{headword}': {str(e)}")
                
        finally:
            # Reset loading state
            entry_display.set_loading_state(False)
    
    # Event handlers
    
    def _on_search_requested(self, data: Optional[Dict[str, Any]] = None):
        """Handle search request event."""
        if not data:
            return
            
        # Extract search parameters
        term = data.get('term', '')
        context = data.get('context')
        
        if not term:
            return
            
        # Perform the search
        self.search_word(term, context)
    
    def _on_headword_selected(self, data: Optional[Dict[str, Any]] = None):
        """Handle headword selection event."""
        if not data:
            return
            
        # Extract headword
        headword = data.get('headword', '')
        
        if not headword:
            return
            
        # Select the headword
        self.select_headword(headword)
    
    def _on_history_item_selected(self, data: Optional[Dict[str, Any]] = None):
        """Handle history item selection event."""
        if not data:
            return
            
        # Extract index
        index = data.get('index', -1)
        
        if index < 0:
            return
            
        # Get the history item
        user_model = self.get_model('user')
        if not user_model:
            return
            
        recent_lookups = user_model.get_recent_lookups()
        if index >= len(recent_lookups):
            return
            
        # Get item details
        item = recent_lookups[index]
        headword = item.get('headword', '')
        target_language = item.get('target_language')
        definition_language = item.get('definition_language')
        
        if not headword:
            return
            
        # Update language filters if needed
        language_filter = self.get_view('language_filter')
        if language_filter and target_language and definition_language:
            language_filter.set_language_filters(target_language, definition_language)
            
            # Update current filters
            self.current_language_filters = {
                'target_language': target_language,
                'definition_language': definition_language
            }
            
        # Select the headword
        self.select_headword(headword)
    
    def _on_clear_history_requested(self, data: Optional[Dict[str, Any]] = None):
        """Handle clear history request event."""
        user_model = self.get_model('user')
        search_panel = self.get_view('search_panel')
        
        if not user_model or not search_panel:
            return
            
        # Clear recent lookups
        user_model.clear_recent_lookups()
        
        # Update search panel
        search_panel.update_history_list([])
    
    def _on_context_text_selected(self, data: Optional[Dict[str, Any]] = None):
        """Handle context text selection event."""
        if not data:
            return
            
        # Extract selected text
        selected_text = data.get('selected_text', '')
        context = data.get('context', '')
        
        if not selected_text:
            return
            
        # Update search entry with selected text
        search_panel = self.get_view('search_panel')
        if search_panel:
            search_panel.set_search_term(selected_text)
    
    def _on_language_filter_changed(self, data: Optional[Dict[str, Any]] = None):
        """Handle language filter change event."""
        if not data:
            return
            
        # Extract filter settings
        target_language = data.get('target_language')
        definition_language = data.get('definition_language')
        
        # Update current filters
        self.current_language_filters = {
            'target_language': target_language,
            'definition_language': definition_language
        }
        
        # Refresh filtered entries
        self._refresh_filtered_entries()
        
        # Save to user settings
        user_model = self.get_model('user')
        if user_model:
            settings_to_update = {}
            
            if target_language and target_language != "All":
                settings_to_update['target_language'] = target_language
                
            if definition_language and definition_language != "All":
                settings_to_update['definition_language'] = definition_language
                
            if settings_to_update:
                user_model.update_settings(settings_to_update)
    
    def _on_search_filter_changed(self, data: Optional[Dict[str, Any]] = None):
        """Handle search filter change event."""
        if not data:
            return
            
        # Extract filter text
        filter_text = data.get('filter_text', '')
        
        # Update current filter
        self.current_filter_text = filter_text
        
        # Refresh filtered entries
        self._refresh_filtered_entries()
    
    def _on_clipboard_monitoring_changed(self, data: Optional[Dict[str, Any]] = None):
        """Handle clipboard monitoring change event."""
        if not data:
            return
            
        # Extract active state
        active = data.get('active', False)
        
        # Update user settings
        user_model = self.get_model('user')
        if user_model:
            user_model.set_setting('monitor_clipboard', active)