"""
Log Handler

This module provides integration between the event bus system and the logger,
automatically logging events to appropriate log levels.
"""

from typing import Dict, Any, Optional

from . import logger
from .event_bus import EventBus

class LogHandler:
    """
    Handler for integrating the event bus with the logger.
    
    This class subscribes to events on the event bus and logs them
    with appropriate log levels.
    
    Attributes:
        event_bus: Event bus to subscribe to
        module_map: Map of event types to module names
        level_map: Map of event types to log levels
    """
    
    def __init__(self, event_bus: EventBus):
        """
        Initialize the log handler.
        
        Args:
            event_bus: Event bus to subscribe to
        """
        self.event_bus = event_bus
        
        # Map event types to modules for better organization
        self.module_map = {
            'database': 'database',
            'api': 'api',
            'request': 'requests',
            'anki': 'anki',
            'error': 'errors',
            'ui': 'ui',
            'window': 'ui',
            'settings': 'settings',
            'theme': 'ui.theme',
            'search': 'search',
            'entry': 'entries',
            'task': 'async',
            'async': 'async',
            'cache': 'cache',
            'prompt': 'prompts',
            'language': 'language'
        }
        
        # Map event types to log levels
        # Events are categorized as module:event_type
        # Example: 'database:initialized', 'error:api'
        self.level_map = {
            # Error events (always logged as errors)
            'error:': logger.ERROR,
            
            # Informational events (INFO level)
            'database:initialized': logger.INFO,
            'database:entry_added': logger.INFO,
            'database:entry_deleted': logger.INFO,
            'database:cache_cleared': logger.INFO,
            
            # Detailed events (DEBUG level)
            'database:connection_created': logger.DEBUG,
            'database:connection_replaced': logger.DEBUG,
            'database:restoring_data': logger.DEBUG,
            
            # API events
            'api:call_started': logger.INFO,
            'api:call_completed': logger.INFO,
            'api:cache_hit': logger.DEBUG,
            'api:retry': logger.WARNING,
            
            # Request events
            'request:created': logger.DEBUG,
            'request:cancelled': logger.INFO,
            'request:all_cancelled': logger.INFO,
            'request_queue:status_changed': logger.DEBUG,
            
            # Async/task events
            'task:submitted': logger.DEBUG,
            'task:started': logger.DEBUG,
            'task:completed': logger.DEBUG,
            'task:failed': logger.WARNING,
            'task:cancelled': logger.INFO,
            'task:progress': logger.DEBUG,
            'tasks:cleared': logger.DEBUG,
            'tasks:auto_cleared': logger.DEBUG,
            'async:workers_started': logger.INFO,
            'async:worker_error': logger.ERROR,
            'async:shutdown': logger.INFO,
            
            # UI events
            'ui:scale_factor_changed': logger.DEBUG,
            'window:closing': logger.INFO,
            'view:added': logger.DEBUG,
            'view:removed': logger.DEBUG,
            
            # Settings events
            'settings:changed': logger.INFO,
            'settings:loaded': logger.INFO,
            'settings:saved': logger.INFO,
            
            # Anki events
            'anki:connected': logger.INFO,
            'anki:disconnected': logger.INFO,
            'anki:card_added': logger.INFO,
            
            # Search events
            'search:requested': logger.DEBUG,
            'search:filter_updated': logger.DEBUG,
            'search:completed': logger.DEBUG,
            
            # Entry events
            'entry:saved': logger.INFO,
            'entry:retrieved': logger.DEBUG,
            
            # Cache events
            'cache:cleared': logger.INFO,
        }
        
        # Subscribe to all events
        self.event_bus.subscribe_all(self._on_event)
    
    def _on_event(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        """
        Handle an event by logging it.
        
        Args:
            event_type: Type of the event
            data: Event data
        """
        # Determine log level
        log_level = self._get_log_level(event_type)
        
        # Determine module
        module = self._get_module(event_type)
        
        # Prepare log message
        if data:
            # Extract message from data if present
            message = data.get('message', f"Event: {event_type}")
            
            # Make a copy of data without the message
            log_data = data.copy()
            if 'message' in log_data:
                del log_data['message']
        else:
            # No data, just log the event type
            message = f"Event: {event_type}"
            log_data = {}
        
        # Log the event
        logger.log(log_level, message, module, **log_data)
    
    def _get_log_level(self, event_type: str) -> int:
        """
        Determine the log level for an event.
        
        Args:
            event_type: Type of the event
            
        Returns:
            Log level for the event
        """
        # Check for exact match
        if event_type in self.level_map:
            return self.level_map[event_type]
        
        # Check for prefix match
        for prefix, level in self.level_map.items():
            if event_type.startswith(prefix):
                return level
        
        # Default to INFO level
        return logger.INFO
    
    def _get_module(self, event_type: str) -> str:
        """
        Determine the module for an event.
        
        Args:
            event_type: Type of the event
            
        Returns:
            Module name for the event
        """
        # Extract the module part from the event type
        parts = event_type.split(':')
        if len(parts) > 1:
            module_prefix = parts[0]
            
            # Check if we have a mapping for this module
            if module_prefix in self.module_map:
                return self.module_map[module_prefix]
        
        # Default to 'events' module
        return 'events'


# Easy way to create a log handler for an event bus
def create_log_handler(event_bus: EventBus) -> LogHandler:
    """
    Create a log handler for an event bus.
    
    Args:
        event_bus: Event bus to subscribe to
        
    Returns:
        Log handler instance
    """
    return LogHandler(event_bus)