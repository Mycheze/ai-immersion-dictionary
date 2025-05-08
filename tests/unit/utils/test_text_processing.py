"""
Tests for the text_processing utility functions.

This module contains tests for the text processing utility functions used
throughout the application.
"""

import pytest
from src.utils.text_processing import (
    strip_punctuation,
    normalize_language_name,
    extract_words,
    highlight_substring,
    truncate_text,
    clean_json_content,
    format_error_message,
    get_word_context
)

class TestTextProcessing:
    """Tests for the text processing utility functions."""
    
    def test_strip_punctuation(self):
        """Test stripping leading and trailing punctuation."""
        # Test with leading punctuation
        assert strip_punctuation("!Hello") == "Hello"
        
        # Test with trailing punctuation
        assert strip_punctuation("Hello!") == "Hello"
        
        # Test with both leading and trailing punctuation
        assert strip_punctuation("!Hello!") == "Hello"
        
        # Test with multiple punctuation marks
        assert strip_punctuation("!!!Hello!!!") == "Hello"
        
        # Test with internal punctuation (should be preserved)
        assert strip_punctuation("Hello, World!") == "Hello, World"
        
        # Test with internal hyphens (should be preserved)
        assert strip_punctuation("!Hello-World!") == "Hello-World"
        
        # Test with only punctuation
        assert strip_punctuation("!!!") == ""
        
        # Test with empty string
        assert strip_punctuation("") == ""
    
    def test_normalize_language_name(self):
        """Test normalizing language names."""
        # Test with extra spaces
        assert normalize_language_name("  English  ") == "english"
        
        # Test with mixed case
        assert normalize_language_name("CzEcH") == "czech"
        
        # Test with multiple spaces
        assert normalize_language_name("American  English") == "american english"
        
        # Test with empty string
        assert normalize_language_name("") == ""
    
    def test_extract_words(self):
        """Test extracting words from text."""
        # Test with simple text
        assert extract_words("Hello World") == ["Hello", "World"]
        
        # Test with extra spaces
        assert extract_words("  Hello   World  ") == ["Hello", "World"]
        
        # Test with punctuation (preserved)
        assert extract_words("Hello, World!") == ["Hello,", "World!"]
        
        # Test with empty string
        assert extract_words("") == []
        
        # Test with just spaces
        assert extract_words("   ") == []
    
    def test_highlight_substring(self):
        """Test highlighting substrings."""
        # Test with matching substring
        assert highlight_substring("Hello World", "Hello") == '<span class="highlight">Hello</span> World'
        
        # Test with non-matching substring
        assert highlight_substring("Hello World", "Goodbye") == "Hello World"
        
        # Test with empty substring
        assert highlight_substring("Hello World", "") == "Hello World"
        
        # Test with empty text
        assert highlight_substring("", "Hello") == ""
        
        # Test with multiple occurrences
        assert highlight_substring("Hello Hello", "Hello") == '<span class="highlight">Hello</span> <span class="highlight">Hello</span>'
    
    def test_truncate_text(self):
        """Test truncating text."""
        # Test with text shorter than max length
        assert truncate_text("Hello", 10) == "Hello"
        
        # Test with text equal to max length
        assert truncate_text("Hello", 5) == "Hello"
        
        # Test with text longer than max length
        assert truncate_text("Hello World", 5) == "Hello..."
        
        # Test with custom ellipsis
        assert truncate_text("Hello World", 5, ellipsis="...more") == "Hello...more"
        
        # Test with word boundary truncation
        assert truncate_text("Hello beautiful World", 10) == "Hello..."
        
        # Test with empty text
        assert truncate_text("", 10) == ""
    
    def test_clean_json_content(self):
        """Test cleaning JSON content."""
        # Test with JSON code block
        assert clean_json_content("```json\n{\"key\": \"value\"}\n```") == "{\"key\": \"value\"}"
        
        # Test with plain code block
        assert clean_json_content("```\n{\"key\": \"value\"}\n```") == "{\"key\": \"value\"}"
        
        # Test with no code block
        assert clean_json_content("{\"key\": \"value\"}") == "{\"key\": \"value\"}"
        
        # Test with leading/trailing whitespace
        assert clean_json_content("  {\"key\": \"value\"}  ") == "{\"key\": \"value\"}"
        
        # Test with empty string
        assert clean_json_content("") == ""
    
    def test_format_error_message(self):
        """Test formatting error messages."""
        # Test with ValueError
        error = ValueError("Invalid value")
        assert format_error_message(error, user_friendly=True) == "An error occurred: Invalid value"
        assert format_error_message(error, user_friendly=False) == "ValueError: Invalid value"
        
        # Test with connection error
        error = Exception("Connection timeout")
        assert format_error_message(error, user_friendly=True) == "Connection error. Please check your internet connection and try again."
        
        # Test with API key error
        error = Exception("Invalid API key")
        assert format_error_message(error, user_friendly=True) == "API authentication error. Please check your API key."
        
        # Test with permission error
        error = Exception("Access denied")
        assert format_error_message(error, user_friendly=True) == "Permission denied. You don't have access to this resource."
    
    def test_get_word_context(self):
        """Test getting word context."""
        text = "The quick brown fox jumps over the lazy dog"
        
        # Test with word in the middle
        assert get_word_context(text, "brown", context_size=1) == "quick brown fox"
        
        # Test with word at the beginning
        assert get_word_context(text, "The", context_size=2) == "The quick brown"
        
        # Test with word at the end
        assert get_word_context(text, "dog", context_size=2) == "the lazy dog"
        
        # Test with word not in text
        assert get_word_context(text, "cat", context_size=2) == "cat"
        
        # Test with case insensitivity
        assert get_word_context(text, "BROWN", context_size=1) == "quick brown fox"
        
        # Test with partial word match
        assert get_word_context(text, "bro", context_size=1) == "quick brown fox"
        
        # Test with empty text
        assert get_word_context("", "word", context_size=2) == "word"
        
        # Test with empty word
        assert get_word_context(text, "", context_size=2) == ""