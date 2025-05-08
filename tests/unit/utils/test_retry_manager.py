"""
Tests for the RetryManager utility.

This module contains tests for the RetryManager class, which provides
retry functionality for operations that may fail temporarily.
"""

import pytest
import time
from unittest.mock import Mock, patch
from src.utils.retry_manager import RetryConfig, RetryManager, retry_api_call

class TestRetryConfig:
    """Tests for the RetryConfig class."""
    
    def test_initialization(self):
        """Test that RetryConfig initializes correctly with default values."""
        config = RetryConfig()
        
        # Check default values
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True
        assert config.jitter_factor == 0.2
        assert config.retry_codes == []
        assert config.retry_on_exceptions == []
        
        # Test with custom values
        custom_config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=10.0,
            backoff_factor=1.5,
            jitter=False,
            jitter_factor=0.1,
            retry_codes=[429, 500],
            retry_on_exceptions=[ConnectionError, TimeoutError]
        )
        
        assert custom_config.max_retries == 5
        assert custom_config.base_delay == 0.5
        assert custom_config.max_delay == 10.0
        assert custom_config.backoff_factor == 1.5
        assert custom_config.jitter is False
        assert custom_config.jitter_factor == 0.1
        assert custom_config.retry_codes == [429, 500]
        assert custom_config.retry_on_exceptions == [ConnectionError, TimeoutError]
    
    def test_should_retry(self):
        """Test the should_retry method."""
        # Config with specific retry conditions
        config = RetryConfig(
            retry_codes=[429, 500],
            retry_on_exceptions=[ConnectionError, TimeoutError]
        )
        
        # Test retry based on exception type
        assert config.should_retry(ConnectionError()) is True
        assert config.should_retry(TimeoutError()) is True
        assert config.should_retry(ValueError()) is False
        
        # Test retry based on error code
        assert config.should_retry(Exception(), 429) is True
        assert config.should_retry(Exception(), 500) is True
        assert config.should_retry(Exception(), 404) is False
        
        # Test retry based on both
        assert config.should_retry(ConnectionError(), 429) is True
        assert config.should_retry(ValueError(), 429) is True
        assert config.should_retry(ConnectionError(), 404) is True
        assert config.should_retry(ValueError(), 404) is False
    
    def test_calculate_delay(self):
        """Test the calculate_delay method."""
        # Config without jitter for deterministic testing
        config = RetryConfig(
            base_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0,
            jitter=False
        )
        
        # First retry should use base delay
        assert config.calculate_delay(0) == 1.0
        
        # Second retry should use backoff
        assert config.calculate_delay(1) == 2.0
        
        # Third retry should use more backoff
        assert config.calculate_delay(2) == 4.0
        
        # Fourth retry should use even more backoff
        assert config.calculate_delay(3) == 8.0
        
        # Fifth retry should be capped at max_delay
        config.max_delay = 5.0
        assert config.calculate_delay(3) == 5.0
        
        # Test with jitter
        config.jitter = True
        config.jitter_factor = 0.5
        
        # With jitter, the delay should be in range [base_delay * (1 - jitter_factor), base_delay * (1 + jitter_factor)]
        delay = config.calculate_delay(0)  # base_delay = 1.0
        assert 0.5 <= delay <= 1.5


