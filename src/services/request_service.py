"""
Request Service

This module provides a service that manages asynchronous API requests through the
request manager, providing a clean interface for controllers to make API calls.
"""

from typing import Dict, Any, Optional, Callable, List, Union
import threading
import uuid

from src.request_manager import RequestManager
from .base_service import BaseService

class RequestService(BaseService):
    """
    Service for managing asynchronous API requests.
    
    This service wraps the request manager, providing a clean interface for
    controllers to make asynchronous API calls and handle responses.
    
    Attributes:
        request_manager: The request manager instance
        dictionary_engine: Reference to the dictionary engine
        event_bus: Event system for service-related notifications
    """
    
    def __init__(self, dictionary_engine=None, event_bus=None):
        """
        Initialize the request service.
        
        Args:
            dictionary_engine: Reference to the dictionary engine
            event_bus: Optional event bus for notifications
        """
        self.dictionary_engine = dictionary_engine
        super().__init__(event_bus)
    
    def _initialize(self):
        """Initialize the request service."""
        # Create the request manager
        self.request_manager = RequestManager(self.dictionary_engine)
        
        # Register for events
        self.request_manager.set_ui_callback(self._on_queue_status_changed)
    
    def _on_queue_status_changed(self):
        """Handle request queue status change."""
        # Get queue statistics
        stats = self.request_manager.get_queue_stats()
        
        # Publish event with queue statistics
        if self.event_bus:
            self.event_bus.publish('request_queue:status_changed', {
                'stats': stats
            })
    
    def get_lemma(self, word: str, sentence_context: Optional[str] = None, 
                  success_callback: Callable = None, error_callback: Callable = None,
                  max_retries: int = 3, retry_delay: float = 2.0) -> str:
        """
        Get the lemma form of a word.
        
        Args:
            word: The word to get the lemma for
            sentence_context: Optional context sentence
            success_callback: Function to call with result on success
            error_callback: Function to call with error on failure
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            
        Returns:
            Request ID for tracking
        """
        # Prepare request parameters
        params = {
            'word': word
        }
        
        if sentence_context:
            params['sentence_context'] = sentence_context
            
        # Add request to the queue
        request_id = self.request_manager.add_request(
            'lemma',
            params,
            success_callback or (lambda x: None),
            error_callback or (lambda x: self._default_error_handler('lemma', x)),
            max_retries=max_retries,
            retry_delay=retry_delay
        )
        
        # Notify of request creation
        if self.event_bus:
            self.event_bus.publish('request:created', {
                'request_id': request_id,
                'type': 'lemma',
                'word': word,
                'max_retries': max_retries
            })
            
        return request_id
    
    def create_entry(self, word: str, target_lang: Optional[str] = None, 
                    source_lang: Optional[str] = None, sentence_context: Optional[str] = None,
                    success_callback: Callable = None, error_callback: Callable = None,
                    max_retries: int = 3, retry_delay: float = 2.0) -> str:
        """
        Create a new dictionary entry.
        
        Args:
            word: The word to create an entry for
            target_lang: Target language
            source_lang: Source language
            sentence_context: Optional context sentence
            success_callback: Function to call with result on success
            error_callback: Function to call with error on failure
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            
        Returns:
            Request ID for tracking
        """
        # Prepare request parameters
        params = {
            'word': word
        }
        
        if target_lang:
            params['target_lang'] = target_lang
            
        if source_lang:
            params['source_lang'] = source_lang
            
        if sentence_context:
            params['sentence_context'] = sentence_context
            
        # Add request to the queue
        request_id = self.request_manager.add_request(
            'entry',
            params,
            success_callback or (lambda x: None),
            error_callback or (lambda x: self._default_error_handler('entry', x)),
            max_retries=max_retries,
            retry_delay=retry_delay
        )
        
        # Notify of request creation
        if self.event_bus:
            self.event_bus.publish('request:created', {
                'request_id': request_id,
                'type': 'entry',
                'word': word
            })
            
        return request_id
    
    def regenerate_entry(self, headword: str, target_lang: Optional[str] = None,
                        source_lang: Optional[str] = None, definition_lang: Optional[str] = None,
                        success_callback: Callable = None, error_callback: Callable = None,
                        max_retries: int = 3, retry_delay: float = 2.0) -> str:
        """
        Regenerate an existing dictionary entry.
        
        Args:
            headword: The headword to regenerate
            target_lang: Target language
            source_lang: Source language
            definition_lang: Definition language
            success_callback: Function to call with result on success
            error_callback: Function to call with error on failure
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            
        Returns:
            Request ID for tracking
        """
        # Generate a variation seed for subtle differences in regeneration
        variation_seed = str(uuid.uuid4())
        
        # Prepare request parameters
        params = {
            'headword': headword,
            'variation_seed': variation_seed
        }
        
        if target_lang:
            params['target_lang'] = target_lang
            
        if source_lang:
            params['source_lang'] = source_lang
            
        if definition_lang:
            params['definition_lang'] = definition_lang
            
        # Add request to the queue
        request_id = self.request_manager.add_request(
            'regenerate',
            params,
            success_callback or (lambda x: None),
            error_callback or (lambda x: self._default_error_handler('regenerate', x)),
            max_retries=max_retries,
            retry_delay=retry_delay
        )
        
        # Notify of request creation
        if self.event_bus:
            self.event_bus.publish('request:created', {
                'request_id': request_id,
                'type': 'regenerate',
                'headword': headword
            })
            
        return request_id
    
    def validate_language(self, language_name: str, 
                         success_callback: Callable = None, error_callback: Callable = None,
                         max_retries: int = 3, retry_delay: float = 2.0) -> str:
        """
        Validate a language name.
        
        Args:
            language_name: The language name to validate
            success_callback: Function to call with result on success
            error_callback: Function to call with error on failure
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            
        Returns:
            Request ID for tracking
        """
        # Prepare request parameters
        params = {
            'language_name': language_name
        }
        
        # Add request to the queue
        request_id = self.request_manager.add_request(
            'validate_language',
            params,
            success_callback or (lambda x: None),
            error_callback or (lambda x: self._default_error_handler('validate_language', x)),
            max_retries=max_retries,
            retry_delay=retry_delay
        )
        
        # Notify of request creation
        if self.event_bus:
            self.event_bus.publish('request:created', {
                'request_id': request_id,
                'type': 'validate_language',
                'language_name': language_name
            })
            
        return request_id
    
    def cancel_request(self, request_id: str) -> bool:
        """
        Cancel a pending request.
        
        Args:
            request_id: ID of the request to cancel
            
        Returns:
            True if the request was cancelled, False otherwise
        """
        result = self.request_manager.cancel_request(request_id)
        
        if result and self.event_bus:
            self.event_bus.publish('request:cancelled', {
                'request_id': request_id
            })
            
        return result
    
    def cancel_all_requests(self) -> int:
        """
        Cancel all pending requests.
        
        Returns:
            Number of requests cancelled
        """
        count = self.request_manager.cancel_all_requests()
        
        if count > 0 and self.event_bus:
            self.event_bus.publish('request:all_cancelled', {
                'count': count
            })
            
        return count
    
    def get_request_status(self, request_id: str) -> Optional[str]:
        """
        Get the status of a request.
        
        Args:
            request_id: ID of the request
            
        Returns:
            Status of the request or None if not found
        """
        return self.request_manager.get_request_status(request_id)
    
    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get statistics about the request queue.
        
        Returns:
            Dictionary with queue statistics
        """
        return self.request_manager.get_queue_stats()
    
    def get_active_count(self) -> int:
        """
        Get the number of active requests.
        
        Returns:
            Number of active requests
        """
        return self.request_manager.get_active_count()
    
    def get_pending_count(self) -> int:
        """
        Get the number of pending requests.
        
        Returns:
            Number of pending requests
        """
        return self.request_manager.get_pending_count()
    
    def _default_error_handler(self, request_type: str, error: str):
        """
        Default error handler for request failures.
        
        Args:
            request_type: Type of the failed request
            error: Error message
        """
        # Notify of error if event bus exists
        if self.event_bus:
            self.event_bus.publish('error:request', {
                'request_type': request_type,
                'message': error
            })
    
    def shutdown(self):
        """Clean up resources and shut down the request manager."""
        # Cancel all pending requests
        self.cancel_all_requests()
        
        # Shut down the request manager
        if self.request_manager:
            self.request_manager.shutdown()