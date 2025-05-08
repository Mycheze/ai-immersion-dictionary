"""
Utility modules for the DeepDict application.

This package contains utility classes and functions used throughout the application:
- event_bus: Centralized event system for component communication
- error_handler: Unified error handling and reporting
- type_definitions: TypedDict and type aliases for type annotations
- text_processing: Text manipulation and processing utilities
"""

from .event_bus import EventBus
from .error_handler import ErrorHandler, ErrorSeverity
from .text_processing import (
    strip_punctuation,
    normalize_language_name,
    extract_words,
    highlight_substring,
    truncate_text,
    clean_json_content,
    format_error_message,
    get_word_context
)

__all__ = [
    'EventBus',
    'ErrorHandler',
    'ErrorSeverity',
    'strip_punctuation',
    'normalize_language_name',
    'extract_words',
    'highlight_substring',
    'truncate_text',
    'clean_json_content',
    'format_error_message',
    'get_word_context'
]