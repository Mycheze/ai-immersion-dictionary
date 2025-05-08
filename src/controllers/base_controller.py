"""
Base Controller

This module provides a base controller class that all specific controllers
will inherit from, establishing common functionality and interfaces.
"""

from typing import Dict, Any, Optional, Callable

from src.utils import logger

class BaseController:
    """
    Base class for all controllers in the application.
    
    This class provides common functionality for controllers, including
    event handling and model-view communication.
    
    Attributes:
        models: Dictionary of models accessible to the controller
        views: Dictionary of views accessible to the controller
        event_bus: Event system for controller-related notifications
    """
    
    def __init__(self, models=None, views=None, event_bus=None):
        """
        Initialize the base controller.
        
        Args:
            models: Dictionary of models accessible to the controller
            views: Dictionary of views accessible to the controller
            event_bus: Event system for controller-related notifications
        """
        self.models = models or {}
        self.views = views or {}
        self.event_bus = event_bus
        self.event_handlers = {}
        
        # Get controller name from class name
        self.controller_name = self.__class__.__name__
        self.log_module = self.controller_name.lower().replace("controller", "")
        
        # Log initialization
        logger.debug(f"Initializing {self.controller_name}", self.log_module)
        
        # Register controller event handlers
        self._register_event_handlers()
        
        # Log initialization completion
        logger.debug(f"{self.controller_name} initialized", self.log_module)
    
    def _register_event_handlers(self):
        """
        Register event handlers for the controller.
        
        This method should be overridden by subclasses to register their
        specific event handlers.
        """
        pass
    
    def register_event_handler(self, event_name: str, handler: Callable):
        """
        Register an event handler function.
        
        Args:
            event_name: Name of the event to handle
            handler: Function to call when the event occurs
        """
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
            
        if handler not in self.event_handlers[event_name]:
            self.event_handlers[event_name].append(handler)
            
            # Log handler registration
            logger.trace(f"Registered handler for event: {event_name}", self.log_module)
            
        # Subscribe to the event if event bus is available
        if self.event_bus:
            self.event_bus.subscribe(event_name, lambda data: self._dispatch_event(event_name, data))
    
    def unregister_event_handler(self, event_name: str, handler: Callable):
        """
        Unregister an event handler function.
        
        Args:
            event_name: Name of the event
            handler: Function to unregister
        """
        if event_name in self.event_handlers and handler in self.event_handlers[event_name]:
            self.event_handlers[event_name].remove(handler)
            
            # Log handler unregistration
            logger.trace(f"Unregistered handler for event: {event_name}", self.log_module)
            
            # If no more handlers for this event, unsubscribe
            if not self.event_handlers[event_name] and self.event_bus:
                self.event_bus.unsubscribe(event_name, lambda data: self._dispatch_event(event_name, data))
    
    def _dispatch_event(self, event_name: str, data: Optional[Dict[str, Any]] = None):
        """
        Dispatch an event to all registered handlers.
        
        Args:
            event_name: Name of the event
            data: Data associated with the event
        """
        if event_name in self.event_handlers:
            # Log event dispatch at trace level
            if isinstance(data, dict):
                # Make a copy to avoid modifying the original
                log_data = data.copy()
                # Truncate large values or remove binary data for logging
                for key, value in log_data.items():
                    if isinstance(value, str) and len(value) > 100:
                        log_data[key] = f"{value[:100]}... (truncated)"
                logger.trace(f"Dispatching event: {event_name}", self.log_module, **log_data)
            else:
                logger.trace(f"Dispatching event: {event_name}", self.log_module, data=str(data)[:100] if data else None)
            
            for handler in self.event_handlers[event_name]:
                try:
                    handler(data)
                except Exception as e:
                    # Use logger instead of print
                    logger.error(
                        f"Error in event handler for {event_name}: {str(e)}", 
                        self.log_module, 
                        exc_info=True
                    )
                    
                    # Notify of error if event bus exists
                    if self.event_bus:
                        self.event_bus.publish('error:controller', {
                            'message': f"Error in controller event handler: {str(e)}",
                            'event': event_name,
                            'controller': self.controller_name
                        })
    
    def get_model(self, name: str) -> Any:
        """
        Get a model by name.
        
        Args:
            name: Name of the model to get
            
        Returns:
            The model instance or None if not found
        """
        result = self.models.get(name)
        if result is None:
            logger.warning(f"Model '{name}' not found", self.log_module)
        return result
    
    def get_view(self, name: str) -> Any:
        """
        Get a view by name.
        
        Args:
            name: Name of the view to get
            
        Returns:
            The view instance or None if not found
        """
        result = self.views.get(name)
        if result is None:
            logger.warning(f"View '{name}' not found", self.log_module)
        return result
        
    def log_debug(self, message: str, **kwargs):
        """
        Log a debug message with controller context.
        
        Args:
            message: Message to log
            **kwargs: Additional context
        """
        logger.debug(message, self.log_module, **kwargs)
    
    def log_info(self, message: str, **kwargs):
        """
        Log an info message with controller context.
        
        Args:
            message: Message to log
            **kwargs: Additional context
        """
        logger.info(message, self.log_module, **kwargs)
    
    def log_warning(self, message: str, **kwargs):
        """
        Log a warning message with controller context.
        
        Args:
            message: Message to log
            **kwargs: Additional context
        """
        logger.warning(message, self.log_module, **kwargs)
    
    def log_error(self, message: str, exc_info=None, **kwargs):
        """
        Log an error message with controller context.
        
        Args:
            message: Message to log
            exc_info: Exception info
            **kwargs: Additional context
        """
        logger.error(message, self.log_module, exc_info=exc_info, **kwargs)
        
    def log_trace(self, message: str, **kwargs):
        """
        Log a trace message with controller context.
        
        Args:
            message: Message to log
            **kwargs: Additional context
        """
        logger.trace(message, self.log_module, **kwargs)