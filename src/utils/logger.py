"""
Logger

This module provides a centralized logging system for the application, supporting
multiple output destinations and log levels.
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Union, Dict, Any, List

# Create custom log levels
TRACE = 5  # More detailed than DEBUG
logging.addLevelName(TRACE, "TRACE")

# Define custom log format
DEFAULT_LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
DETAILED_LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s (%(filename)s:%(lineno)d)"

class Logger:
    """
    Centralized logger for the application.
    
    This class provides a wrapper around Python's logging module with additional
    features such as contextual logging, multiple destinations, and structured
    logging support.
    
    Attributes:
        name: Logger name
        log_dir: Directory for log files
        console_level: Log level for console output
        file_level: Log level for file output
        loggers: Dictionary of logger instances
        handlers: Dictionary of log handlers
    """
    
    def __init__(
        self,
        name: str = "deepdict",
        log_dir: Optional[Union[str, Path]] = None,
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
        max_log_files: int = 10,
        max_file_size: int = 10 * 1024 * 1024  # 10 MB
    ):
        """
        Initialize the logger.
        
        Args:
            name: Logger name
            log_dir: Directory for log files (default: app_root/logs)
            console_level: Log level for console output
            file_level: Log level for file output
            max_log_files: Maximum number of log files to keep
            max_file_size: Maximum size of each log file in bytes
        """
        self.name = name
        self.console_level = console_level
        self.file_level = file_level
        self.max_log_files = max_log_files
        self.max_file_size = max_file_size
        
        # Get application root directory
        app_root = Path(__file__).parent.parent.parent.absolute()
        
        # Set up log directory
        if log_dir is None:
            self.log_dir = app_root / "logs"
        else:
            self.log_dir = Path(log_dir) if isinstance(log_dir, str) else log_dir
            
        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Set up root logger
        self.root_logger = logging.getLogger(name)
        self.root_logger.setLevel(min(console_level, file_level))
        
        # Track loggers and handlers
        self.loggers = {}
        self.handlers = {}
        
        # Set up handlers
        self._setup_console_handler()
        self._setup_file_handler()
        
        # Store context
        self.context = {}
    
    def _setup_console_handler(self):
        """Set up console handler for logging to stdout."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.console_level)
        
        # Set formatter
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
        console_handler.setFormatter(formatter)
        
        # Add handler to root logger
        self.root_logger.addHandler(console_handler)
        
        # Store handler
        self.handlers['console'] = console_handler
    
    def _setup_file_handler(self):
        """Set up file handler for logging to a file."""
        from logging.handlers import RotatingFileHandler
        
        # Generate log file path
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = self.log_dir / f"{self.name}_{timestamp}.log"
        
        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.max_log_files
        )
        file_handler.setLevel(self.file_level)
        
        # Set formatter with detailed information
        formatter = logging.Formatter(DETAILED_LOG_FORMAT)
        file_handler.setFormatter(formatter)
        
        # Add handler to root logger
        self.root_logger.addHandler(file_handler)
        
        # Store handler
        self.handlers['file'] = file_handler
    
    def get_logger(self, module_name: str) -> logging.Logger:
        """
        Get a logger for a specific module.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Logger instance for the module
        """
        # Check if logger already exists
        if module_name in self.loggers:
            return self.loggers[module_name]
            
        # Create new logger
        logger_name = f"{self.name}.{module_name}"
        logger = logging.getLogger(logger_name)
        
        # Store logger
        self.loggers[module_name] = logger
        
        return logger
    
    def set_context(self, **kwargs):
        """
        Set context values for logging.
        
        Args:
            **kwargs: Context key-value pairs
        """
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context values."""
        self.context.clear()
    
    def set_level(self, level: int, handler: Optional[str] = None):
        """
        Set log level for handlers.
        
        Args:
            level: Log level to set
            handler: Handler name ('console', 'file', or None for all)
        """
        if handler is None or handler == 'all':
            # Update all handlers
            for h in self.handlers.values():
                h.setLevel(level)
                
            # Update root logger level
            self.root_logger.setLevel(level)
            
        elif handler in self.handlers:
            # Update specific handler
            self.handlers[handler].setLevel(level)
    
    def log(self, level: int, message: str, module: Optional[str] = None, exc_info=None, **kwargs):
        """
        Log a message at the specified level.
        
        Args:
            level: Log level
            message: Log message
            module: Module name (uses root logger if None)
            exc_info: Exception info to include
            **kwargs: Additional context for this log entry
        """
        # Get logger
        logger = self.root_logger if module is None else self.get_logger(module)
        
        # Combine context
        context = {**self.context, **kwargs}
        
        # Format message with context if present
        if context:
            context_str = ", ".join(f"{k}={v!r}" for k, v in context.items())
            full_message = f"{message} [{context_str}]"
        else:
            full_message = message
            
        # Log the message
        logger.log(level, full_message, exc_info=exc_info)
    
    def trace(self, message: str, module: Optional[str] = None, **kwargs):
        """
        Log a message at TRACE level.
        
        Args:
            message: Log message
            module: Module name
            **kwargs: Additional context
        """
        self.log(TRACE, message, module, **kwargs)
    
    def debug(self, message: str, module: Optional[str] = None, **kwargs):
        """
        Log a message at DEBUG level.
        
        Args:
            message: Log message
            module: Module name
            **kwargs: Additional context
        """
        self.log(logging.DEBUG, message, module, **kwargs)
    
    def info(self, message: str, module: Optional[str] = None, **kwargs):
        """
        Log a message at INFO level.
        
        Args:
            message: Log message
            module: Module name
            **kwargs: Additional context
        """
        self.log(logging.INFO, message, module, **kwargs)
    
    def warning(self, message: str, module: Optional[str] = None, **kwargs):
        """
        Log a message at WARNING level.
        
        Args:
            message: Log message
            module: Module name
            **kwargs: Additional context
        """
        self.log(logging.WARNING, message, module, **kwargs)
    
    def error(self, message: str, module: Optional[str] = None, exc_info=None, **kwargs):
        """
        Log a message at ERROR level.
        
        Args:
            message: Log message
            module: Module name
            exc_info: Exception info to include
            **kwargs: Additional context
        """
        self.log(logging.ERROR, message, module, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, module: Optional[str] = None, exc_info=None, **kwargs):
        """
        Log a message at CRITICAL level.
        
        Args:
            message: Log message
            module: Module name
            exc_info: Exception info to include
            **kwargs: Additional context
        """
        self.log(logging.CRITICAL, message, module, exc_info=exc_info, **kwargs)
    
    def exception(self, message: str, module: Optional[str] = None, **kwargs):
        """
        Log a message at ERROR level with exception info.
        
        Args:
            message: Log message
            module: Module name
            **kwargs: Additional context
        """
        self.log(logging.ERROR, message, module, exc_info=True, **kwargs)
    
    def configure(self, config: Dict[str, Any]):
        """
        Configure the logger from a dictionary.
        
        Args:
            config: Configuration dictionary
        """
        # Configure console level
        if 'console_level' in config:
            level = self._parse_level(config['console_level'])
            self.set_level(level, 'console')
            
        # Configure file level
        if 'file_level' in config:
            level = self._parse_level(config['file_level'])
            self.set_level(level, 'file')
    
    def _parse_level(self, level: Union[int, str]) -> int:
        """
        Parse log level from string or int.
        
        Args:
            level: Log level as string or int
            
        Returns:
            Integer log level
        """
        if isinstance(level, int):
            return level
            
        level_upper = level.upper()
        
        if level_upper == 'TRACE':
            return TRACE
        elif level_upper == 'DEBUG':
            return logging.DEBUG
        elif level_upper == 'INFO':
            return logging.INFO
        elif level_upper == 'WARNING' or level_upper == 'WARN':
            return logging.WARNING
        elif level_upper == 'ERROR':
            return logging.ERROR
        elif level_upper == 'CRITICAL' or level_upper == 'FATAL':
            return logging.CRITICAL
        else:
            # Default to INFO
            return logging.INFO
    
    def cleanup_old_logs(self, max_age_days: int = 30):
        """
        Clean up old log files.
        
        Args:
            max_age_days: Maximum age of log files in days
        """
        now = datetime.now()
        
        for log_file in self.log_dir.glob(f"{self.name}_*.log*"):
            file_stat = log_file.stat()
            file_age = datetime.fromtimestamp(file_stat.st_mtime)
            age_days = (now - file_age).days
            
            if age_days > max_age_days:
                try:
                    log_file.unlink()
                    self.info(f"Removed old log file: {log_file.name}", "logger")
                except Exception as e:
                    self.error(f"Error removing old log file: {str(e)}", "logger")


# Create singleton instance
app_logger = Logger()

# Utility functions to access the singleton

def get_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a module.
    
    Args:
        module_name: Name of the module
        
    Returns:
        Logger for the module
    """
    return app_logger.get_logger(module_name)

