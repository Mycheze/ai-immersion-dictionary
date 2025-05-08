"""
Tests for the CacheManager utility.

This module contains tests for the CacheManager class, which provides
a two-level caching system for improving performance and reducing API calls.
"""

import pytest
import os
import tempfile
import json
import time
import threading
from pathlib import Path
from unittest.mock import Mock

from src.utils.cache_manager import LRUCache, CacheManager, cached
from src.utils.event_bus import EventBus

class TestLRUCache:
    """Tests for the LRUCache class."""
    
    def test_initialization(self):
        """Test that the LRUCache initializes correctly."""
        cache = LRUCache(capacity=10)
        assert cache.capacity == 10
        assert len(cache.cache) == 0
        assert isinstance(cache.lock, threading.RLock)
    
    def test_put_and_get(self):
        """Test storing and retrieving items."""
        cache = LRUCache(capacity=3)
        
        # Add an item
        cache.put("key1", "value1")
        hit, value = cache.get("key1")
        
        # Check retrieval
        assert hit is True
        assert value == "value1"
        
        # Check non-existent key
        hit, value = cache.get("nonexistent")
        assert hit is False
        assert value is None
    
    def test_capacity_limit(self):
        """Test that cache respects capacity limit."""
        cache = LRUCache(capacity=2)
        
        # Add items to fill the cache
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Check both items are in the cache
        assert cache.size() == 2
        
        # Add another item, exceeding capacity
        cache.put("key3", "value3")
        
        # Check oldest item was removed
        assert cache.size() == 2
        hit, _ = cache.get("key1")
        assert hit is False  # key1 should be evicted
        
        # Check other items are still there
        hit, value2 = cache.get("key2")
        hit, value3 = cache.get("key3")
        assert hit is True
        assert value2 == "value2"
        assert value3 == "value3"
    
    def test_lru_behavior(self):
        """Test that least recently used items are evicted first."""
        cache = LRUCache(capacity=3)
        
        # Add items
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        # Access key1, making key2 the least recently used
        cache.get("key1")
        cache.get("key3")
        
        # Add another item, exceeding capacity
        cache.put("key4", "value4")
        
        # Check key2 (least recently used) was evicted
        hit, _ = cache.get("key2")
        assert hit is False
        
        # Check other items are still there
        hit, _ = cache.get("key1")
        hit, _ = cache.get("key3")
        hit, _ = cache.get("key4")
        assert hit is True
    
    def test_remove(self):
        """Test removing items from the cache."""
        cache = LRUCache(capacity=3)
        
        # Add items
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Remove an item
        result = cache.remove("key1")
        assert result is True
        
        # Check it's gone
        hit, _ = cache.get("key1")
        assert hit is False
        
        # Check removing non-existent key
        result = cache.remove("nonexistent")
        assert result is False
    
    def test_clear(self):
        """Test clearing the entire cache."""
        cache = LRUCache(capacity=3)
        
        # Add items
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Clear the cache
        cache.clear()
        
        # Check it's empty
        assert cache.size() == 0
        hit, _ = cache.get("key1")
        assert hit is False
    
    def test_thread_safety(self):
        """Test thread safety of the cache."""
        cache = LRUCache(capacity=100)
        
        # Function to add items from a thread
        def add_items(start, count):
            for i in range(start, start + count):
                key = f"key{i}"
                value = f"value{i}"
                cache.put(key, value)
        
        # Create threads to add items concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_items, args=(i * 20, 20))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check all items were added
        assert cache.size() == 100
        
        # Check some random items
        hit, value = cache.get("key0")
        assert hit is True
        assert value == "value0"
        
        hit, value = cache.get("key99")
        assert hit is True
        assert value == "value99"


