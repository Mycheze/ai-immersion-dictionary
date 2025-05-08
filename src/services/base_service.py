"""
Base Service

This module provides a base service class that all specific services
will inherit from, establishing common functionality and interfaces.
"""

from typing import Any, Optional, Dict

from src.utils import logger

class BaseService:
    """
    Base class for all services in the application.
    
    This class provides common functionality for services, including
    event handling and dependency management.
    
    Attributes:
        event_bus: Event system for service-related notifications
    """
    
    def __init__(self, event_bus=None):
        """
        Initialize the base service.
        
        Args:
            event_bus: Optional event bus for notifications
        """
        self.event_bus = event_bus
        
        # Get service name from class name
        self.service_name = self.__class__.__name__
        self.log_module = self.service_name.lower().replace("service", "")
        
        # Log initialization
        logger.debug(f"Initializing {self.service_name}", self.log_module)
        
        # Initialize the service
        self._initialize()
        
        # Log initialization completion
        logger.debug(f"{self.service_name} initialized", self.log_module)
    
    def _initialize(self):
        """
        Initialize the service.
        
        This method should be overridden by subclasses to perform
        service-specific initialization.
        """
        pass
    
    def publish_event(self, event_name: str, data: Optional[Any] = None):
        """
        Publish an event to the event bus.
        
        Args:
            event_name: Name of the event to publish
            data: Data to include with the event
        """
        # Log the event at trace level to avoid excessive logging
        if isinstance(data, dict):
            # Make a copy to avoid modifying the original
            log_data = data.copy()
            # Truncate large values or remove binary data for logging
            for key, value in log_data.items():
                if isinstance(value, str) and len(value) > 100:
                    log_data[key] = f"{value[:100]}... (truncated)"
            logger.trace(f"Publishing event: {event_name}", self.log_module, **log_data)
        else:
            logger.trace(f"Publishing event: {event_name}", self.log_module, data=str(data)[:100] if data else None)
        
        # Publish the event
        if self.event_bus:
            self.event_bus.publish(event_name, data)
    
    def shutdown(self):
        """
        Clean up resources and shut down the service.
        
        This method should be overridden by subclasses to perform
        service-specific cleanup.
        """
        logger.debug(f"Shutting down {self.service_name}", self.log_module)
    
    def log_debug(self, message: str, **kwargs):
        """
        Log a debug message with service context.
        
        Args:
            message: Message to log
            **kwargs: Additional context
        """
        logger.debug(message, self.log_module, **kwargs)
    
    def log_info(self, message: str, **kwargs):
        """
        Log an info message with service context.
        
        Args:
            message: Message to log
            **kwargs: Additional context
        """
        logger.info(message, self.log_module, **kwargs)
    
    def log_warning(self, message: str, **kwargs):
        """
        Log a warning message with service context.
        
        Args:
            message: Message to log
            **kwargs: Additional context
        """
        logger.warning(message, self.log_module, **kwargs)
    
    def log_error(self, message: str, exc_info=None, **kwargs):
        """
        Log an error message with service context.
        
        Args:
            message: Message to log
            exc_info: Exception info
            **kwargs: Additional context
        """
        logger.error(message, self.log_module, exc_info=exc_info, **kwargs)