"""
Base View

This module provides a base class for all view components in the application,
establishing a common interface and shared functionality.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, Callable

class BaseView:
    """
    Base class for all view components.
    
    This class provides common functionality for UI components including
    event handling, styling, and lifecycle management.
    
    Attributes:
        parent: The parent widget or window
        event_bus: Event system for view-related notifications
        frame: The main frame containing this view's widgets
    """
    
    def __init__(
        self, 
        parent,
        event_bus=None,
        **kwargs
    ):
        """
        Initialize the base view.
        
        Args:
            parent: The parent widget or window
            event_bus: Optional event bus for notifications
            **kwargs: Additional keyword arguments for customization
        """
        self.parent = parent
        self.event_bus = event_bus
        self.frame = None
        self.widgets = {}
        self.event_handlers = {}
        
        # Default styling options
        self.style_options = {
            'padx': kwargs.get('padx', 5),
            'pady': kwargs.get('pady', 5),
            'bg': kwargs.get('bg', None),
            'border_width': kwargs.get('border_width', 0),
            'relief': kwargs.get('relief', tk.FLAT),
            'width': kwargs.get('width', None),
            'height': kwargs.get('height', None)
        }
        
        # Scale factor for text and UI elements
        self.scale_factor = kwargs.get('scale_factor', 1.0)
        
        # Create the view frame
        self._create_frame()
        
        # Register for scale factor updates if event bus provided
        if self.event_bus:
            self.event_bus.subscribe('ui:scale_factor_changed', self._on_scale_factor_changed)
    
    def _create_frame(self):
        """Create the main frame for this view."""
        options = {}
        
        # Apply style options
        if self.style_options['bg']:
            options['background'] = self.style_options['bg']
            
        if self.style_options['border_width']:
            options['borderwidth'] = self.style_options['border_width']
            
        if self.style_options['relief']:
            options['relief'] = self.style_options['relief']
            
        if self.style_options['width']:
            options['width'] = self.style_options['width']
            
        if self.style_options['height']:
            options['height'] = self.style_options['height']
            
        # Create the frame
        self.frame = ttk.Frame(self.parent, **options)
    
    def pack(self, **kwargs):
        """
        Pack the view frame using the pack geometry manager.
        
        Args:
            **kwargs: Arguments to pass to the pack method
        """
        pack_options = {
            'padx': self.style_options['padx'],
            'pady': self.style_options['pady'],
            'fill': kwargs.get('fill', tk.BOTH),
            'expand': kwargs.get('expand', True),
            'side': kwargs.get('side', tk.TOP)
        }
        
        # Override with any provided kwargs
        pack_options.update(kwargs)
        
        # Pack the frame
        self.frame.pack(**pack_options)
    
    def grid(self, **kwargs):
        """
        Grid the view frame using the grid geometry manager.
        
        Args:
            **kwargs: Arguments to pass to the grid method
        """
        grid_options = {
            'padx': self.style_options['padx'],
            'pady': self.style_options['pady'],
            'sticky': kwargs.get('sticky', 'nsew')
        }
        
        # Override with any provided kwargs
        grid_options.update(kwargs)
        
        # Grid the frame
        self.frame.grid(**grid_options)
    
    def place(self, **kwargs):
        """
        Place the view frame using the place geometry manager.
        
        Args:
            **kwargs: Arguments to pass to the place method
        """
        # Place the frame
        self.frame.place(**kwargs)
    
    def hide(self):
        """Hide the view by removing it from the layout manager."""
        self.frame.pack_forget() if hasattr(self.frame, 'pack_info') else None
        self.frame.grid_forget() if hasattr(self.frame, 'grid_info') else None
        self.frame.place_forget() if hasattr(self.frame, 'place_info') else None
    
    def show(self):
        """
        Show the view using its previous layout configuration.
        
        This is a convenience method that attempts to restore the previous
        layout. For more precise control, use pack(), grid(), or place().
        """
        # Try to determine the previous layout manager
        if hasattr(self.frame, 'pack_info') and self.frame.pack_info():
            self.frame.pack()
        elif hasattr(self.frame, 'grid_info') and self.frame.grid_info():
            self.frame.grid()
        elif hasattr(self.frame, 'place_info') and self.frame.place_info():
            self.frame.place()
        else:
            # Default to pack if no previous layout info
            self.frame.pack(fill=tk.BOTH, expand=True)
    
    def register_event_handler(self, event_name: str, handler: Callable):
        """
        Register an event handler function.
        
        Args:
            event_name: Name of the event to handle
            handler: Function to call when the event occurs
        """
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
            
        self.event_handlers[event_name].append(handler)
        
        # Subscribe to the event if event bus is available
        if self.event_bus:
            self.event_bus.subscribe(event_name, self._handle_event)
    
    def unregister_event_handler(self, event_name: str, handler: Callable):
        """
        Unregister an event handler function.
        
        Args:
            event_name: Name of the event
            handler: Function to unregister
        """
        if event_name in self.event_handlers and handler in self.event_handlers[event_name]:
            self.event_handlers[event_name].remove(handler)
            
            # If no more handlers for this event, unsubscribe
            if not self.event_handlers[event_name] and self.event_bus:
                self.event_bus.unsubscribe(event_name, self._handle_event)
    
    def _handle_event(self, event_data: Optional[Dict[str, Any]] = None):
        """
        Handle an event by calling all registered handlers.
        
        Args:
            event_data: Data associated with the event
        """
        # Get the event name from the event_bus callback data
        event_name = None
        if self.event_bus:
            event_name = self.event_bus.current_event
            
        if not event_name:
            return
            
        # Call all handlers for this event
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    handler(event_data)
                except Exception as e:
                    print(f"Error in event handler for {event_name}: {str(e)}")
    
    def _on_scale_factor_changed(self, data: Dict[str, Any]):
        """
        Handle changes to the UI scale factor.
        
        Args:
            data: Event data including the new scale factor
        """
        if 'scale_factor' in data:
            self.scale_factor = data['scale_factor']
            self.update_scale()
    
    def update_scale(self):
        """
        Update UI elements based on the current scale factor.
        
        This method should be overridden by subclasses to implement
        scaling behavior for specific UI components.
        """
        pass
    
    def destroy(self):
        """Clean up resources and destroy the view."""
        # Unsubscribe from events
        if self.event_bus:
            self.event_bus.unsubscribe('ui:scale_factor_changed', self._on_scale_factor_changed)
            
            # Unsubscribe from all registered events
            for event_name in self.event_handlers:
                self.event_bus.unsubscribe(event_name, self._handle_event)
                
        # Destroy the frame
        if self.frame:
            self.frame.destroy()
            self.frame = None