class TestRetryManager:
    """Tests for the RetryManager class."""
    
    def test_default_configs(self):
        """Test that default configs are properly defined."""
        assert 'api' in RetryManager.DEFAULT_CONFIGS
        assert 'database' in RetryManager.DEFAULT_CONFIGS
        assert 'network' in RetryManager.DEFAULT_CONFIGS
        
        # Check that the API config has reasonable defaults
        api_config = RetryManager.DEFAULT_CONFIGS['api']
        assert api_config.max_retries == 3
        assert 429 in api_config.retry_codes  # Should retry on rate limiting
        assert ConnectionError in api_config.retry_on_exceptions
    
    def test_with_retry_success_first_try(self):
        """Test with_retry when operation succeeds on first try."""
        # Mock operation that always succeeds
        operation = Mock(return_value="success")
        
        # Call with_retry
        result = RetryManager.with_retry(operation, max_retries=3)
        
        # Check that the operation was called once and the result is correct
        operation.assert_called_once()
        assert result == "success"
    
    def test_with_retry_success_after_retries(self):
        """Test with_retry when operation succeeds after some retries."""
        # Mock operation that fails twice then succeeds
        operation = Mock(side_effect=[ConnectionError(), ConnectionError(), "success"])
        
        # Mock time.sleep to avoid waiting during tests
        with patch('time.sleep') as mock_sleep:
            # Call with_retry
            result = RetryManager.with_retry(
                operation,
                config=RetryConfig(
                    max_retries=3,
                    retry_on_exceptions=[ConnectionError]
                )
            )
            
            # Check that operation was called 3 times
            assert operation.call_count == 3
            
            # Check that sleep was called 2 times (after each failure)
            assert mock_sleep.call_count == 2
            
            # Check the result
            assert result == "success"
    
    def test_with_retry_all_attempts_fail(self):
        """Test with_retry when all attempts fail."""
        # Mock operation that always fails
        operation = Mock(side_effect=ConnectionError("Connection failed"))
        
        # Mock time.sleep to avoid waiting during tests
        with patch('time.sleep'):
            # Call with_retry and expect it to raise
            with pytest.raises(ConnectionError, match="Connection failed"):
                RetryManager.with_retry(
                    operation,
                    config=RetryConfig(
                        max_retries=2,
                        retry_on_exceptions=[ConnectionError]
                    )
                )
            
            # Check that operation was called for initial attempt + max_retries
            assert operation.call_count == 3
    
    def test_with_retry_non_retriable_exception(self):
        """Test with_retry when a non-retriable exception occurs."""
        # Mock operation that raises a non-retriable exception
        operation = Mock(side_effect=ValueError("Invalid value"))
        
        # Call with_retry and expect it to raise immediately
        with pytest.raises(ValueError, match="Invalid value"):
            RetryManager.with_retry(
                operation,
                config=RetryConfig(
                    max_retries=3,
                    retry_on_exceptions=[ConnectionError]  # ValueError not in list
                )
            )
        
        # Check that operation was called only once
        operation.assert_called_once()
    
    def test_with_retry_callback(self):
        """Test with_retry with a retry callback."""
        # Mock operation that fails twice then succeeds
        operation = Mock(side_effect=[ConnectionError(), ConnectionError(), "success"])
        
        # Mock callback
        on_retry = Mock()
        
        # Mock time.sleep to avoid waiting during tests
        with patch('time.sleep'):
            # Call with_retry
            result = RetryManager.with_retry(
                operation,
                config=RetryConfig(
                    max_retries=3,
                    retry_on_exceptions=[ConnectionError]
                ),
                on_retry=on_retry
            )
            
            # Check that callback was called for each retry
            assert on_retry.call_count == 2
            
            # Check callback arguments for first call
            args, kwargs = on_retry.call_args_list[0]
            assert isinstance(args[0], ConnectionError)  # The exception
            assert args[1] == 1  # Retry attempt number (1-indexed)
            assert isinstance(args[2], float)  # Delay
            
            # Check the result
            assert result == "success"
    
    def test_retry_api_call(self):
        """Test the retry_api_call helper function."""
        # Mock API call that fails with status code then succeeds
        class MockApiError(Exception):
            def __init__(self, status_code):
                self.status_code = status_code
        
        api_call = Mock(side_effect=[
            MockApiError(429),  # Rate limited
            MockApiError(500),  # Server error
            "success"
        ])
        
        # Mock callback
        on_retry = Mock()
        
        # Mock time.sleep to avoid waiting during tests
        with patch('time.sleep'):
            # Call retry_api_call
            result = retry_api_call(
                api_call,
                max_retries=3,
                on_retry=on_retry
            )
            
            # Check that API call was attempted 3 times
            assert api_call.call_count == 3
            
            # Check that callback was called for each retry
            assert on_retry.call_count == 2
            
            # Check the result
            assert result == "success"