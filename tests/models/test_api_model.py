"""
Tests for the APIModel class.

This module contains tests for the APIModel which handles API interactions
with language models.
"""

import os
import json
import tempfile
import pytest
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path

from src.models.api_model import APIModel

class TestAPIModel:
    """Tests for the APIModel class."""
    
    @pytest.fixture
    def temp_api_key_file(self):
        """Create a temporary API key file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test_api_key_12345")
        file_path = f.name
        yield file_path
        os.unlink(file_path)
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory with sample prompt templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample prompt files
            prompt_files = {
                "test_prompt.txt": "This is a test prompt with [VARIABLE].",
                "language_prompt.txt": "Language information for [TARGET_LANGUAGE] and [SOURCE_LANGUAGE]."
            }
            
            for filename, content in prompt_files.items():
                with open(os.path.join(temp_dir, filename), 'w', encoding='utf-8') as f:
                    f.write(content)
                    
            yield temp_dir
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def api_model(self, temp_api_key_file, temp_config_dir, temp_cache_dir, event_bus):
        """Create an APIModel instance with test paths."""
        return APIModel(
            api_key_path=temp_api_key_file,
            cache_dir=temp_cache_dir,
            config_dir=temp_config_dir,
            event_bus=event_bus
        )
    
    def test_init_with_api_key(self, api_model, event_bus):
        """Test initialization with valid API key."""
        assert api_model.api_key == "test_api_key_12345"
        assert api_model.client is not None
        
        # Check template loading
        assert len(api_model.prompt_templates) == 2
        assert "test_prompt" in api_model.prompt_templates
        assert "language_prompt" in api_model.prompt_templates
    
    def test_init_with_missing_api_key(self, temp_config_dir, temp_cache_dir, event_bus):
        """Test initialization with missing API key file."""
        # Setup error spy
        error_spy = MagicMock()
        event_bus.subscribe('error:api', error_spy)
        
        # Create model with non-existent API key path
        model = APIModel(
            api_key_path="/path/to/nonexistent/api_key.txt",
            cache_dir=temp_cache_dir,
            config_dir=temp_config_dir,
            event_bus=event_bus
        )
        
        # Verify API key is None and client wasn't created
        assert model.api_key is None
        assert model.client is None
        
        # Verify error was published
        assert error_spy.called
        call_args = error_spy.call_args[0][0]
        assert 'message' in call_args
        assert 'not found' in call_args['message']
    
    def test_get_prompt_template(self, api_model):
        """Test retrieving prompt templates."""
        # Test getting existing template
        template = api_model.get_prompt_template("test_prompt")
        assert template == "This is a test prompt with [VARIABLE]."
        
        # Test getting non-existent template
        template = api_model.get_prompt_template("nonexistent")
        assert template is None
    
    def test_process_prompt(self, api_model, event_bus):
        """Test processing prompt templates with variable replacement."""
        # Test with simple replacements
        replacements = {"VARIABLE": "replaced value"}
        processed = api_model.process_prompt("test_prompt", replacements)
        assert processed == "This is a test prompt with replaced value."
        
        # Test with language template
        replacements = {
            "TARGET_LANGUAGE": "Czech",
            "SOURCE_LANGUAGE": "English"
        }
        processed = api_model.process_prompt("language_prompt", replacements)
        assert processed == "Language information for Czech and English."
        
        # Test with missing variables
        error_spy = MagicMock()
        event_bus.subscribe('error:prompts', error_spy)
        
        incomplete = api_model.process_prompt("language_prompt", {"TARGET_LANGUAGE": "Czech"})
        assert incomplete is None
        assert error_spy.called
        
        # Test with additional variables
        processed = api_model.process_prompt(
            "language_prompt", 
            {"TARGET_LANGUAGE": "Czech"},
            additional_vars={"SOURCE_LANGUAGE": "German"}
        )
        assert processed == "Language information for Czech and German."
    
    @patch('openai.OpenAI')
    def test_call_api(self, mock_openai, api_model, event_bus):
        """Test API calling with mocked OpenAI client."""
        # Setup mock response
        mock_response = MagicMock()
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create.return_value = mock_response
        mock_chat.completions = mock_completions
        mock_client.chat = mock_chat
        
        # Replace client with mock
        api_model.client = mock_client
        
        # Setup event spies
        start_spy = MagicMock()
        complete_spy = MagicMock()
        event_bus.subscribe('api:call_started', start_spy)
        event_bus.subscribe('api:call_completed', complete_spy)
        
        # Test API call
        messages = [{"role": "system", "content": "Test system message"}]
        result = api_model.call_api(messages, temperature=0.5)
        
        # Verify API was called correctly
        mock_completions.create.assert_called_once()
        call_kwargs = mock_completions.create.call_args[1]
        assert call_kwargs["model"] == "deepseek-chat"
        assert call_kwargs["messages"] == messages
        assert call_kwargs["temperature"] == 0.5
        
        # Verify result is the mock response
        assert result is mock_response
        
        # Verify events were published
        assert start_spy.called
        assert complete_spy.called
    
    @patch('openai.OpenAI')
    def test_api_call_error(self, mock_openai, api_model, event_bus):
        """Test handling API call errors."""
        # Setup API error
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create.side_effect = Exception("API test error")
        mock_chat.completions = mock_completions
        mock_client.chat = mock_chat
        
        # Replace client with mock
        api_model.client = mock_client
        
        # Setup error spy
        error_spy = MagicMock()
        event_bus.subscribe('error:api', error_spy)
        
        # Test API call with error
        messages = [{"role": "system", "content": "Test system message"}]
        result = api_model.call_api(messages)
        
        # Verify error handling
        assert result is None
        assert error_spy.called
        call_args = error_spy.call_args[0][0]
        assert "API test error" in call_args['message']
    
    def test_generate_cache_key(self, api_model):
        """Test cache key generation."""
        # Test with simple params
        params1 = {"word": "apple", "language": "Czech"}
        key1 = api_model.generate_cache_key("lemma", params1)
        assert isinstance(key1, str)
        assert len(key1) > 0
        
        # Test with different params
        params2 = {"word": "orange", "language": "Czech"}
        key2 = api_model.generate_cache_key("lemma", params2)
        assert key1 != key2  # Different params should yield different keys
        
        # Test with same params but different order
        params3 = {"language": "Czech", "word": "apple"}
        key3 = api_model.generate_cache_key("lemma", params3)
        assert key1 == key3  # Should be same despite different order
        
        # Test with different request type
        key4 = api_model.generate_cache_key("entry", params1)
        assert key1 != key4  # Different request type should yield different key
    
    def test_caching(self, api_model, event_bus):
        """Test response caching functionality."""
        # Setup mock response data
        test_response = {"result": "test response data"}
        cache_key = "test_cache_key"
        
        # Test saving to cache
        result = api_model._save_to_cache(cache_key, test_response)
        assert result is True
        
        # Verify file was created
        cache_path = api_model._get_cache_path(cache_key)
        assert os.path.exists(cache_path)
        
        # Test reading from cache
        cached = api_model._get_from_cache(cache_key)
        assert cached == test_response
        
        # Test cache hit in API call
        with patch.object(api_model, '_get_from_cache') as mock_get_cache:
            with patch.object(api_model, 'client') as mock_client:
                # Set up the cache hit
                mock_get_cache.return_value = test_response
                
                # Cache hit spy
                hit_spy = MagicMock()
                event_bus.subscribe('api:cache_hit', hit_spy)
                
                # Call API with caching
                result = api_model.call_api(
                    [{"role": "user", "content": "test"}],
                    cache_key=cache_key
                )
                
                # Verify result came from cache
                assert result == test_response
                assert hit_spy.called
                assert api_model.cache_stats['hits'] == 1
                
                # Verify API client was not called
                mock_client.chat.completions.create.assert_not_called()
    
    def test_clear_cache(self, api_model, event_bus):
        """Test clearing the cache."""
        # Create some test cache entries
        cache_keys = ["test_key1", "test_key2", "test_key3"]
        test_data = {"result": "test data"}
        
        for key in cache_keys:
            api_model._save_to_cache(key, test_data)
        
        # Setup event spy
        clear_spy = MagicMock()
        event_bus.subscribe('cache:cleared', clear_spy)
        
        # Clear the cache
        cleared = api_model.clear_cache()
        assert cleared == 3
        
        # Verify cache directory is empty
        cache_files = list(Path(api_model.cache_dir).glob('*.json'))
        assert len(cache_files) == 0
        
        # Verify event was published
        assert clear_spy.called
        call_args = clear_spy.call_args[0][0]
        assert call_args['count'] == 3
    
    def test_cache_expiration(self, api_model):
        """Test cache entry expiration."""
        # Create test cache entry
        cache_key = "expiration_test"
        test_data = {"result": "expiration test data"}
        
        api_model._save_to_cache(cache_key, test_data)
        
        # Set very short cache expiration
        api_model.cache_max_age = 0  # Immediate expiration
        
        # Try to get from cache (should be expired)
        result = api_model._get_from_cache(cache_key)
        assert result is None
    
    def test_get_cache_stats(self, api_model):
        """Test getting cache statistics."""
        # Create some test cache entries
        cache_keys = ["stats_key1", "stats_key2"]
        test_data = {"result": "stats test data"}
        
        for key in cache_keys:
            api_model._save_to_cache(key, test_data)
        
        # Update cache stats manually for testing
        api_model.cache_stats['hits'] = 5
        api_model.cache_stats['misses'] = 3
        api_model.cache_stats['errors'] = 1
        
        # Get cache stats
        stats = api_model.get_cache_stats()
        
        # Verify stats
        assert stats['file_count'] == 2
        assert stats['hits'] == 5
        assert stats['misses'] == 3
        assert stats['errors'] == 1
        assert stats['hit_ratio'] == 5/8  # 5 hits out of 8 total requests