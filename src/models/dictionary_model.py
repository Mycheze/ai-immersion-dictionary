"""
Dictionary Model

This module provides the data model for dictionary entries, including storage,
retrieval, and manipulation operations.
"""

import json
from typing import List, Dict, Optional, Any, Union, Callable
from datetime import datetime

from ..utils.type_definitions import DictionaryEntry, SearchFilters
from ..utils.text_processing import normalize_language_name, clean_json_content

class DictionaryModel:
    """
    Model for dictionary entry operations.
    
    This class encapsulates all dictionary data operations, providing a clean
    interface for working with dictionary entries regardless of the underlying
    storage mechanism.
    
    Attributes:
        db_manager: The database manager for storage operations
        cached_entries: Dictionary of recently accessed entries
        event_bus: Event system for model-related notifications
    """
    
    def __init__(self, db_service, async_service=None, event_bus=None):
        """
        Initialize the dictionary model.
        
        Args:
            db_service: The database service for storage operations
            async_service: Optional async service for asynchronous operations
            event_bus: Optional event bus for notifications
        """
        self.db_service = db_service
        self.async_service = async_service
        self.event_bus = event_bus
        self.cached_entries = {}
        self.max_cache_size = 100
        self.cache_access_order = []
    
    def get_entry_by_headword(
        self, 
        headword: str, 
        target_lang: Optional[str] = None,
        source_lang: Optional[str] = None,
        definition_lang: Optional[str] = None
    ) -> Optional[DictionaryEntry]:
        """
        Retrieve a dictionary entry by headword.
        
        Args:
            headword: The headword to retrieve
            target_lang: Optional target language filter
            source_lang: Optional source language filter
            definition_lang: Optional definition language filter
            
        Returns:
            The dictionary entry or None if not found
        """
        # Create a cache key based on the search parameters
        cache_key = self._get_cache_key(headword, target_lang, source_lang, definition_lang)
        
        # Check cache first
        if cache_key in self.cached_entries:
            self._update_cache_access(cache_key)
            return self.cached_entries[cache_key]
        
        # Retrieve from database
        entry = self.db_service.get_entry_by_headword(
            headword, source_lang, target_lang, definition_lang
        )
        
        # Update cache if entry was found
        if entry:
            self._cache_entry(cache_key, entry)
            
        return entry
        
    def get_entry_by_headword_async(
        self,
        headword: str,
        target_lang: Optional[str] = None,
        source_lang: Optional[str] = None,
        definition_lang: Optional[str] = None,
        callback: Callable = None,
        error_callback: Callable = None
    ) -> None:
        """
        Retrieve a dictionary entry by headword asynchronously.
        
        Args:
            headword: The headword to retrieve
            target_lang: Optional target language filter
            source_lang: Optional source language filter
            definition_lang: Optional definition language filter
            callback: Function to call with entry on success
            error_callback: Function to call with error message on failure
        """
        # Create a cache key based on the search parameters
        cache_key = self._get_cache_key(headword, target_lang, source_lang, definition_lang)
        
        # Check cache first
        if cache_key in self.cached_entries:
            self._update_cache_access(cache_key)
            if callback:
                callback(self.cached_entries[cache_key])
            return
            
        # Get async service
        async_service = getattr(self, 'async_service', None)
        if not async_service:
            # Fall back to synchronous method if async service not available
            try:
                entry = self.get_entry_by_headword(headword, target_lang, source_lang, definition_lang)
                if callback:
                    callback(entry)
            except Exception as e:
                if error_callback:
                    error_callback(str(e))
                elif self.event_bus:
                    self.event_bus.publish('error:entry_lookup', {
                        'message': f'Error retrieving entry: {str(e)}',
                        'headword': headword
                    })
            return
            
        # Define wrapper callbacks
        def on_entry_success(entry):
            # Update cache if entry was found
            if entry:
                self._cache_entry(cache_key, entry)
                
            # Emit event with result
            if self.event_bus:
                self.event_bus.publish('entry:retrieved', {
                    'headword': headword,
                    'found': entry is not None
                })
                
            # Call user callback
            if callback:
                callback(entry)
                
        def on_entry_error(error):
            # Emit error event
            if self.event_bus:
                self.event_bus.publish('error:entry_lookup', {
                    'message': f'Error retrieving entry: {error}',
                    'headword': headword
                })
                
            # Call user error callback
            if error_callback:
                error_callback(error)
        
        # Perform async entry lookup
        self.db_service.get_entry_by_headword_async(
            async_service,
            headword,
            source_lang,
            target_lang,
            definition_lang,
            callback=on_entry_success,
            error_callback=on_entry_error
        )
    
    def search_entries(self, filters: SearchFilters) -> List[DictionaryEntry]:
        """
        Search for dictionary entries using filters.
        
        Args:
            filters: Dictionary of search filters
            
        Returns:
            List of matching dictionary entries
        """
        # Extract filter parameters
        search_term = filters.get('search_term', '')
        target_lang = filters.get('target_language')
        source_lang = filters.get('source_language')
        definition_lang = filters.get('definition_language')
        
        # Perform database search
        entries = self.db_service.search_entries(
            search_term, source_lang, target_lang, definition_lang
        )
        
        # Emit event with results if event bus exists
        if self.event_bus:
            self.event_bus.publish('search:completed', {
                'search_term': search_term,
                'count': len(entries),
                'filters': filters
            })
            
        return entries
        
    def search_entries_async(self, filters: SearchFilters, callback: Callable = None, error_callback: Callable = None) -> None:
        """
        Search for dictionary entries asynchronously.
        
        Args:
            filters: Dictionary of search filters
            callback: Function to call with results on success
            error_callback: Function to call with error message on failure
        """
        # Extract filter parameters
        search_term = filters.get('search_term', '')
        target_lang = filters.get('target_language')
        source_lang = filters.get('source_language')
        definition_lang = filters.get('definition_language')
        
        # Get async service
        async_service = getattr(self, 'async_service', None)
        if not async_service:
            # Fall back to synchronous search if async service not available
            try:
                entries = self.search_entries(filters)
                if callback:
                    callback(entries)
            except Exception as e:
                if error_callback:
                    error_callback(str(e))
                elif self.event_bus:
                    self.event_bus.publish('error:search', {
                        'message': f'Error in search: {str(e)}'
                    })
            return
            
        # Define wrapper callbacks
        def on_search_success(entries):
            # Emit event with results
            if self.event_bus:
                self.event_bus.publish('search:completed', {
                    'search_term': search_term,
                    'count': len(entries),
                    'filters': filters
                })
                
            # Call user callback
            if callback:
                callback(entries)
                
        def on_search_error(error):
            # Emit error event
            if self.event_bus:
                self.event_bus.publish('error:search', {
                    'message': f'Error in search: {error}',
                    'search_term': search_term
                })
                
            # Call user error callback
            if error_callback:
                error_callback(error)
        
        # Perform async database search
        self.db_service.search_entries_async(
            async_service,
            search_term, 
            source_lang, 
            target_lang, 
            definition_lang,
            callback=on_search_success,
            error_callback=on_search_error
        )
    
    def save_entry(self, entry: DictionaryEntry) -> Optional[int]:
        """
        Save a dictionary entry to storage.
        
        Args:
            entry: The dictionary entry to save
            
        Returns:
            The entry ID if successfully saved, None otherwise
        """
        # Validate entry structure
        if not self._validate_entry(entry):
            if self.event_bus:
                self.event_bus.publish('error:validation', {
                    'message': 'Invalid dictionary entry structure'
                })
            return None
        
        # Save to database
        entry_id = self.db_service.add_entry(entry)
        
        if entry_id and self.event_bus:
            # Get entry metadata
            metadata = entry.get('metadata', {})
            
            # Publish event with entry information
            self.event_bus.publish('entry:saved', {
                'entry_id': entry_id,
                'headword': entry.get('headword', ''),
                'target_language': metadata.get('target_language', ''),
                'definition_language': metadata.get('definition_language', '')
            })
            
        return entry_id
        
    def save_entry_async(self, entry: DictionaryEntry, callback: Callable = None, error_callback: Callable = None) -> None:
        """
        Save a dictionary entry to storage asynchronously.
        
        Args:
            entry: The dictionary entry to save
            callback: Function to call with entry ID on success
            error_callback: Function to call with error message on failure
        """
        # Validate entry structure
        if not self._validate_entry(entry):
            if self.event_bus:
                self.event_bus.publish('error:validation', {
                    'message': 'Invalid dictionary entry structure'
                })
                
            if error_callback:
                error_callback('Invalid dictionary entry structure')
                
            return
            
        # Get async service
        async_service = getattr(self, 'async_service', None)
        if not async_service:
            # Fall back to synchronous method if async service not available
            try:
                entry_id = self.save_entry(entry)
                if callback:
                    callback(entry_id)
            except Exception as e:
                if error_callback:
                    error_callback(str(e))
                elif self.event_bus:
                    self.event_bus.publish('error:entry_saving', {
                        'message': f'Error saving entry: {str(e)}',
                        'headword': entry.get('headword', '')
                    })
            return
            
        # Define wrapper callbacks
        def on_save_success(entry_id):
            if entry_id and self.event_bus:
                # Get entry metadata
                metadata = entry.get('metadata', {})
                
                # Publish event with entry information
                self.event_bus.publish('entry:saved', {
                    'entry_id': entry_id,
                    'headword': entry.get('headword', ''),
                    'target_language': metadata.get('target_language', ''),
                    'definition_language': metadata.get('definition_language', '')
                })
                
            # Call user callback
            if callback:
                callback(entry_id)
                
        def on_save_error(error):
            # Emit error event
            if self.event_bus:
                self.event_bus.publish('error:entry_saving', {
                    'message': f'Error saving entry: {error}',
                    'headword': entry.get('headword', '')
                })
                
            # Call user error callback
            if error_callback:
                error_callback(error)
        
        # Perform async entry save
        self.db_service.add_entry_async(
            async_service,
            entry,
            callback=on_save_success,
            error_callback=on_save_error
        )
    
    def delete_entry(
        self, 
        headword: str, 
        target_lang: Optional[str] = None,
        source_lang: Optional[str] = None,
        definition_lang: Optional[str] = None
    ) -> bool:
        """
        Delete a dictionary entry.
        
        Args:
            headword: The headword to delete
            target_lang: Optional target language filter
            source_lang: Optional source language filter
            definition_lang: Optional definition language filter
            
        Returns:
            True if the entry was deleted, False otherwise
        """
        # Create cache key for the entry
        cache_key = self._get_cache_key(headword, target_lang, source_lang, definition_lang)
        
        # Remove from cache if present
        if cache_key in self.cached_entries:
            del self.cached_entries[cache_key]
            if cache_key in self.cache_access_order:
                self.cache_access_order.remove(cache_key)
        
        # Delete from database
        success = self.db_service.delete_entry(
            headword, source_lang, target_lang, definition_lang
        )
        
        if success and self.event_bus:
            self.event_bus.publish('entry:deleted', {
                'headword': headword,
                'target_language': target_lang,
                'source_language': source_lang,
                'definition_language': definition_lang
            })
            
        return success
        
    def delete_entry_async(
        self,
        headword: str,
        target_lang: Optional[str] = None,
        source_lang: Optional[str] = None,
        definition_lang: Optional[str] = None,
        callback: Callable = None,
        error_callback: Callable = None
    ) -> None:
        """
        Delete a dictionary entry asynchronously.
        
        Args:
            headword: The headword to delete
            target_lang: Optional target language filter
            source_lang: Optional source language filter
            definition_lang: Optional definition language filter
            callback: Function to call with success status on completion
            error_callback: Function to call with error message on failure
        """
        # Create cache key for the entry
        cache_key = self._get_cache_key(headword, target_lang, source_lang, definition_lang)
        
        # Remove from cache if present
        if cache_key in self.cached_entries:
            del self.cached_entries[cache_key]
            if cache_key in self.cache_access_order:
                self.cache_access_order.remove(cache_key)
                
        # Get async service
        async_service = getattr(self, 'async_service', None)
        if not async_service:
            # Fall back to synchronous method if async service not available
            try:
                success = self.delete_entry(headword, target_lang, source_lang, definition_lang)
                if callback:
                    callback(success)
            except Exception as e:
                if error_callback:
                    error_callback(str(e))
                elif self.event_bus:
                    self.event_bus.publish('error:entry_deletion', {
                        'message': f'Error deleting entry: {str(e)}',
                        'headword': headword
                    })
            return
            
        # Define wrapper callbacks
        def on_delete_success(success):
            if success and self.event_bus:
                self.event_bus.publish('entry:deleted', {
                    'headword': headword,
                    'target_language': target_lang,
                    'source_language': source_lang,
                    'definition_language': definition_lang
                })
                
            # Call user callback
            if callback:
                callback(success)
                
        def on_delete_error(error):
            # Emit error event
            if self.event_bus:
                self.event_bus.publish('error:entry_deletion', {
                    'message': f'Error deleting entry: {error}',
                    'headword': headword
                })
                
            # Call user error callback
            if error_callback:
                error_callback(error)
        
        # Perform async entry deletion
        self.db_service.delete_entry_async(
            async_service,
            headword,
            source_lang,
            target_lang,
            definition_lang,
            callback=on_delete_success,
            error_callback=on_delete_error
        )
    
    def get_all_languages(self) -> Dict[str, List[str]]:
        """
        Get all languages used in the dictionary.
        
        Returns:
            Dictionary with source_languages, target_languages, and definition_languages
        """
        return self.db_service.get_all_languages()
        
    def get_all_languages_async(self, callback: Callable = None, error_callback: Callable = None) -> None:
        """
        Get all languages used in the dictionary asynchronously.
        
        Args:
            callback: Function to call with results on success
            error_callback: Function to call with error message on failure
        """
        # Get async service
        async_service = getattr(self, 'async_service', None)
        if not async_service:
            # Fall back to synchronous method if async service not available
            try:
                languages = self.get_all_languages()
                if callback:
                    callback(languages)
            except Exception as e:
                if error_callback:
                    error_callback(str(e))
                elif self.event_bus:
                    self.event_bus.publish('error:languages', {
                        'message': f'Error getting languages: {str(e)}'
                    })
            return
            
        # Define wrapper callbacks
        def on_languages_success(languages):
            # Emit event with results
            if self.event_bus:
                self.event_bus.publish('languages:loaded', {
                    'source_count': len(languages.get('source_languages', [])),
                    'target_count': len(languages.get('target_languages', [])),
                    'definition_count': len(languages.get('definition_languages', []))
                })
                
            # Call user callback
            if callback:
                callback(languages)
                
        def on_languages_error(error):
            # Emit error event
            if self.event_bus:
                self.event_bus.publish('error:languages', {
                    'message': f'Error getting languages: {error}'
                })
                
            # Call user error callback
            if error_callback:
                error_callback(error)
        
        # Perform async languages fetch
        self.db_service.get_all_languages_async(
            async_service,
            callback=on_languages_success,
            error_callback=on_languages_error
        )
    
    def parse_entry_json(self, json_text: str) -> Optional[DictionaryEntry]:
        """
        Parse JSON text into a dictionary entry.
        
        Args:
            json_text: JSON string to parse
            
        Returns:
            Parsed dictionary entry or None if parsing failed
        """
        try:
            # Clean the JSON text (remove markdown code blocks etc.)
            cleaned_text = clean_json_content(json_text)
            
            # Parse JSON into dictionary
            entry = json.loads(cleaned_text)
            
            # Validate the entry structure
            if not self._validate_entry(entry):
                if self.event_bus:
                    self.event_bus.publish('error:validation', {
                        'message': 'Invalid dictionary entry structure in JSON'
                    })
                return None
                
            return entry
            
        except json.JSONDecodeError as e:
            if self.event_bus:
                self.event_bus.publish('error:parsing', {
                    'message': f'Failed to parse JSON: {str(e)}',
                    'json_text': json_text[:100] + '...' if len(json_text) > 100 else json_text
                })
            return None
            
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:unknown', {
                    'message': f'Error processing JSON entry: {str(e)}'
                })
            return None
    
    def format_entry_json(self, entry: DictionaryEntry, indent: int = 2) -> str:
        """
        Format a dictionary entry as JSON.
        
        Args:
            entry: The dictionary entry to format
            indent: Number of spaces for indentation
            
        Returns:
            Formatted JSON string
        """
        try:
            return json.dumps(entry, indent=indent, ensure_ascii=False)
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:formatting', {
                    'message': f'Error formatting entry as JSON: {str(e)}'
                })
            return str(entry)
    
    def clear_cache(self) -> None:
        """Clear the entry cache."""
        self.cached_entries.clear()
        self.cache_access_order.clear()
    
    def _validate_entry(self, entry: DictionaryEntry) -> bool:
        """
        Validate the structure of a dictionary entry.
        
        Args:
            entry: The entry to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check required top-level fields
        required_fields = ['headword', 'metadata', 'meanings']
        for field in required_fields:
            if field not in entry:
                return False
        
        # Check metadata
        metadata = entry.get('metadata', {})
        required_metadata = ['source_language', 'target_language', 'definition_language']
        for field in required_metadata:
            if field not in metadata:
                return False
        
        # Check at least one meaning
        meanings = entry.get('meanings', [])
        if not meanings or not isinstance(meanings, list):
            return False
        
        # Check meaning structure
        for meaning in meanings:
            if 'definition' not in meaning:
                return False
        
        return True
        
    def is_valid_entry(self, entry: DictionaryEntry) -> bool:
        """
        Check if an entry has a valid structure.
        
        Args:
            entry: The entry to validate
            
        Returns:
            True if the entry has a valid structure, False otherwise
        """
        return self._validate_entry(entry)
    
    def _get_cache_key(
        self, 
        headword: str, 
        target_lang: Optional[str] = None,
        source_lang: Optional[str] = None,
        definition_lang: Optional[str] = None
    ) -> str:
        """
        Generate a cache key for an entry.
        
        Args:
            headword: The headword
            target_lang: Target language
            source_lang: Source language
            definition_lang: Definition language
            
        Returns:
            String cache key
        """
        key_parts = [headword.lower()]
        
        if target_lang:
            key_parts.append(f"t:{normalize_language_name(target_lang)}")
        if source_lang:
            key_parts.append(f"s:{normalize_language_name(source_lang)}")
        if definition_lang:
            key_parts.append(f"d:{normalize_language_name(definition_lang)}")
            
        return "|".join(key_parts)
    
    def _cache_entry(self, cache_key: str, entry: DictionaryEntry) -> None:
        """
        Add an entry to the cache with LRU eviction.
        
        Args:
            cache_key: The cache key for the entry
            entry: The dictionary entry to cache
        """
        # If cache is full, remove least recently used entry
        if len(self.cached_entries) >= self.max_cache_size and self.cache_access_order:
            lru_key = self.cache_access_order.pop(0)
            if lru_key in self.cached_entries:
                del self.cached_entries[lru_key]
        
        # Add new entry to cache
        self.cached_entries[cache_key] = entry
        self.cache_access_order.append(cache_key)
    
    def _update_cache_access(self, cache_key: str) -> None:
        """
        Update the access time for a cached entry.
        
        Args:
            cache_key: The cache key to update
        """
        if cache_key in self.cache_access_order:
            self.cache_access_order.remove(cache_key)
            self.cache_access_order.append(cache_key)