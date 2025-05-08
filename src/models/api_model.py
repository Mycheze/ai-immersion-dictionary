"""
API Model

This module provides a model for API interactions and response handling,
abstracting the details of API communication from the rest of the application.
"""

import os
import re
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta

from openai import OpenAI
from openai.types.completion_usage import CompletionUsage
from openai.types.chat import ChatCompletion
from openai.error import APIError, APIConnectionError, RateLimitError, APIStatusError, OpenAIError

from src.utils.retry_manager import retry_api_call, RetryConfig, RetryManager

class APIModel:
    """
    Model for API interactions with AI language models.
    
    This class encapsulates all API-related operations, providing a clean
    interface for making API calls and handling responses.
    
    Attributes:
        client: The API client for communication
        api_key: The API key for authentication
        cache_dir: Directory for caching API responses
        event_bus: Event system for model-related notifications
        template_dirs: Directories containing prompt templates
    """
    
    def __init__(
        self, 
        api_key_path: Union[str, Path] = None,
        cache_dir: Union[str, Path] = None, 
        config_dir: Union[str, Path] = None,
        event_bus = None
    ):
        """
        Initialize the API model.
        
        Args:
            api_key_path: Path to the API key file
            cache_dir: Directory for caching responses
            config_dir: Directory containing prompt templates
            event_bus: Optional event bus for notifications
        """
        self.app_root = Path(__file__).parent.parent.parent.absolute()
        self.api_key_path = Path(api_key_path) if api_key_path else self.app_root / 'api_key.txt'
        self.config_dir = Path(config_dir) if config_dir else self.app_root / 'config'
        
        # Set up cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = self.app_root / 'cache'
            
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Read API key
        self.api_key = self._read_api_key()
        self.client = None
        
        # Initialize API client if we have a valid key
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
            
        # Set event bus
        self.event_bus = event_bus
        
        # Load prompt templates
        self.prompt_templates = {}
        self._load_prompt_templates()
        
        # Initialize cache manager
        from src.utils.cache_manager import cache_manager
        self.cache_manager = cache_manager
        
        # Configure cache manager
        self.cache_manager.cache_dir = self.cache_dir
        self.cache_manager.cache_enabled = True
        self.cache_manager.cache_max_age = 24 * 60 * 60  # Default: 24 hours in seconds
        self.cache_manager.event_bus = event_bus
        
        # For backwards compatibility
        self.cache_enabled = True
        self.cache_max_age = 24 * 60 * 60
    
    def _read_api_key(self) -> Optional[str]:
        """
        Read API key from file.
        
        Returns:
            API key string or None if not found
        """
        try:
            with open(self.api_key_path, 'r') as f:
                api_key = f.read().strip()
                if not api_key:
                    if self.event_bus:
                        self.event_bus.publish('error:api', {
                            'message': "API key file is empty"
                        })
                    return None
                return api_key
        except FileNotFoundError:
            if self.event_bus:
                self.event_bus.publish('error:api', {
                    'message': f"API key file not found at {self.api_key_path}"
                })
            return None
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:api', {
                    'message': f"Error reading API key: {str(e)}"
                })
            return None
    
    def _load_prompt_templates(self) -> None:
        """Load all prompt templates from the config directory."""
        try:
            for template_file in self.config_dir.glob('*.txt'):
                template_name = template_file.stem
                with open(template_file, 'r', encoding='utf-8') as f:
                    self.prompt_templates[template_name] = f.read()
                    
            if self.event_bus:
                self.event_bus.publish('prompts:loaded', {
                    'count': len(self.prompt_templates),
                    'templates': list(self.prompt_templates.keys())
                })
                
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:prompts', {
                    'message': f"Error loading prompt templates: {str(e)}"
                })
    
    def get_prompt_template(self, template_name: str) -> Optional[str]:
        """
        Get a prompt template by name.
        
        Args:
            template_name: Name of the template (without .txt extension)
            
        Returns:
            The template text or None if not found
        """
        if template_name in self.prompt_templates:
            return self.prompt_templates[template_name]
            
        # Try to load it if not already loaded
        template_path = self.config_dir / f"{template_name}.txt"
        if template_path.exists():
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    template = f.read()
                    self.prompt_templates[template_name] = template
                    return template
            except Exception as e:
                if self.event_bus:
                    self.event_bus.publish('error:prompts', {
                        'message': f"Error loading prompt template '{template_name}': {str(e)}"
                    })
                    
        return None
    
    def process_prompt(
        self, 
        template_name: str, 
        replacements: Dict[str, str],
        additional_vars: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Process a prompt template by replacing variables.
        
        Args:
            template_name: Name of the template to process
            replacements: Dictionary of template variables and values
            additional_vars: Additional variables to include in replacement
            
        Returns:
            The processed prompt or None if processing failed
        """
        try:
            # Get the template
            template = self.get_prompt_template(template_name)
            if not template:
                if self.event_bus:
                    self.event_bus.publish('error:prompts', {
                        'message': f"Prompt template '{template_name}' not found"
                    })
                return None
                
            # Find all variables in the template
            variables = set(re.findall(r'\[([A-Z_]+)\]', template))
            
            # Check for missing variables
            missing = [var for var in variables if var not in replacements]
            if missing and not additional_vars:
                if self.event_bus:
                    self.event_bus.publish('error:prompts', {
                        'message': f"Missing variables in prompt template: {', '.join(missing)}"
                    })
                return None
                
            # Process the template
            processed = template
            for var in variables:
                if var in replacements:
                    processed = processed.replace(f'[{var}]', replacements[var])
                elif additional_vars and var in additional_vars:
                    processed = processed.replace(f'[{var}]', additional_vars[var])
                    
            return processed
            
        except Exception as e:
            if self.event_bus:
                self.event_bus.publish('error:prompts', {
                    'message': f"Error processing prompt template: {str(e)}"
                })
            return None
    
    def call_api(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        cache_key: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[Any]:
        """
        Call the API with messages and handle response.
        
        Args:
            messages: List of message dictionaries (role, content)
            temperature: Temperature parameter for generation (0.0-1.0)
            cache_key: Optional cache key for response caching
            max_retries: Maximum number of retry attempts for failed API calls
            
        Returns:
            API response or None if the call failed
        """
        # Check if API client is available
        if not self.client:
            if self.event_bus:
                self.event_bus.publish('error:api', {
                    'message': "No API client available - please set up your API key"
                })
            return None
            
        # Try to get from cache first if caching is enabled
        if self.cache_enabled and cache_key:
            hit, cached_response = self.cache_manager.get(cache_key)
            if hit and cached_response:
                # Cache hit notification is handled by cache_manager
                return cached_response
                
        # Prepare parameters for the API call
        params = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        # Notify of API call start if event bus exists
        if self.event_bus:
            self.event_bus.publish('api:call_started', {
                'model': params["model"],
                'temperature': temperature,
                'message_count': len(messages)
            })
                
        # Define the API call function
        def _make_api_call():
            # Make the actual API call
            return self.client.chat.completions.create(**params)
        
        # Define retry notification callback
        def _on_retry(exception, attempt, delay):
            if self.event_bus:
                self.event_bus.publish('api:retry', {
                    'attempt': attempt,
                    'max_retries': max_retries,
                    'delay': delay,
                    'error': str(exception),
                    'model': params["model"]
                })
        
        try:
            # Time the API call (including any retries)
            start_time = time.time()
            
            # Make the API call with retry logic
            response = retry_api_call(
                _make_api_call,
                max_retries=max_retries,
                on_retry=_on_retry
            )
            
            # Calculate call duration
            duration = time.time() - start_time
            
            # Extract usage statistics if available
            usage = None
            if hasattr(response, 'usage') and isinstance(response.usage, CompletionUsage):
                usage = {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            
            # Notify of API call completion if event bus exists
            if self.event_bus:
                self.event_bus.publish('api:call_completed', {
                    'duration': duration,
                    'model': params["model"],
                    'temperature': temperature,
                    'usage': usage
                })
                
            # Cache the response if caching is enabled
            if self.cache_enabled and cache_key:
                self.cache_manager.put(cache_key, response)
                
            return response
            
        except (APIError, APIConnectionError, RateLimitError, APIStatusError) as e:
            # Handle specific API errors
            error_type = type(e).__name__
            status_code = getattr(e, 'status_code', None)
            
            # Errors are tracked by the cache manager
            
            # Notify of API error if event bus exists
            if self.event_bus:
                self.event_bus.publish('error:api', {
                    'message': f"API call failed after {max_retries} retries: {str(e)}",
                    'error_type': error_type,
                    'status_code': status_code
                })
                
            return None
            
        except Exception as e:
            # Handle generic errors
            self.cache_stats['errors'] += 1
            
            # Notify of API error if event bus exists
            if self.event_bus:
                self.event_bus.publish('error:api', {
                    'message': f"API call failed with unexpected error: {str(e)}",
                    'error_type': type(e).__name__
                })
                
            return None
    
    def generate_cache_key(self, request_type: str, params: Dict[str, Any]) -> str:
        """
        Generate a cache key for an API request.
        
        Args:
            request_type: Type of request (lemma, entry, etc.)
            params: Request parameters
            
        Returns:
            Unique cache key for the request
        """
        # Use cache manager to generate key
        return self.cache_manager.generate_cache_key(request_type, params)
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """
        Get the file path for a cache key.
        
        Args:
            cache_key: The cache key
            
        Returns:
            Path to the cache file
        """
        # For backward compatibility
        return self.cache_dir / f"{cache_key}.json"
    
    def clear_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Clear the API response cache.
        
        Args:
            older_than_days: Only clear entries older than this many days
            
        Returns:
            Number of cache entries cleared
        """
        # Use cache manager to clear both memory and disk cache
        return self.cache_manager.clear(older_than_days)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the API cache.
        
        Returns:
            Dictionary of cache statistics
        """
        # Get stats from cache manager
        cache_stats = self.cache_manager.get_stats()
        
        # Add file count and size info
        cache_file_count = len(list(self.cache_dir.glob('*.json')))
        cache_size = sum(f.stat().st_size for f in self.cache_dir.glob('*.json'))
        
        cache_stats.update({
            'file_count': cache_file_count,
            'size_bytes': cache_size,
        })
        
        return cache_stats