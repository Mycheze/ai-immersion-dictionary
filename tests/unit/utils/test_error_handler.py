"""
Tests for the ErrorHandler utility.

This module contains tests for the ErrorHandler class, which provides
centralized error handling for the application.
"""

import pytest
import logging
from unittest.mock import MagicMock, patch
from src.utils.error_handler import ErrorHandler, ErrorSeverity

class TestErrorHandler:
    """Tests for the ErrorHandler class."""
    
    def test_initialization(self, event_bus):
        """Test that the ErrorHandler initializes correctly."""
        handler = ErrorHandler(event_bus)
        assert handler.event_bus == event_bus
        assert isinstance(handler.logger, logging.Logger)
        assert handler.custom_handlers == {}
    
    def test_handle_exception(self, event_bus):
        """Test handling exceptions with various severity levels."""
        # Create a mock event_bus
        mock_event_bus = MagicMock()
        
        # Create the error handler
        handler = ErrorHandler(mock_event_bus)
        
        # Create a test exception
        test_exception = ValueError("Test error")
        
        # Handle with INFO severity
        handler.handle_exception(
            test_exception,
            user_message="Test info message",
            severity=ErrorSeverity.INFO
        )
        
        # Check that the event bus was called
        mock_event_bus.publish.assert_called_with(
            'error:occurred',
            {
                'type': 'ValueError',
                'message': 'Test info message',
                'severity': 'INFO',
                'details': 'Test error',
                'context': None
            }
        )
        
        # Reset the mock
        mock_event_bus.reset_mock()
        
        # Handle with ERROR severity
        handler.handle_exception(
            test_exception,
            user_message="Test error message",
            severity=ErrorSeverity.ERROR,
            context={'test': 'context'}
        )
        
        # Check that the event bus was called with the correct data
        mock_event_bus.publish.assert_called_with(
            'error:occurred',
            {
                'type': 'ValueError',
                'message': 'Test error message',
                'severity': 'ERROR',
                'details': 'Test error',
                'context': {'test': 'context'}
            }
        )
    
    def test_custom_error_handler(self, event_bus):
        """Test registering and using custom error handlers."""
        handler = ErrorHandler(event_bus)
        
        # Create a mock custom handler
        custom_handler = MagicMock()
        
        # Register the custom handler
        handler.register_handler('ValueError', custom_handler)
        
        # Handle a ValueError
        test_exception = ValueError("Test error")
        test_context = {'test': 'context'}
        
        handler.handle_exception(
            test_exception,
            context=test_context
        )
        
        # Check that the custom handler was called
        custom_handler.assert_called_with(test_exception, test_context)
    
    @patch('sys.exit')
    def test_fatal_error(self, mock_exit, event_bus):
        """Test handling fatal errors."""
        handler = ErrorHandler(event_bus)
        
        # Handle a fatal error
        test_exception = RuntimeError("Fatal error")
        
        handler.handle_exception(
            test_exception,
            user_message="Fatal error occurred",
            severity=ErrorSeverity.FATAL
        )
        
        # Check that sys.exit was called
        mock_exit.assert_called_with(1)
    
    def test_log_error(self, event_bus):
        """Test logging errors without exceptions."""
        # Create a mock event_bus
        mock_event_bus = MagicMock()
        
        # Create the error handler
        handler = ErrorHandler(mock_event_bus)
        
        # Log an error
        handler.log_error(
            "Test error message",
            severity=ErrorSeverity.WARNING,
            context={'test': 'context'}
        )
        
        # Check that the event bus was called
        mock_event_bus.publish.assert_called_with(
            'error:occurred',
            {
                'type': 'Application',
                'message': 'Test error message',
                'severity': 'WARNING',
                'details': 'Test error message',
                'context': {'test': 'context'}
            }
        )
    
    @patch('sys.exit')
    def test_log_fatal_error(self, mock_exit, event_bus):
        """Test logging fatal errors."""
        handler = ErrorHandler(event_bus)
        
        # Log a fatal error
        handler.log_error(
            "Fatal error message",
            severity=ErrorSeverity.FATAL
        )
        
        # Check that sys.exit was called
        mock_exit.assert_called_with(1)
    
    def test_error_handler_no_event_bus(self):
        """Test ErrorHandler behavior without an event bus."""
        handler = ErrorHandler(None)
        
        # Handle an exception without an event bus
        test_exception = ValueError("Test error")
        
        # This should not raise any errors
        handler.handle_exception(test_exception)
    
    def test_error_handler_failing_custom_handler(self, event_bus):
        """Test behavior when a custom handler raises an exception."""
        handler = ErrorHandler(event_bus)
        
        # Create a custom handler that raises an exception
        def failing_handler(exception, context):
            raise RuntimeError("Handler error")
        
        # Register the custom handler
        handler.register_handler('ValueError', failing_handler)
        
        # Handle a ValueError
        test_exception = ValueError("Test error")
        
        # This should not raise an error
        handler.handle_exception(test_exception)
        
        # We just verify that the code completes without raising an exception