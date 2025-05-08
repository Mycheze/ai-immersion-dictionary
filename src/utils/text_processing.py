"""
Text processing utilities for the dictionary application.

This module provides functions for working with text, including validation,
normalization, and common text operations used throughout the application.
"""

import re
import string
from typing import List, Optional, Dict, Any

def strip_punctuation(text: str) -> str:
    """
    Remove leading and trailing punctuation from a string.
    
    This preserves internal spaces, hyphens, and other punctuation that might
    be part of a multi-word expression.
    
    Args:
        text: The input text to process
        
    Returns:
        The text with leading and trailing punctuation removed
    """
    return re.sub(r'^[^\w\s-]+|[^\w\s-]+$', '', text)

def normalize_language_name(name: str) -> str:
    """
    Normalize a language name for consistent comparison.
    
    Args:
        name: The language name to normalize
        
    Returns:
        Normalized language name (lowercase, no extra spaces)
    """
    # Strip whitespace and convert to lowercase
    normalized = name.strip().lower()
    
    # Replace multiple spaces with a single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Return the normalized language name
    return normalized

def extract_words(text: str) -> List[str]:
    """
    Extract a list of words from a text string.
    
    Args:
        text: The input text
        
    Returns:
        List of individual words
    """
    # Split by whitespace and filter out empty strings
    return [word for word in re.split(r'\s+', text) if word]

def highlight_substring(text: str, substring: str) -> str:
    """
    Create a version of text with the substring highlighted with HTML tags.
    
    Args:
        text: The original text
        substring: The substring to highlight
        
    Returns:
        Text with HTML highlighting tags
    """
    if not substring or substring not in text:
        return text
        
    return text.replace(substring, f'<span class="highlight">{substring}</span>')

def truncate_text(text: str, max_length: int, ellipsis: str = '...') -> str:
    """
    Truncate text to a maximum length with an ellipsis.
    
    Args:
        text: The text to truncate
        max_length: Maximum allowed length
        ellipsis: String to append to truncated text
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
        
    # Ensure we don't cut words in the middle
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length // 2:  # Only truncate at word boundary if reasonable
        truncated = truncated[:last_space]
        
    return truncated + ellipsis

def clean_json_content(json_text: str) -> str:
    """
    Clean JSON content received from API responses.
    
    Removes markdown code blocks and other unwanted formatting that might
    interfere with JSON parsing.
    
    Args:
        json_text: The JSON text to clean
        
    Returns:
        Cleaned JSON string
    """
    # Remove opening markdown code block markers
    cleaned = re.sub(r'^\s*```(json)?\s*$', '', json_text, flags=re.MULTILINE)
    
    # Remove closing markdown code block markers
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
    
    # Trim whitespace
    cleaned = cleaned.strip()
    
    return cleaned

def format_error_message(error: Exception, user_friendly: bool = True) -> str:
    """
    Format an exception into a user-friendly or detailed error message.
    
    Args:
        error: The exception to format
        user_friendly: Whether to return a simplified user-friendly message
        
    Returns:
        Formatted error message
    """
    error_type = type(error).__name__
    error_message = str(error)
    
    if user_friendly:
        # Create a simplified message for users
        if 'connection' in error_message.lower() or 'timeout' in error_message.lower():
            return "Connection error. Please check your internet connection and try again."
        elif 'api key' in error_message.lower() or 'authentication' in error_message.lower():
            return "API authentication error. Please check your API key."
        elif 'permission' in error_message.lower() or 'access' in error_message.lower():
            return "Permission denied. You don't have access to this resource."
        else:
            return f"An error occurred: {error_message}"
    else:
        # Create a detailed message for logs/debugging
        return f"{error_type}: {error_message}"

def get_word_context(text: str, word: str, context_size: int = 5) -> str:
    """
    Extract a word with surrounding context from a larger text.
    
    Args:
        text: The full text
        word: The word to extract context for
        context_size: Number of words for context before/after
        
    Returns:
        The word with surrounding context
    """
    if not word in text:
        return word
        
    words = extract_words(text)
    word_index = -1
    
    # Find the word in the list of words
    for i, w in enumerate(words):
        if w.lower() == word.lower() or w.lower().startswith(word.lower()):
            word_index = i
            break
            
    if word_index == -1:
        return word
        
    # Extract context
    start = max(0, word_index - context_size)
    end = min(len(words), word_index + context_size + 1)
    
    context_words = words[start:end]
    return ' '.join(context_words)