import threading
from typing import Dict, List, Callable, Any, Optional

class EventBus:
    """
    Centralized event bus for communication between application components.
    
    The EventBus implements a publisher-subscriber pattern that allows components
    to communicate without direct dependencies on each other. This promotes loose
    coupling and makes the codebase more modular and testable.
    
    Usage:
        # Create an event bus
        event_bus = EventBus()
        
        # Subscribe to events
        event_bus.subscribe("search:completed", on_search_completed)
        
        # Publish events
        event_bus.publish("search:completed", {"word": "hello", "results": [...]})
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self.subscribers: Dict[str, List[Callable]] = {}
        self.lock = threading.RLock()
    
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """
        Subscribe to an event type with a callback function.
        
        Args:
            event_type: The type of event to subscribe to
            callback: Function to call when event is published
        """
        with self.lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            
            if callback not in self.subscribers[event_type]:
                self.subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: The type of event to unsubscribe from
            callback: The callback function to remove
            
        Returns:
            bool: True if the subscription was removed, False otherwise
        """
        with self.lock:
            if event_type in self.subscribers and callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
                return True
        return False
    
    def publish(self, event_type: str, data: Optional[Any] = None) -> int:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: The type of event to publish
            data: Data to pass to subscribers (optional)
            
        Returns:
            int: Number of subscribers notified
        """
        if event_type not in self.subscribers:
            return 0
            
        count = 0
        # Make a copy of the subscriber list to avoid issues if callbacks modify subscriptions
        with self.lock:
            subscribers = self.subscribers[event_type].copy()
            
        for callback in subscribers:
            try:
                callback(data)
                count += 1
            except Exception as e:
                print(f"Error in event handler for {event_type}: {str(e)}")
                
        return count
    
    def publish_async(self, event_type: str, data: Optional[Any] = None) -> None:
        """
        Publish an event asynchronously (in a separate thread).
        
        Args:
            event_type: The type of event to publish
            data: Data to pass to subscribers (optional)
        """
        thread = threading.Thread(
            target=self.publish,
            args=(event_type, data),
            daemon=True
        )
        thread.start()
        
    def clear_all_subscriptions(self) -> None:
        """Clear all event subscriptions."""
        with self.lock:
            self.subscribers.clear()
    
    def clear_event_subscriptions(self, event_type: str) -> bool:
        """
        Clear all subscriptions for a specific event type.
        
        Args:
            event_type: The event type to clear
            
        Returns:
            bool: True if the event type existed and was cleared, False otherwise
        """
        with self.lock:
            if event_type in self.subscribers:
                del self.subscribers[event_type]
                return True
        return False
    
    def get_subscriber_count(self, event_type: str) -> int:
        """
        Get the number of subscribers for an event type.
        
        Args:
            event_type: The event type to check
            
        Returns:
            int: Number of subscribers
        """
        with self.lock:
            if event_type in self.subscribers:
                return len(self.subscribers[event_type])
        return 0