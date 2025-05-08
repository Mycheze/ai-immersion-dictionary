"""
Tests for the EventBus utility.

This module contains tests for the EventBus class, which provides
a centralized event system for the application.
"""

import pytest
import threading
import time
from src.utils.event_bus import EventBus

class TestEventBus:
    """Tests for the EventBus class."""
    
    def test_initialization(self):
        """Test that the EventBus initializes correctly."""
        event_bus = EventBus()
        assert event_bus.subscribers == {}
        assert isinstance(event_bus.lock, threading.RLock)
    
    def test_subscribe_and_publish(self):
        """Test subscribing to events and publishing events."""
        event_bus = EventBus()
        
        # Create a mock callback
        received_data = []
        def callback(data):
            received_data.append(data)
        
        # Subscribe to an event
        event_bus.subscribe("test_event", callback)
        
        # Check that the callback was registered
        assert "test_event" in event_bus.subscribers
        assert callback in event_bus.subscribers["test_event"]
        
        # Publish an event
        event_data = {"message": "Hello, World!"}
        count = event_bus.publish("test_event", event_data)
        
        # Check that the callback was called
        assert count == 1
        assert len(received_data) == 1
        assert received_data[0] == event_data
    
    def test_unsubscribe(self):
        """Test unsubscribing from events."""
        event_bus = EventBus()
        
        # Create a mock callback
        def callback(data):
            pass
        
        # Subscribe and then unsubscribe
        event_bus.subscribe("test_event", callback)
        result = event_bus.unsubscribe("test_event", callback)
        
        # Check that the callback was unregistered
        assert result is True
        assert "test_event" in event_bus.subscribers
        assert callback not in event_bus.subscribers["test_event"]
        
        # Unsubscribe from a non-existent event
        result = event_bus.unsubscribe("non_existent_event", callback)
        assert result is False
        
        # Unsubscribe a non-existent callback
        def another_callback(data):
            pass
        
        event_bus.subscribe("test_event", callback)
        result = event_bus.unsubscribe("test_event", another_callback)
        assert result is False
    
    def test_publish_nonexistent_event(self):
        """Test publishing an event with no subscribers."""
        event_bus = EventBus()
        
        # Publish an event with no subscribers
        count = event_bus.publish("non_existent_event", {"message": "Hello"})
        
        # Check that no callbacks were called
        assert count == 0
    
    def test_multiple_subscribers(self):
        """Test multiple subscribers for a single event."""
        event_bus = EventBus()
        
        # Create mock callbacks
        callback1_called = False
        callback2_called = False
        
        def callback1(data):
            nonlocal callback1_called
            callback1_called = True
        
        def callback2(data):
            nonlocal callback2_called
            callback2_called = True
        
        # Subscribe both callbacks
        event_bus.subscribe("test_event", callback1)
        event_bus.subscribe("test_event", callback2)
        
        # Publish an event
        count = event_bus.publish("test_event", {"message": "Hello"})
        
        # Check that both callbacks were called
        assert count == 2
        assert callback1_called is True
        assert callback2_called is True
    
    def test_error_in_callback(self):
        """Test that errors in callbacks are handled gracefully."""
        event_bus = EventBus()
        
        # Create a callback that raises an error
        def error_callback(data):
            raise ValueError("Test error")
        
        # Create a normal callback
        normal_called = False
        def normal_callback(data):
            nonlocal normal_called
            normal_called = True
        
        # Subscribe both callbacks
        event_bus.subscribe("test_event", error_callback)
        event_bus.subscribe("test_event", normal_callback)
        
        # Publish an event
        count = event_bus.publish("test_event", {"message": "Hello"})
        
        # Check that the error didn't prevent the normal callback from being called
        assert count == 1  # Only one callback succeeded
        assert normal_called is True
    
    def test_async_publish(self):
        """Test publishing events asynchronously."""
        event_bus = EventBus()
        
        # Create a mock callback with delay
        called = False
        def slow_callback(data):
            time.sleep(0.1)  # Short delay
            nonlocal called
            called = True
        
        # Subscribe the callback
        event_bus.subscribe("test_event", slow_callback)
        
        # Publish asynchronously
        event_bus.publish_async("test_event", {"message": "Hello"})
        
        # Verify callback hasn't been called yet
        assert called is False
        
        # Wait for callback to complete
        time.sleep(0.2)
        
        # Now it should be called
        assert called is True
    
    def test_clear_event_subscriptions(self):
        """Test clearing all subscriptions for a specific event."""
        event_bus = EventBus()
        
        # Create callbacks
        def callback1(data):
            pass
        
        def callback2(data):
            pass
        
        # Subscribe to multiple events
        event_bus.subscribe("event1", callback1)
        event_bus.subscribe("event2", callback1)
        event_bus.subscribe("event2", callback2)
        
        # Clear subscriptions for event2
        result = event_bus.clear_event_subscriptions("event2")
        
        # Check that event2 subscriptions were cleared
        assert result is True
        assert "event1" in event_bus.subscribers
        assert "event2" not in event_bus.subscribers
        
        # Clear subscriptions for a non-existent event
        result = event_bus.clear_event_subscriptions("non_existent_event")
        assert result is False
    
    def test_clear_all_subscriptions(self):
        """Test clearing all subscriptions."""
        event_bus = EventBus()
        
        # Create a callback
        def callback(data):
            pass
        
        # Subscribe to multiple events
        event_bus.subscribe("event1", callback)
        event_bus.subscribe("event2", callback)
        
        # Clear all subscriptions
        event_bus.clear_all_subscriptions()
        
        # Check that all subscriptions were cleared
        assert event_bus.subscribers == {}
    
    def test_get_subscriber_count(self):
        """Test getting the subscriber count for an event."""
        event_bus = EventBus()
        
        # Create callbacks
        def callback1(data):
            pass
        
        def callback2(data):
            pass
        
        # Subscribe to an event
        event_bus.subscribe("test_event", callback1)
        event_bus.subscribe("test_event", callback2)
        
        # Get the subscriber count
        count = event_bus.get_subscriber_count("test_event")
        
        # Check the count
        assert count == 2
        
        # Get count for a non-existent event
        count = event_bus.get_subscriber_count("non_existent_event")
        assert count == 0
    
    def test_thread_safety(self):
        """Test thread safety of the EventBus."""
        event_bus = EventBus()
        
        # Create a shared counter
        count = 0
        count_lock = threading.Lock()
        
        def increment_count(data):
            nonlocal count
            with count_lock:
                count += 1
        
        # Subscribe the callback
        event_bus.subscribe("test_event", increment_count)
        
        # Create multiple threads to publish events
        threads = []
        for _ in range(10):
            thread = threading.Thread(
                target=event_bus.publish,
                args=("test_event", {"message": "Hello"})
            )
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that the callback was called the correct number of times
        assert count == 10