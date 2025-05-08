import sys
import traceback
from enum import Enum
from typing import Callable, Dict, Optional, Any

from . import logger

class ErrorSeverity(Enum):
    """Enumeration of error severity levels."""
    INFO = 1       # Informational messages, not errors
    WARNING = 2    # Non-critical errors that don't prevent operation
    ERROR = 3      # Errors that prevent a specific operation
    CRITICAL = 4   # Errors that may prevent the application from functioning
    FATAL = 5      # Errors that require application termination

class ErrorHandler:
    """
    Centralized error handling system for the application.
    
    This class provides a uniform way to handle errors throughout the application
    with consistent logging, user feedback, and appropriate recovery actions.
    
    Usage:
        error_handler = ErrorHandler(event_bus)
        
        # Handle an exception
        try:
            result = some_operation()
        except Exception as e:
            error_handler.handle_exception(
                e, 
                "Failed to perform operation",
                severity=ErrorSeverity.ERROR
            )
    """
    
    def __init__(self, event_bus=None):
        """
        Initialize the error handler.
        
        Args:
            event_bus: The application event bus for error notifications
        """
        self.event_bus = event_bus
        self.custom_handlers: Dict[str, Callable] = {}
    
    def handle_exception(
        self, 
        exception: Exception, 
        user_message: str = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Dict[str, Any] = None,
        notify_user: bool = True
    ) -> None:
        """
        Handle an exception with appropriate logging and notifications.
        
        Args:
            exception: The exception to handle
            user_message: A user-friendly message about the error
            severity: The severity level of the error
            context: Additional context information about the error
            notify_user: Whether to notify the user about the error
        """
        error_type = type(exception).__name__
        error_message = str(exception)
        
        # Create detailed log message
        log_message = f"{error_type}: {error_message}"
        
        # Extract context for logging
        context_dict = context or {}
        
        # Add exception details to context
        context_dict['error_type'] = error_type
        
        # Log with appropriate level and context
        if severity == ErrorSeverity.WARNING:
            logger.warning(log_message, "errors", exc_info=exception, **context_dict)
        elif severity == ErrorSeverity.ERROR:
            logger.error(log_message, "errors", exc_info=exception, **context_dict)
        elif severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, "errors", exc_info=exception, **context_dict)
        elif severity == ErrorSeverity.FATAL:
            logger.critical(f"FATAL: {log_message}", "errors", exc_info=exception, **context_dict)
        else:
            logger.info(log_message, "errors", **context_dict)
        
        # Notify through event bus if available
        if self.event_bus and notify_user:
            error_data = {
                "type": error_type,
                "message": user_message or error_message,
                "severity": severity.name,
                "details": error_message,
                "context": context
            }
            
            self.event_bus.publish("error:occurred", error_data)
            
        # Check for custom handlers
        if error_type in self.custom_handlers:
            try:
                self.custom_handlers[error_type](exception, context)
            except Exception as handler_error:
                self.logger.error(f"Error in custom handler: {str(handler_error)}")
        
        # Exit application on fatal errors
        if severity == ErrorSeverity.FATAL:
            print("A fatal error occurred. See log for details.")
            sys.exit(1)
    
    def register_handler(self, error_type: str, handler: Callable) -> None:
        """
        Register a custom handler for a specific error type.
        
        Args:
            error_type: The name of the exception class to handle
            handler: Function that takes (exception, context) parameters
        """
        self.custom_handlers[error_type] = handler
    
    def log_error(
        self, 
        message: str, 
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Dict[str, Any] = None,
        notify_user: bool = True
    ) -> None:
        """
        Log an error without an exception.
        
        Args:
            message: The error message
            severity: The severity level of the error
            context: Additional context information
            notify_user: Whether to notify the user
        """
        # Extract context for logging
        context_dict = context or {}
        
        # Log with appropriate level and context
        if severity == ErrorSeverity.WARNING:
            logger.warning(message, "errors", **context_dict)
        elif severity == ErrorSeverity.ERROR:
            logger.error(message, "errors", **context_dict)
        elif severity == ErrorSeverity.CRITICAL or severity == ErrorSeverity.FATAL:
            logger.critical(message, "errors", **context_dict)
        else:
            logger.info(message, "errors", **context_dict)
            
        # Notify through event bus if available
        if self.event_bus and notify_user:
            error_data = {
                "type": "Application",
                "message": message,
                "severity": severity.name,
                "details": message,
                "context": context
            }
            
            self.event_bus.publish("error:occurred", error_data)
            
        # Exit application on fatal errors
        if severity == ErrorSeverity.FATAL:
            print("A fatal error occurred. See log for details.")
            sys.exit(1)