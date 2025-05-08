"""
Tests for the Logger utility.

This module contains tests for the Logger class, which provides
a centralized logging system for the application.
"""

import pytest
import os
import logging
import tempfile
from pathlib import Path
from src.utils.logger import Logger, TRACE, app_logger
from src.utils.logger import debug, info, warning, error, trace, critical, exception

class TestLogger:
    """Tests for the Logger class."""
    
    def test_initialization(self):
        """Test that the Logger initializes correctly."""
        # Create a temporary log directory
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = Logger(name="test_logger", log_dir=temp_dir)
            
            # Check that the logger was initialized correctly
            assert logger.name == "test_logger"
            assert logger.log_dir == Path(temp_dir)
            assert logger.console_level == logging.INFO
            assert logger.file_level == logging.DEBUG
            assert logger.root_logger is not None
            
            # Check that the log directory was created
            assert os.path.exists(temp_dir)
            
            # Check that the handlers were created
            assert 'console' in logger.handlers
            assert 'file' in logger.handlers
            
            # Check that the loggers dictionary is empty
            assert logger.loggers == {}
    
    def test_get_logger(self):
        """Test getting a logger for a specific module."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = Logger(name="test_logger", log_dir=temp_dir)
            
            # Get a logger for a module
            module_logger = logger.get_logger("test_module")
            
            # Check that the logger was created
            assert "test_module" in logger.loggers
            assert logger.loggers["test_module"] == module_logger
            assert module_logger.name == "test_logger.test_module"
            
            # Get the same logger again
            module_logger2 = logger.get_logger("test_module")
            
            # Check that the same logger was returned
            assert module_logger2 is module_logger
    
    def test_log_levels(self):
        """Test setting and using different log levels."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = Logger(
                name="test_logger",
                log_dir=temp_dir,
                console_level=logging.WARNING,  # Only show warnings and higher in console
                file_level=TRACE  # Log everything to file
            )
            
            # Check that the levels were set correctly
            assert logger.console_level == logging.WARNING
            assert logger.file_level == TRACE
            
            # Set new levels
            logger.set_level(logging.ERROR, 'console')
            logger.set_level(logging.DEBUG, 'file')
            
            # Check that the levels were updated
            assert logger.handlers['console'].level == logging.ERROR
            assert logger.handlers['file'].level == logging.DEBUG
            
            # Set all levels at once
            logger.set_level(logging.INFO)
            
            # Check that all levels were updated
            assert logger.handlers['console'].level == logging.INFO
            assert logger.handlers['file'].level == logging.INFO
    
    def test_log_methods(self):
        """Test different logging methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = Logger(name="test_logger", log_dir=temp_dir)
            
            # Log at different levels
            logger.trace("Trace message", "test")
            logger.debug("Debug message", "test")
            logger.info("Info message", "test")
            logger.warning("Warning message", "test")
            logger.error("Error message", "test")
            logger.critical("Critical message", "test")
            
            # Log with context
            logger.info("Message with context", "test", user="test_user", action="login")
            
            # Log with exception info
            try:
                raise ValueError("Test error")
            except ValueError:
                logger.exception("Exception message", "test")
    
    def test_context_management(self):
        """Test context management."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = Logger(name="test_logger", log_dir=temp_dir)
            
            # Set context
            logger.set_context(user="test_user", session_id="123")
            
            # Check that the context was set
            assert logger.context == {"user": "test_user", "session_id": "123"}
            
            # Log with context
            logger.info("Message with context", "test")
            
            # Update context
            logger.set_context(action="login")
            
            # Check that the context was updated
            assert logger.context == {"user": "test_user", "session_id": "123", "action": "login"}
            
            # Clear context
            logger.clear_context()
            
            # Check that the context was cleared
            assert logger.context == {}
    
    def test_configuration(self):
        """Test configuration from dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = Logger(name="test_logger", log_dir=temp_dir)
            
            # Configure from dictionary
            logger.configure({
                'console_level': 'ERROR',
                'file_level': 'DEBUG'
            })
            
            # Check that the levels were updated
            assert logger.handlers['console'].level == logging.ERROR
            assert logger.handlers['file'].level == logging.DEBUG
            
            # Test with string level names
            logger.configure({
                'console_level': 'WARNING',
                'file_level': 'TRACE'
            })
            
            # Check that the levels were updated
            assert logger.handlers['console'].level == logging.WARNING
            assert logger.handlers['file'].level == TRACE
    
    def test_parse_level(self):
        """Test parsing log levels from strings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = Logger(name="test_logger", log_dir=temp_dir)
            
            # Test all level names
            assert logger._parse_level("TRACE") == TRACE
            assert logger._parse_level("DEBUG") == logging.DEBUG
            assert logger._parse_level("INFO") == logging.INFO
            assert logger._parse_level("WARNING") == logging.WARNING
            assert logger._parse_level("WARN") == logging.WARNING
            assert logger._parse_level("ERROR") == logging.ERROR
            assert logger._parse_level("CRITICAL") == logging.CRITICAL
            assert logger._parse_level("FATAL") == logging.CRITICAL
            
            # Test default for unknown level
            assert logger._parse_level("UNKNOWN") == logging.INFO
            
            # Test with integer levels
            assert logger._parse_level(TRACE) == TRACE
            assert logger._parse_level(logging.DEBUG) == logging.DEBUG
    
    def test_global_functions(self):
        """Test the global logging functions."""
        # These functions access the singleton instance, so we can't use a temporary directory
        # We'll just test that they don't raise exceptions
        
        # Test all global functions
        trace("Test trace message", "test_module")
        debug("Test debug message", "test_module")
        info("Test info message", "test_module")
        warning("Test warning message", "test_module")
        error("Test error message", "test_module")
        critical("Test critical message", "test_module")
        
        try:
            raise ValueError("Test error")
        except ValueError:
            exception("Test exception message", "test_module")