class TestCacheManager:
    """Tests for the CacheManager class."""
    
    @pytest.fixture
    def event_bus(self):
        """Fixture for creating an EventBus instance."""
        return EventBus()
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Fixture for creating a temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_cache_dir, event_bus):
        """Fixture for creating a CacheManager instance with a temporary cache directory."""
        manager = CacheManager(
            cache_dir=temp_cache_dir,
            memory_cache_capacity=10,
            cache_max_age=60,  # 1 minute
            event_bus=event_bus
        )
        yield manager
    
    def test_initialization(self, temp_cache_dir, event_bus):
        """Test that the CacheManager initializes correctly."""
        manager = CacheManager(
            cache_dir=temp_cache_dir,
            memory_cache_capacity=10,
            cache_max_age=60,
            event_bus=event_bus
        )
        
        # Check initialization
        assert manager.cache_dir == temp_cache_dir
        assert manager.memory_cache_capacity == 10
        assert manager.cache_max_age == 60
        assert manager.event_bus == event_bus
        assert manager.cache_enabled is True
        assert manager.memory_cache_enabled is True
        assert manager.disk_cache_enabled is True
        
        # Check that the cache directory was created
        assert os.path.exists(temp_cache_dir)
    
    def test_generate_cache_key(self, cache_manager):
        """Test generating a cache key."""
        # Generate a key
        key1 = cache_manager.generate_cache_key("test", {"a": 1, "b": 2})
        
        # Check it's a hex string (MD5 hash)
        assert isinstance(key1, str)
        assert all(c in "0123456789abcdef" for c in key1)
        assert len(key1) == 32  # MD5 hash length
        
        # Check that same input produces same key
        key2 = cache_manager.generate_cache_key("test", {"a": 1, "b": 2})
        assert key1 == key2
        
        # Check that different input produces different key
        key3 = cache_manager.generate_cache_key("test", {"a": 1, "b": 3})
        assert key1 != key3
    
    def test_put_and_get(self, cache_manager):
        """Test storing and retrieving items."""
        # Add an item
        cache_manager.put("test_key", {"data": "test_value"})
        
        # Get the item
        hit, value = cache_manager.get("test_key")
        
        # Check retrieval
        assert hit is True
        assert value == {"data": "test_value"}
        
        # Check non-existent key
        hit, value = cache_manager.get("nonexistent")
        assert hit is False
        assert value is None
    
    def test_memory_and_disk_cache(self, cache_manager, temp_cache_dir):
        """Test that items are stored in both memory and disk cache."""
        # Add an item
        cache_manager.put("test_key", {"data": "test_value"})
        
        # Check it's in memory cache
        hit, _ = cache_manager.memory_cache.get("test_key")
        assert hit is True
        
        # Check it's in disk cache
        disk_path = temp_cache_dir / "test_key.json"
        assert disk_path.exists()
        
        # Read disk cache file
        with open(disk_path, 'r', encoding='utf-8') as f:
            disk_data = json.load(f)
        
        assert disk_data == {"data": "test_value"}
    
    def test_memory_cache_hit(self, cache_manager):
        """Test that memory cache is checked first."""
        # Add an item
        cache_manager.put("test_key", {"data": "test_value"})
        
        # Get the item
        hit, value = cache_manager.get("test_key")
        
        # Check retrieval
        assert hit is True
        assert value == {"data": "test_value"}
        
        # Check stats
        stats = cache_manager.get_stats()
        assert stats["memory_hits"] == 1
        assert stats["disk_hits"] == 0
    
    def test_disk_cache_fallback(self, cache_manager):
        """Test that disk cache is used when item not in memory."""
        # Add an item
        cache_manager.put("test_key", {"data": "test_value"})
        
        # Clear memory cache
        cache_manager.memory_cache.clear()
        
        # Get the item
        hit, value = cache_manager.get("test_key")
        
        # Check retrieval
        assert hit is True
        assert value == {"data": "test_value"}
        
        # Check stats
        stats = cache_manager.get_stats()
        assert stats["memory_hits"] == 0
        assert stats["disk_hits"] == 1
        
        # Check item was added back to memory cache
        memory_hit, memory_value = cache_manager.memory_cache.get("test_key")
        assert memory_hit is True
        assert memory_value == {"data": "test_value"}
    
    def test_remove(self, cache_manager, temp_cache_dir):
        """Test removing items from both caches."""
        # Add an item
        cache_manager.put("test_key", {"data": "test_value"})
        
        # Check it exists in both caches
        disk_path = temp_cache_dir / "test_key.json"
        assert disk_path.exists()
        
        memory_hit, _ = cache_manager.memory_cache.get("test_key")
        assert memory_hit is True
        
        # Remove the item
        result = cache_manager.remove("test_key")
        assert result is True
        
        # Check it's gone from both caches
        assert not disk_path.exists()
        
        memory_hit, _ = cache_manager.memory_cache.get("test_key")
        assert memory_hit is False
    
    def test_clear(self, cache_manager, temp_cache_dir):
        """Test clearing the entire cache."""
        # Add multiple items
        cache_manager.put("key1", "value1")
        cache_manager.put("key2", "value2")
        cache_manager.put("key3", "value3")
        
        # Check they exist in both caches
        assert len(list(temp_cache_dir.glob("*.json"))) == 3
        assert cache_manager.memory_cache.size() == 3
        
        # Clear the cache
        cleared_count = cache_manager.clear()
        
        # Check all items were cleared
        assert cleared_count == 3  # Combined from both caches
        assert len(list(temp_cache_dir.glob("*.json"))) == 0
        assert cache_manager.memory_cache.size() == 0
    
    def test_set_capacity(self, cache_manager):
        """Test setting the memory cache capacity."""
        # Add multiple items
        for i in range(10):
            cache_manager.put(f"key{i}", f"value{i}")
        
        # Check capacity
        assert cache_manager.memory_cache_capacity == 10
        assert cache_manager.memory_cache.size() == 10
        
        # Set new capacity (smaller)
        cache_manager.set_capacity(5)
        
        # Check capacity was updated and items were evicted
        assert cache_manager.memory_cache_capacity == 5
        assert cache_manager.memory_cache.size() == 5
        
        # Check most recently added items are still there
        for i in range(5, 10):
            hit, value = cache_manager.memory_cache.get(f"key{i}")
            assert hit is True
            assert value == f"value{i}"
    
    def test_cached_decorator(self, cache_manager):
        """Test the cached decorator."""
        # Define a function that uses the cached decorator
        call_count = 0
        
        @cached(prefix="test_function")
        def test_function(a, b):
            nonlocal call_count
            call_count += 1
            return a + b
        
        # Call the function twice with same arguments
        result1 = test_function(1, 2)
        result2 = test_function(1, 2)
        
        # Check results are correct
        assert result1 == 3
        assert result2 == 3
        
        # Check function was only called once (second call used cache)
        assert call_count == 1
        
        # Call with different arguments
        result3 = test_function(2, 3)
        
        # Check result is correct
        assert result3 == 5
        
        # Check function was called again
        assert call_count == 2