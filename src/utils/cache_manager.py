"""
Cache Manager

This module provides a caching system for improving performance and reducing API calls.
It implements a two-level caching strategy with an in-memory LRU cache and disk-based
persistent cache.
"""

import os
import json
import time
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List, Callable
from collections import OrderedDict


class LRUCache:
    """
    In-memory Least Recently Used (LRU) cache.
    
    This class provides a memory-efficient cache that automatically evicts
    the least recently used items when the cache reaches its capacity.
    
    Attributes:
        capacity: Maximum number of items to store in the cache
        cache: OrderedDict of cached items, with most recently used at the end
        lock: Thread lock for synchronizing access to the cache
    """
    
    def __init__(self, capacity: int = 100):
        """
        Initialize the LRU cache.
        
        Args:
            capacity: Maximum number of items to store in the cache
        """
        self.capacity = capacity
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        
    def get(self, key: str) -> Tuple[bool, Any]:
        """
        Get an item from the cache.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Tuple of (hit, value), where hit is True if the key was found,
            and value is the cached value (or None if not found)
        """
        with self.lock:
            if key not in self.cache:
                return False, None
            
            # Move the accessed item to the end (most recently used)
            value = self.cache.pop(key)
            self.cache[key] = value
            return True, value
    
    def put(self, key: str, value: Any) -> None:
        """
        Add or update an item in the cache.
        
        Args:
            key: Cache key to store
            value: Value to cache
        """
        with self.lock:
            # Remove the key if it already exists
            if key in self.cache:
                self.cache.pop(key)
            
            # If at capacity, remove the first item (least recently used)
            if len(self.cache) >= self.capacity:
                self.cache.popitem(last=False)
            
            # Add the new key-value pair
            self.cache[key] = value
    
    def remove(self, key: str) -> bool:
        """
        Remove an item from the cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if the key was removed, False if it wasn't in the cache
        """
        with self.lock:
            if key in self.cache:
                self.cache.pop(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear the entire cache."""
        with self.lock:
            self.cache.clear()
    
    def get_keys(self) -> List[str]:
        """
        Get all keys in the cache.
        
        Returns:
            List of keys in the cache
        """
        with self.lock:
            return list(self.cache.keys())
    
    def size(self) -> int:
        """
        Get the current size of the cache.
        
        Returns:
            Number of items in the cache
        """
        with self.lock:
            return len(self.cache)


class CacheManager:
    """
    Two-level caching system with in-memory and disk storage.
    
    This class provides a comprehensive caching solution that combines the speed
    of in-memory caching with the persistence of disk-based storage, optimizing
    both performance and resource usage.
    
    Attributes:
        memory_cache: LRU cache for fast in-memory access
        cache_dir: Directory for disk-based cache storage
        event_bus: Event system for cache-related notifications
        cache_enabled: Whether caching is enabled
        disk_cache_enabled: Whether disk caching is enabled
        memory_cache_enabled: Whether memory caching is enabled
        cache_max_age: Maximum age of cache entries in seconds
        memory_cache_capacity: Maximum number of items in memory cache
        cache_stats: Statistics for monitoring cache performance
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        memory_cache_capacity: int = 100,
        cache_max_age: int = 24 * 60 * 60,  # 24 hours in seconds
        event_bus = None
    ):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory for disk-based cache storage
            memory_cache_capacity: Maximum number of items in memory cache
            cache_max_age: Maximum age of cache entries in seconds
            event_bus: Optional event bus for notifications
        """
        # Set up memory cache
        self.memory_cache = LRUCache(capacity=memory_cache_capacity)
        
        # Set up disk cache
        if cache_dir is None:
            app_root = Path(__file__).parent.parent.parent.absolute()
            self.cache_dir = app_root / 'cache'
        else:
            self.cache_dir = cache_dir
            
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Set event bus
        self.event_bus = event_bus
        
        # Cache settings
        self.cache_enabled = True
        self.disk_cache_enabled = True
        self.memory_cache_enabled = True
        self.cache_max_age = cache_max_age
        self.memory_cache_capacity = memory_cache_capacity
        
        # Cache statistics
        self.cache_stats = {
            'memory_hits': 0,
            'disk_hits': 0,
            'misses': 0,
            'errors': 0
        }
        
        # Periodically clean up expired disk cache entries
        self._schedule_cleanup()
    
    def generate_cache_key(self, prefix: str, data: Dict[str, Any]) -> str:
        """
        Generate a cache key for the given data.
        
        Args:
            prefix: Prefix for the cache key (e.g., 'lemma', 'entry')
            data: Data to hash for the cache key
            
        Returns:
            Unique cache key for the data
        """
        # Create a string representation of the data
        data_str = json.dumps(data, sort_keys=True)
        key_data = f"{prefix}:{data_str}"
        
        # Generate a hash for the key
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Tuple[bool, Any]:
        """
        Get an item from the cache.
        
        First checks the memory cache, then falls back to the disk cache.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Tuple of (hit, value), where hit is True if the key was found,
            and value is the cached value (or None if not found)
        """
        if not self.cache_enabled:
            return False, None
        
        # Try memory cache first (if enabled)
        if self.memory_cache_enabled:
            memory_hit, value = self.memory_cache.get(key)
            if memory_hit:
                self.cache_stats['memory_hits'] += 1
                
                # Publish event if needed
                if self.event_bus:
                    self.event_bus.publish('cache:memory_hit', {
                        'cache_key': key
                    })
                    
                return True, value
        
        # If not in memory and disk cache is enabled, try disk
        if self.disk_cache_enabled:
            disk_hit, value = self._get_from_disk(key)
            if disk_hit:
                self.cache_stats['disk_hits'] += 1
                
                # Add to memory cache for future access
                if self.memory_cache_enabled:
                    self.memory_cache.put(key, value)
                
                # Publish event if needed
                if self.event_bus:
                    self.event_bus.publish('cache:disk_hit', {
                        'cache_key': key
                    })
                    
                return True, value
        
        # Not found in either cache
        self.cache_stats['misses'] += 1
        return False, None
    
    def put(self, key: str, value: Any) -> None:
        """
        Add or update an item in the cache.
        
        Stores the item in both memory and disk caches if enabled.
        
        Args:
            key: Cache key to store
            value: Value to cache
        """
        if not self.cache_enabled:
            return
        
        # Store in memory cache if enabled
        if self.memory_cache_enabled:
            self.memory_cache.put(key, value)
        
        # Store in disk cache if enabled
        if self.disk_cache_enabled:
            self._save_to_disk(key, value)
        
        # Publish event if needed
        if self.event_bus:
            self.event_bus.publish('cache:item_added', {
                'cache_key': key
            })
    
    def remove(self, key: str) -> bool:
        """
        Remove an item from both memory and disk caches.
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if the key was removed from at least one cache
        """
        removed = False
        
        # Remove from memory cache
        if self.memory_cache_enabled:
            if self.memory_cache.remove(key):
                removed = True
        
        # Remove from disk cache
        if self.disk_cache_enabled:
            disk_path = self._get_disk_path(key)
            if disk_path.exists():
                try:
                    disk_path.unlink()
                    removed = True
                except Exception as e:
                    if self.event_bus:
                        self.event_bus.publish('error:cache', {
                            'message': f"Error removing disk cache item: {str(e)}",
                            'cache_key': key
                        })
        
        # Publish event if needed
        if removed and self.event_bus:
            self.event_bus.publish('cache:item_removed', {
                'cache_key': key
            })
            
        return removed
    
    def clear(self, older_than_days: Optional[int] = None) -> int:
        """
        Clear items from both memory and disk caches.
        
        Args:
            older_than_days: Only clear items older than this many days
                            (only applies to disk cache, memory cache is completely cleared)
            
        Returns:
            Number of items cleared from both caches
        """
        cleared_count = 0
        
        # Clear memory cache
        if self.memory_cache_enabled:
            memory_size = self.memory_cache.size()
            self.memory_cache.clear()
            cleared_count += memory_size
        
        # Clear disk cache
        if self.disk_cache_enabled:
            disk_cleared = self._clear_disk_cache(older_than_days)
            cleared_count += disk_cleared
        
        # Publish event if needed
        if self.event_bus:
            self.event_bus.publish('cache:cleared', {
                'count': cleared_count,
                'older_than_days': older_than_days
            })
            
        return cleared_count
    
    def set_capacity(self, memory_capacity: int) -> None:
        """
        Set the capacity of the memory cache.
        
        Args:
            memory_capacity: New maximum number of items in memory cache
        """
        # Create a new memory cache with the new capacity
        new_cache = LRUCache(capacity=memory_capacity)
        
        # Copy items from the old cache to the new one (most recently used first)
        keys = self.memory_cache.get_keys()
        for key in reversed(keys):
            _, value = self.memory_cache.get(key)
            new_cache.put(key, value)
        
        # Replace the old cache with the new one
        self.memory_cache = new_cache
        self.memory_cache_capacity = memory_capacity
        
        # Publish event if needed
        if self.event_bus:
            self.event_bus.publish('cache:capacity_changed', {
                'memory_capacity': memory_capacity
            })
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics and status.
        
        Returns:
            Dictionary of cache statistics and status information
        """
        total_hits = self.cache_stats['memory_hits'] + self.cache_stats['disk_hits']
        total_requests = total_hits + self.cache_stats['misses']
        hit_rate = (total_hits / total_requests) * 100 if total_requests > 0 else 0
        
        return {
            'enabled': self.cache_enabled,
            'memory_enabled': self.memory_cache_enabled,
            'disk_enabled': self.disk_cache_enabled,
            'memory_capacity': self.memory_cache_capacity,
            'memory_size': self.memory_cache.size(),
            'memory_hits': self.cache_stats['memory_hits'],
            'disk_hits': self.cache_stats['disk_hits'],
            'misses': self.cache_stats['misses'],
            'errors': self.cache_stats['errors'],
            'hit_rate': hit_rate,
            'max_age_seconds': self.cache_max_age
        }
    
    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self.cache_stats = {
            'memory_hits': 0,
            'disk_hits': 0,
            'misses': 0,
            'errors': 0
        }
    
    def _get_disk_path(self, key: str) -> Path:
        """
        Get the disk path for a cache key.
        
        Args:
            key: Cache key
            
        Returns:
            Path object for the cache file
        """
        return self.cache_dir / f"{key}.json"
    
    def _get_from_disk(self, key: str) -> Tuple[bool, Any]:
        """
        Get an item from the disk cache.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Tuple of (hit, value), where hit is True if the key was found
            and not expired, and value is the cached value (or None if not found)
        """
        disk_path = self._get_disk_path(key)
        if not disk_path.exists():
            return False, None
        
        try:
            # Check if the file is expired
            file_mod_time = datetime.fromtimestamp(disk_path.stat().st_mtime)
            if datetime.now() - file_mod_time > timedelta(seconds=self.cache_max_age):
                # Cache expired, remove it
                try:
                    disk_path.unlink()
                except:
                    pass
                return False, None
            
            # Read and parse the cache file
            with open(disk_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            return True, cache_data
            
        except Exception as e:
            self.cache_stats['errors'] += 1
            
            if self.event_bus:
                self.event_bus.publish('error:cache', {
                    'message': f"Error reading from disk cache: {str(e)}",
                    'cache_key': key
                })
                
            return False, None
    
    def _save_to_disk(self, key: str, value: Any) -> bool:
        """
        Save an item to the disk cache.
        
        Args:
            key: Cache key to store
            value: Value to cache
            
        Returns:
            True if successful, False if there was an error
        """
        disk_path = self._get_disk_path(key)
        try:
            # Ensure the cache directory exists
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Write to the cache file
            with open(disk_path, 'w', encoding='utf-8') as f:
                json.dump(value, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            self.cache_stats['errors'] += 1
            
            if self.event_bus:
                self.event_bus.publish('error:cache', {
                    'message': f"Error writing to disk cache: {str(e)}",
                    'cache_key': key
                })
                
            return False
    
    def _clear_disk_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Clear items from the disk cache.
        
        Args:
            older_than_days: Only clear items older than this many days
            
        Returns:
            Number of items cleared from the disk cache
        """
        cleared_count = 0
        
        try:
            for cache_file in self.cache_dir.glob('*.json'):
                # Check age if filter specified
                if older_than_days is not None:
                    file_mod_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    age_days = (datetime.now() - file_mod_time).days
                    
                    if age_days < older_than_days:
                        continue
                        
                # Delete the cache file
                try:
                    cache_file.unlink()
                    cleared_count += 1
                except:
                    continue
        
        except Exception as e:
            self.cache_stats['errors'] += 1
            
            if self.event_bus:
                self.event_bus.publish('error:cache', {
                    'message': f"Error clearing disk cache: {str(e)}"
                })
                
        return cleared_count
    
    def _schedule_cleanup(self) -> None:
        """Schedule periodic cleanup of expired cache entries."""
        def _cleanup():
            # Clear expired disk cache entries
            self._clear_disk_cache(older_than_days=self.cache_max_age / (24 * 60 * 60))
            
            # Schedule the next cleanup
            threading.Timer(3600, _cleanup).start()  # Run every hour
        
        # Start the first cleanup after 1 hour
        threading.Timer(3600, _cleanup).start()


# Create singleton instance for global use
cache_manager = CacheManager()

# Decorator for caching function results
def cached(prefix: str, key_args: List[str] = None, expiry: int = None):
    """
    Decorator for caching function results.
    
    Args:
        prefix: Prefix for the cache key
        key_args: List of argument names to include in the cache key
        expiry: Custom expiry time in seconds (overrides default)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create a dictionary of all arguments
            all_args = {}
            
            # Add positional arguments using function's parameter names
            if args:
                import inspect
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                
                for i, arg in enumerate(args):
                    if i < len(param_names):
                        all_args[param_names[i]] = arg
            
            # Add keyword arguments
            all_args.update(kwargs)
            
            # Filter arguments for the cache key if key_args specified
            cache_args = {}
            if key_args:
                for arg_name in key_args:
                    if arg_name in all_args:
                        cache_args[arg_name] = all_args[arg_name]
            else:
                # Use all arguments except those that can't be serialized
                for k, v in all_args.items():
                    if isinstance(v, (str, int, float, bool, list, dict, tuple)):
                        cache_args[k] = v
            
            # Generate cache key
            cache_key = cache_manager.generate_cache_key(prefix, cache_args)
            
            # Check cache
            hit, value = cache_manager.get(cache_key)
            if hit:
                return value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            
            # Only cache if result is not None
            if result is not None:
                cache_manager.put(cache_key, result)
            
            return result
        
        return wrapper
    
    return decorator