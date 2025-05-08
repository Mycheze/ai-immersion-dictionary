"""
Retry Manager

This module provides a utility for handling retries of operations that may fail
temporarily, such as network requests. It implements configurable retry strategies
with exponential backoff, jitter, and customizable retry conditions.
"""

import time
import random
import math
from typing import Callable, Any, Optional, List, Dict, TypeVar, Union

# Type variable for generic return type
T = TypeVar('T')

class RetryConfig:
    """
    Configuration for retry behavior.
    
    Attributes:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        jitter: Whether to add randomness to delay (True/False)
        jitter_factor: Maximum factor by which to randomize delay (0.0-1.0)
        retry_codes: List of error codes that should trigger a retry
        retry_on_exceptions: List of exception types that should trigger a retry
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        jitter_factor: float = 0.2,
        retry_codes: Optional[List[Union[int, str]]] = None,
        retry_on_exceptions: Optional[List[type]] = None
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Factor to multiply delay by after each retry
            jitter: Whether to add randomness to delay
            jitter_factor: Maximum factor by which to randomize delay
            retry_codes: List of error codes that should trigger a retry
            retry_on_exceptions: List of exception types that should trigger a retry
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        self.retry_codes = retry_codes or []
        self.retry_on_exceptions = retry_on_exceptions or []
        
    def should_retry(self, exception: Exception, code: Optional[Union[int, str]] = None) -> bool:
        """
        Determine if a retry should be attempted based on the exception or code.
        
        Args:
            exception: The exception that was raised
            code: Optional error code associated with the exception
            
        Returns:
            True if a retry should be attempted, False otherwise
        """
        # Check if exception type should be retried
        for exc_type in self.retry_on_exceptions:
            if isinstance(exception, exc_type):
                return True
                
        # Check if error code should be retried
        if code is not None and code in self.retry_codes:
            return True
            
        return False
        
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate the delay before the next retry attempt.
        
        Args:
            attempt: Current retry attempt number (0-indexed)
            
        Returns:
            Delay in seconds before the next retry
        """
        # Calculate exponential backoff
        delay = self.base_delay * (self.backoff_factor ** attempt)
        
        # Cap at max delay
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            jitter_amount = delay * self.jitter_factor
            delay = delay + random.uniform(-jitter_amount, jitter_amount)
            
        # Ensure delay is non-negative
        return max(0.0, delay)


class RetryManager:
    """
    Manages retry attempts for operations that may fail temporarily.
    """
    
    # Default retry configuration for different operation types
    DEFAULT_CONFIGS = {
        'api': RetryConfig(
            max_retries=3,
            base_delay=2.0,
            max_delay=30.0,
            backoff_factor=2.0,
            jitter=True,
            retry_on_exceptions=[
                ConnectionError,
                TimeoutError,
                OSError
            ],
            retry_codes=[
                429,  # Too Many Requests
                500,  # Internal Server Error
                502,  # Bad Gateway
                503,  # Service Unavailable
                504   # Gateway Timeout
            ]
        ),
        'database': RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=5.0,
            backoff_factor=1.5,
            jitter=True,
            retry_on_exceptions=[
                ConnectionError,
                TimeoutError,
                OSError
            ]
        ),
        'network': RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0,
            jitter=True,
            retry_on_exceptions=[
                ConnectionError,
                TimeoutError,
                OSError
            ]
        )
    }
    
    @classmethod
    def with_retry(
        cls,
        operation: Callable[..., T],
        config: Optional[RetryConfig] = None,
        config_type: str = 'api',
        on_retry: Optional[Callable[[Exception, int, float], None]] = None,
        get_error_code: Optional[Callable[[Exception], Union[int, str, None]]] = None,
        *args,
        **kwargs
    ) -> T:
        """
        Execute an operation with retry logic.
        
        Args:
            operation: The function to execute
            config: Optional retry configuration (uses default if None)
            config_type: Type of default config to use if no config provided
            on_retry: Optional callback to notify of retry attempts
            get_error_code: Optional function to extract error code from exceptions
            *args: Positional arguments to pass to the operation
            **kwargs: Keyword arguments to pass to the operation
            
        Returns:
            Result of the operation
            
        Raises:
            The last exception encountered if all retries fail
        """
        # Use provided config or default for the specified type
        retry_config = config or cls.DEFAULT_CONFIGS.get(config_type, cls.DEFAULT_CONFIGS['api'])
        
        last_exception = None
        
        # Attempt operation with retries
        for attempt in range(retry_config.max_retries + 1):  # +1 for initial attempt
            try:
                return operation(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                # Extract error code if possible
                error_code = None
                if get_error_code:
                    try:
                        error_code = get_error_code(e)
                    except:
                        pass
                
                # Determine if retry should be attempted
                if attempt < retry_config.max_retries and retry_config.should_retry(e, error_code):
                    # Calculate delay
                    delay = retry_config.calculate_delay(attempt)
                    
                    # Notify of retry if callback provided
                    if on_retry:
                        try:
                            on_retry(e, attempt + 1, delay)
                        except:
                            pass  # Ignore errors in the callback
                    
                    # Wait before retrying
                    time.sleep(delay)
                else:
                    # Re-raise the last exception if no more retries
                    raise
        
        # This should never be reached, but just in case
        raise last_exception if last_exception else RuntimeError("Retry operation failed")


# Helper functions for common retry patterns

def retry_api_call(
    api_call: Callable[..., T],
    max_retries: int = 3,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
    *args,
    **kwargs
) -> T:
    """
    Retry an API call with sensible defaults for API operations.
    
    Args:
        api_call: The API function to call
        max_retries: Maximum number of retry attempts
        on_retry: Optional callback to notify of retry attempts
        *args: Positional arguments to pass to the API call
        **kwargs: Keyword arguments to pass to the API call
        
    Returns:
        Result of the API call
        
    Raises:
        Exception if all retries fail
    """
    # Create a custom config with the specified max_retries
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=2.0,
        max_delay=30.0,
        backoff_factor=2.0,
        jitter=True,
        retry_on_exceptions=[
            ConnectionError,
            TimeoutError,
            OSError
        ],
        retry_codes=[
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504   # Gateway Timeout
        ]
    )
    
    # Helper function to extract error code from different API exceptions
    def get_api_error_code(e: Exception) -> Optional[Union[int, str]]:
        # Try to extract error code based on the exception type/structure
        if hasattr(e, 'status_code'):
            return getattr(e, 'status_code')
        elif hasattr(e, 'code'):
            return getattr(e, 'code')
        elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            return e.response.status_code
        return None
    
    return RetryManager.with_retry(
        api_call,
        config=config,
        on_retry=on_retry,
        get_error_code=get_api_error_code,
        *args,
        **kwargs
    )