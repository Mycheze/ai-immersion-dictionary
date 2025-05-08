"""
Main Window View

This module provides the main application window view, which serves as the
container for all other view components.
"""

import tkinter as tk
from tkinter import ttk, Menu
from typing import Dict, Any, Optional, List, Callable

from .base_view import BaseView

class MainWindowView(BaseView):
    """
    Main application window view.
    
    This class represents the main window of the application and serves as
    the container for all other view components.
    
    Attributes:
        root: The root tkinter window
        event_bus: Event system for view-related notifications
        menu_bar: The main menu bar
        status_bar: The status bar at the bottom of the window
        content_frame: The main content frame
    """
    
    def __init__(
        self,
        root,
        event_bus=None,
        title="AI-Powered Dictionary",
        geometry="1400x900",  # Increased initial window size
        min_width=1200,  # Further increased minimum width for better content display
        min_height=800,  # Further increased minimum height for better content display
        **kwargs
    ):
        """
        Initialize the main window view.
        
        Args:
            root: The root tkinter window
            event_bus: Optional event bus for notifications
            title: Window title
            geometry: Initial window size (WxH)
            min_width: Minimum window width
            min_height: Minimum window height
            **kwargs: Additional keyword arguments
        """
        self.root = root
        
        # Initialize base view with root as parent
        super().__init__(root, event_bus, **kwargs)
        
        # Set window properties
        self.root.title(title)
        self.root.geometry(geometry)
        self.root.minsize(min_width, min_height)
        
        # Track running tasks
        self.running_tasks = {}
        self.active_task_id = None
        
        # Create UI components
        self._create_menu_bar()
        self._create_content_frame()
        self._create_status_bar()
        
        # Track window state
        self.is_fullscreen = False
        
        # Set up keyboard shortcuts
        self._setup_keyboard_shortcuts()
        
        # Track child views
        self.child_views = {}
        
        # Configure grid layout
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Register event handlers
        self._register_event_handlers()
    
    def _create_menu_bar(self):
        """Create the main menu bar."""
        self.menu_bar = Menu(self.root)
        self.root.config(menu=self.menu_bar)
        
        # File menu
        self.file_menu = Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Export Dictionary...", command=self._on_export_dictionary)
        self.file_menu.add_command(label="Import Dictionary...", command=self._on_import_dictionary)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Settings", command=self._on_open_settings)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self._on_exit)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        
        # Edit menu
        self.edit_menu = Menu(self.menu_bar, tearoff=0)
        self.edit_menu.add_command(label="Copy", command=self._on_copy)
        self.edit_menu.add_command(label="Paste", command=self._on_paste)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Clear History", command=self._on_clear_history)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        
        # View menu
        self.view_menu = Menu(self.menu_bar, tearoff=0)
        
        # Text size submenu
        self.text_size_menu = Menu(self.view_menu, tearoff=0)
        self.text_size_menu.add_command(label="Increase Text Size", command=self._on_increase_text_size)
        self.text_size_menu.add_command(label="Decrease Text Size", command=self._on_decrease_text_size)
        self.text_size_menu.add_command(label="Reset Text Size", command=self._on_reset_text_size)
        self.view_menu.add_cascade(label="Text Size", menu=self.text_size_menu)
        
        # Layout options
        self.view_menu.add_command(label="Toggle Fullscreen", command=self._on_toggle_fullscreen)
        self.view_menu.add_separator()
        
        # View options
        self.show_phonetics_var = tk.BooleanVar(value=True)
        self.view_menu.add_checkbutton(
            label="Show Phonetics",
            variable=self.show_phonetics_var,
            command=self._on_toggle_phonetics
        )
        
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        
        # Anki menu
        self.anki_menu = Menu(self.menu_bar, tearoff=0)
        self.anki_menu.add_command(label="Configure Anki Integration", command=self._on_configure_anki)
        self.anki_menu.add_separator()
        self.anki_menu.add_command(label="Connect to Anki", command=self._on_connect_anki)
        self.anki_menu.add_command(label="Test Connection", command=self._on_test_anki_connection)
        self.menu_bar.add_cascade(label="Anki", menu=self.anki_menu)
        
        # Help menu
        self.help_menu = Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="Documentation", command=self._on_open_docs)
        self.help_menu.add_command(label="About", command=self._on_open_about)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
    
    def _create_content_frame(self):
        """Create the main content frame."""
        # Use the frame from BaseView as main container
        content_frame = self.frame
        content_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid layout
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
    
    def _create_status_bar(self):
        """Create the status bar at the bottom of the window."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.grid(row=1, column=0, sticky="ew")
        
        # Status message label
        self.status_message_var = tk.StringVar(value="Ready")
        self.status_message_label = ttk.Label(
            self.status_bar,
            textvariable=self.status_message_var,
            anchor=tk.W,
            padding=(5, 2)
        )
        self.status_message_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Progress indicator frame
        self.progress_frame = ttk.Frame(self.status_bar)
        self.progress_frame.pack(side=tk.RIGHT, padx=5)
        
        # Progress indicator
        self.progress_var = tk.IntVar(value=0)
        self.progress_indicator = ttk.Progressbar(
            self.progress_frame,
            variable=self.progress_var,
            orient=tk.HORIZONTAL,
            length=100,
            mode='determinate'
        )
        self.progress_indicator.pack(side=tk.RIGHT)
        
        # Initially hide progress indicator
        self.progress_frame.pack_forget()
        
        # Task count indicator
        self.task_count_var = tk.StringVar(value="")
        self.task_count_label = ttk.Label(
            self.status_bar,
            textvariable=self.task_count_var,
            padding=(5, 2)
        )
        self.task_count_label.pack(side=tk.RIGHT)
        
        # API status indicator
        self.api_status_var = tk.StringVar(value="API: Disconnected")
        self.api_status_label = ttk.Label(
            self.status_bar,
            textvariable=self.api_status_var,
            padding=(5, 2)
        )
        self.api_status_label.pack(side=tk.RIGHT)
        
        # Anki status indicator
        self.anki_status_var = tk.StringVar(value="Anki: Disconnected")
        self.anki_status_label = ttk.Label(
            self.status_bar,
            textvariable=self.anki_status_var,
            padding=(5, 2)
        )
        self.anki_status_label.pack(side=tk.RIGHT)
        
        # Scale factor indicator
        self.scale_factor_var = tk.StringVar(value="Scale: 100%")
        self.scale_factor_label = ttk.Label(
            self.status_bar,
            textvariable=self.scale_factor_var,
            padding=(5, 2)
        )
        self.scale_factor_label.pack(side=tk.RIGHT)
    
    def _setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts for the application."""
        # Bind common shortcuts
        self.root.bind("<Control-q>", lambda e: self._on_exit())
        self.root.bind("<Control-plus>", lambda e: self._on_increase_text_size())
        self.root.bind("<Control-minus>", lambda e: self._on_decrease_text_size())
        self.root.bind("<Control-0>", lambda e: self._on_reset_text_size())
        self.root.bind("<F11>", lambda e: self._on_toggle_fullscreen())
        self.root.bind("<Escape>", self._on_escape_pressed)
    
    def add_view(self, name: str, view):
        """
        Add a child view to the main window.
        
        Args:
            name: Name to identify the view
            view: The view object to add
        """
        self.child_views[name] = view
        
        # Notify that a view was added
        if self.event_bus:
            self.event_bus.publish('view:added', {
                'name': name,
                'view': view
            })
    
    def remove_view(self, name: str):
        """
        Remove a child view from the main window.
        
        Args:
            name: Name of the view to remove
        """
        if name in self.child_views:
            view = self.child_views[name]
            view.destroy()
            del self.child_views[name]
            
            # Notify that a view was removed
            if self.event_bus:
                self.event_bus.publish('view:removed', {
                    'name': name
                })
    
    def get_view(self, name: str):
        """
        Get a child view by name.
        
        Args:
            name: Name of the view to get
            
        Returns:
            The view object or None if not found
        """
        return self.child_views.get(name)
    
    def set_status_message(self, message: str, duration: int = 0):
        """
        Set the status bar message.
        
        Args:
            message: Message to display
            duration: Duration in milliseconds (0 for permanent)
        """
        self.status_message_var.set(message)
        
        # Clear after duration if specified
        if duration > 0:
            self.root.after(duration, lambda: self.status_message_var.set("Ready"))
    
    def set_api_status(self, connected: bool, message: Optional[str] = None):
        """
        Set the API connection status.
        
        Args:
            connected: Whether the API is connected
            message: Optional status message
        """
        if connected:
            status = "API: Connected"
            if message:
                status += f" ({message})"
            self.api_status_var.set(status)
            self.api_status_label.configure(foreground="green")
        else:
            status = "API: Disconnected"
            if message:
                status += f" ({message})"
            self.api_status_var.set(status)
            self.api_status_label.configure(foreground="red")
    
    def set_anki_status(self, connected: bool, message: Optional[str] = None):
        """
        Set the Anki connection status.
        
        Args:
            connected: Whether Anki is connected
            message: Optional status message
        """
        if connected:
            status = "Anki: Connected"
            if message:
                status += f" ({message})"
            self.anki_status_var.set(status)
            self.anki_status_label.configure(foreground="green")
        else:
            status = "Anki: Disconnected"
            if message:
                status += f" ({message})"
            self.anki_status_var.set(status)
            self.anki_status_label.configure(foreground="red")
    
    def update_scale(self):
        """Update UI elements based on the current scale factor."""
        # Update scale factor indicator
        scale_percent = int(self.scale_factor * 100)
        self.scale_factor_var.set(f"Scale: {scale_percent}%")
        
        # Update child views
        for view in self.child_views.values():
            if hasattr(view, 'update_scale'):
                view.update_scale()
                
        # Notify of scale change
        if self.event_bus:
            self.event_bus.publish('ui:scale_factor_changed', {
                'scale_factor': self.scale_factor
            })
    
    def on_closing(self):
        """Handle window closing event."""
        # Notify of window closing
        if self.event_bus:
            self.event_bus.publish('window:closing', {})
            
        # Destroy all child views
        for name in list(self.child_views.keys()):
            self.remove_view(name)
            
        # Destroy the root window
        self.root.destroy()
    
    # Event handlers
    
    def _on_export_dictionary(self):
        """Handle export dictionary menu action."""
        if self.event_bus:
            self.event_bus.publish('action:export_dictionary', {})
    
    def _on_import_dictionary(self):
        """Handle import dictionary menu action."""
        if self.event_bus:
            self.event_bus.publish('action:import_dictionary', {})
    
    def _on_open_settings(self):
        """Handle open settings menu action."""
        if self.event_bus:
            self.event_bus.publish('action:open_settings', {})
    
    def _on_exit(self):
        """Handle exit menu action."""
        self.on_closing()
    
    def _on_copy(self):
        """Handle copy menu action."""
        if self.event_bus:
            self.event_bus.publish('action:copy', {})
    
    def _on_paste(self):
        """Handle paste menu action."""
        if self.event_bus:
            self.event_bus.publish('action:paste', {})
    
    def _on_clear_history(self):
        """Handle clear history menu action."""
        if self.event_bus:
            self.event_bus.publish('action:clear_history', {})
    
    def _on_increase_text_size(self):
        """Handle increase text size menu action."""
        self.scale_factor = min(2.0, self.scale_factor + 0.1)
        self.update_scale()
        
        if self.event_bus:
            self.event_bus.publish('action:increase_text_size', {
                'scale_factor': self.scale_factor
            })
    
    def _on_decrease_text_size(self):
        """Handle decrease text size menu action."""
        self.scale_factor = max(0.5, self.scale_factor - 0.1)
        self.update_scale()
        
        if self.event_bus:
            self.event_bus.publish('action:decrease_text_size', {
                'scale_factor': self.scale_factor
            })
    
    def _on_reset_text_size(self):
        """Handle reset text size menu action."""
        self.scale_factor = 1.0
        self.update_scale()
        
        if self.event_bus:
            self.event_bus.publish('action:reset_text_size', {
                'scale_factor': self.scale_factor
            })
    
    def _on_toggle_fullscreen(self):
        """Handle toggle fullscreen menu action."""
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes('-fullscreen', self.is_fullscreen)
        
        if self.event_bus:
            self.event_bus.publish('action:toggle_fullscreen', {
                'fullscreen': self.is_fullscreen
            })
    
    def _on_toggle_phonetics(self):
        """Handle toggle phonetics menu action."""
        if self.event_bus:
            self.event_bus.publish('action:toggle_phonetics', {
                'show_phonetics': self.show_phonetics_var.get()
            })
    
    def _on_configure_anki(self):
        """Handle configure Anki menu action."""
        if self.event_bus:
            self.event_bus.publish('action:configure_anki', {})
    
    def _on_connect_anki(self):
        """Handle connect to Anki menu action."""
        if self.event_bus:
            self.event_bus.publish('action:connect_anki', {})
    
    def _on_test_anki_connection(self):
        """Handle test Anki connection menu action."""
        if self.event_bus:
            self.event_bus.publish('action:test_anki_connection', {})
    
    def _on_open_docs(self):
        """Handle open documentation menu action."""
        if self.event_bus:
            self.event_bus.publish('action:open_docs', {})
    
    def _on_open_about(self):
        """Handle open about menu action."""
        if self.event_bus:
            self.event_bus.publish('action:open_about', {})
    
    def _on_escape_pressed(self, event):
        """Handle escape key press."""
        # Exit fullscreen if in fullscreen mode
        if self.is_fullscreen:
            self._on_toggle_fullscreen()
            return "break"  # Prevent further handling
        
        # Let event propagate otherwise
        return None
        
    # Progress indicator methods
    
    def show_progress(self, visible: bool = True):
        """Show or hide the progress indicator."""
        if visible:
            self.progress_frame.pack(side=tk.RIGHT, padx=5)
        else:
            self.progress_frame.pack_forget()
    
    def set_progress(self, value: int):
        """Set the progress indicator value (0-100)."""
        self.progress_var.set(value)
    
    def update_task_count(self):
        """Update the task count indicator."""
        pending_count = len(self.running_tasks)
        
        if pending_count > 0:
            self.task_count_var.set(f"Tasks: {pending_count}")
            self.task_count_label.configure(foreground="blue")
        else:
            self.task_count_var.set("")
    
    def _register_event_handlers(self):
        """Register event handlers for the main window."""
        # Async operation events
        self.register_event_handler('task:submitted', self._on_task_submitted)
        self.register_event_handler('task:started', self._on_task_started)
        self.register_event_handler('task:completed', self._on_task_completed)
        self.register_event_handler('task:failed', self._on_task_failed)
        self.register_event_handler('task:cancelled', self._on_task_cancelled)
        self.register_event_handler('task:progress', self._on_task_progress)
        self.register_event_handler('tasks:cleared', self._on_tasks_cleared)
    
    # Async task event handlers
    
    def _on_task_submitted(self, data):
        """Handle task submitted event."""
        if not data:
            return
            
        task_id = data.get('task_id')
        name = data.get('name', 'Unknown task')
        
        if task_id:
            # Add to running tasks
            self.running_tasks[task_id] = {
                'name': name,
                'status': 'pending',
                'progress': 0
            }
            
            # Update UI
            self.update_task_count()
    
    def _on_task_started(self, data):
        """Handle task started event."""
        if not data:
            return
            
        task_id = data.get('task_id')
        name = data.get('name', 'Unknown task')
        
        if task_id and task_id in self.running_tasks:
            # Update task status
            self.running_tasks[task_id]['status'] = 'running'
            
            # Set as active task
            self.active_task_id = task_id
            
            # Update UI
            self.set_status_message(f"Running: {name}...")
            self.show_progress(True)
            self.set_progress(0)
    
    def _on_task_completed(self, data):
        """Handle task completed event."""
        if not data:
            return
            
        task_id = data.get('task_id')
        
        if task_id and task_id in self.running_tasks:
            # Remove from running tasks
            name = self.running_tasks[task_id]['name']
            del self.running_tasks[task_id]
            
            # Clear active task if this was the active one
            if self.active_task_id == task_id:
                self.active_task_id = None
                self.set_status_message(f"Completed: {name}")
                
                # Find another running task to show, if any
                for t_id, task in self.running_tasks.items():
                    if task['status'] == 'running':
                        self.active_task_id = t_id
                        self.set_progress(task['progress'])
                        self.set_status_message(f"Running: {task['name']}...")
                        break
                else:
                    # No more running tasks
                    self.show_progress(False)
            
            # Update UI
            self.update_task_count()
    
    def _on_task_failed(self, data):
        """Handle task failed event."""
        if not data:
            return
            
        task_id = data.get('task_id')
        error = data.get('error', 'Unknown error')
        
        if task_id and task_id in self.running_tasks:
            # Get task info
            name = self.running_tasks[task_id]['name']
            
            # Remove from running tasks
            del self.running_tasks[task_id]
            
            # Clear active task if this was the active one
            if self.active_task_id == task_id:
                self.active_task_id = None
                self.set_status_message(f"Error in {name}: {error}")
                
                # Find another running task to show, if any
                for t_id, task in self.running_tasks.items():
                    if task['status'] == 'running':
                        self.active_task_id = t_id
                        self.set_progress(task['progress'])
                        self.set_status_message(f"Running: {task['name']}...")
                        break
                else:
                    # No more running tasks
                    self.show_progress(False)
            
            # Update UI
            self.update_task_count()
    
    def _on_task_cancelled(self, data):
        """Handle task cancelled event."""
        if not data:
            return
            
        task_id = data.get('task_id')
        
        if task_id and task_id in self.running_tasks:
            # Remove from running tasks
            del self.running_tasks[task_id]
            
            # Clear active task if this was the active one
            if self.active_task_id == task_id:
                self.active_task_id = None
                
                # Find another running task to show, if any
                for t_id, task in self.running_tasks.items():
                    if task['status'] == 'running':
                        self.active_task_id = t_id
                        self.set_progress(task['progress'])
                        self.set_status_message(f"Running: {task['name']}...")
                        break
                else:
                    # No more running tasks
                    self.show_progress(False)
            
            # Update UI
            self.update_task_count()
    
    def _on_task_progress(self, data):
        """Handle task progress event."""
        if not data:
            return
            
        task_id = data.get('task_id')
        progress = data.get('progress', 0)
        
        if task_id and task_id in self.running_tasks:
            # Update task progress
            self.running_tasks[task_id]['progress'] = progress
            
            # Update UI if this is the active task
            if self.active_task_id == task_id:
                self.set_progress(progress)
    
    def _on_tasks_cleared(self, data):
        """Handle tasks cleared event."""
        # Reset task tracking
        self.running_tasks = {}
        self.active_task_id = None
        
        # Update UI
        self.show_progress(False)
        self.update_task_count()
        self.set_status_message("Ready")