def trace(message: str, module: Optional[str] = None, **kwargs):
    """Log a TRACE message."""
    app_logger.trace(message, module, **kwargs)

def debug(message: str, module: Optional[str] = None, **kwargs):
    """Log a DEBUG message."""
    app_logger.debug(message, module, **kwargs)

def info(message: str, module: Optional[str] = None, **kwargs):
    """Log an INFO message."""
    app_logger.info(message, module, **kwargs)

def warning(message: str, module: Optional[str] = None, **kwargs):
    """Log a WARNING message."""
    app_logger.warning(message, module, **kwargs)

def error(message: str, module: Optional[str] = None, exc_info=None, **kwargs):
    """Log an ERROR message."""
    app_logger.error(message, module, exc_info=exc_info, **kwargs)

def critical(message: str, module: Optional[str] = None, exc_info=None, **kwargs):
    """Log a CRITICAL message."""
    app_logger.critical(message, module, exc_info=exc_info, **kwargs)

def exception(message: str, module: Optional[str] = None, **kwargs):
    """Log an exception."""
    app_logger.exception(message, module, **kwargs)

def set_context(**kwargs):
    """Set logging context."""
    app_logger.set_context(**kwargs)

def clear_context():
    """Clear logging context."""
    app_logger.clear_context()

def configure(config: Dict[str, Any]):
    """Configure the logger."""
    app_logger.configure(config)

def cleanup_old_logs(max_age_days: int = 30):
    """Clean up old log files."""
    app_logger.cleanup_old_logs(max_age_days)


# Monkey patch for TRACE level
def _trace(self, message, *args, **kws):
    """Log TRACE level message."""
    self.log(TRACE, message, *args, **kws)

logging.Logger.trace = _trace