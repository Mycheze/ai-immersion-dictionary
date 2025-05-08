"""
Async Service

This module provides a service for executing tasks asynchronously, with
proper progress reporting and UI feedback.
"""

import time
import uuid
import queue
import threading
from typing import Dict, List, Any, Optional, Callable, Union, Tuple

from .base_service import BaseService

class Task:
    """
    Represents an asynchronous task.
    
    Attributes:
        id: Unique identifier for the task
        name: Human-readable name of the task
        description: Detailed description of the task
        status: Current status of the task (pending, running, completed, cancelled, failed)
        progress: Progress value (0-100)
        result: Result of the task (if completed)
        error: Error message (if failed)
        callback: Function to call when task completes
        error_callback: Function to call when task fails
        created_at: Timestamp when task was created
        started_at: Timestamp when task started running
        completed_at: Timestamp when task completed or failed
    """
    
    def __init__(
        self, 
        func: Callable,
        args: Tuple = (), 
        kwargs: Dict[str, Any] = None,
        name: str = None,
        description: str = None,
        callback: Callable = None,
        error_callback: Callable = None,
        task_id: str = None
    ):
        """
        Initialize a task.
        
        Args:
            func: The function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            name: Name of the task
            description: Description of the task
            callback: Function to call when task completes
            error_callback: Function to call when task fails
            task_id: Unique ID for the task (one will be generated if not provided)
        """
        self.id = task_id or str(uuid.uuid4())
        self.name = name or func.__name__
        self.description = description or f"Task {self.name}"
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.status = "pending"
        self.progress = 0
        self.result = None
        self.error = None
        self.callback = callback
        self.error_callback = error_callback
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
    
    def __str__(self):
        return f"Task {self.name} ({self.id}) - {self.status}"


class TaskPriority:
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class AsyncService(BaseService):
    """
    Service for managing asynchronous tasks.
    
    This service provides a clean interface for executing tasks asynchronously,
    with proper progress reporting and UI feedback.
    
    Attributes:
        tasks: Dictionary of tasks by ID
        task_queue: Queue of pending tasks
        workers: List of worker threads
        max_workers: Maximum number of worker threads
        running: Flag indicating whether the service is running
        event_bus: Event system for service-related notifications
    """
    
    def __init__(self, max_workers: int = 4, event_bus=None):
        """
        Initialize the async service.
        
        Args:
            max_workers: Maximum number of worker threads
            event_bus: Optional event bus for notifications
        """
        self.max_workers = max_workers
        self.tasks = {}
        self.task_queue = queue.PriorityQueue()
        self.workers = []
        self.running = False
        self.lock = threading.Lock()
        
        # Call parent initializer
        super().__init__(event_bus)
    
    def _initialize(self):
        """Initialize the async service."""
        # Start worker threads
        self._start_workers()
        
        # Start task cleanup timer
        self._start_cleanup_timer()
    
    def _start_workers(self):
        """Start worker threads."""
        self.running = True
        
        # Create and start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_thread,
                name=f"AsyncWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
            
        self.publish_event('async:workers_started', {
            'worker_count': len(self.workers)
        })
    
    def _worker_thread(self):
        """Worker thread function."""
        while self.running:
            try:
                # Get a task from the queue with a timeout of 0.1 seconds
                priority, task_id = self.task_queue.get(timeout=0.1)
                
                # Get the task from the tasks dict
                with self.lock:
                    if task_id not in self.tasks:
                        # Task was cancelled
                        self.task_queue.task_done()
                        continue
                        
                    task = self.tasks[task_id]
                
                # Execute the task
                self._execute_task(task)
                
                # Mark the task as done in the queue
                self.task_queue.task_done()
                
            except queue.Empty:
                # Queue is empty, continue to next iteration
                continue
            except Exception as e:
                # Log the error
                self.publish_event('async:worker_error', {
                    'error': str(e),
                    'thread': threading.current_thread().name
                })
    
    def _execute_task(self, task: Task):
        """
        Execute a task.
        
        Args:
            task: The task to execute
        """
        # Update task status and start time
        task.status = "running"
        task.started_at = time.time()
        
        # Notify of task start
        self.publish_event('task:started', {
            'task_id': task.id,
            'name': task.name,
            'description': task.description
        })
        
        try:
            # Execute the task function
            # Add progress_callback to kwargs
            task.kwargs['progress_callback'] = lambda progress: self.update_task_progress(task.id, progress)
            
            # Execute the function
            result = task.func(*task.args, **task.kwargs)
            
            # Update task status and result
            task.status = "completed"
            task.result = result
            task.completed_at = time.time()
            
            # Notify of task completion
            self.publish_event('task:completed', {
                'task_id': task.id,
                'name': task.name,
                'result': result
            })
            
            # Call completion callback if provided
            if task.callback:
                try:
                    task.callback(result)
                except Exception as e:
                    self.publish_event('task:callback_error', {
                        'task_id': task.id,
                        'error': str(e)
                    })
            
        except Exception as e:
            # Update task status and error
            task.status = "failed"
            task.error = str(e)
            task.completed_at = time.time()
            
            # Notify of task failure
            self.publish_event('task:failed', {
                'task_id': task.id,
                'name': task.name,
                'error': str(e)
            })
            
            # Call error callback if provided
            if task.error_callback:
                try:
                    task.error_callback(str(e))
                except Exception as e:
                    self.publish_event('task:error_callback_error', {
                        'task_id': task.id,
                        'error': str(e)
                    })
    
    def submit_task(
        self, 
        func: Callable, 
        *args, 
        name: str = None,
        description: str = None,
        callback: Callable = None,
        error_callback: Callable = None,
        priority: int = TaskPriority.NORMAL,
        **kwargs
    ) -> str:
        """
        Submit a task for execution.
        
        Args:
            func: The function to execute
            *args: Positional arguments for the function
            name: Name of the task
            description: Description of the task
            callback: Function to call when task completes
            error_callback: Function to call when task fails
            priority: Priority of the task (higher priority tasks are executed first)
            **kwargs: Keyword arguments for the function
            
        Returns:
            ID of the submitted task
        """
        # Create the task
        task = Task(
            func=func,
            args=args,
            kwargs=kwargs,
            name=name,
            description=description,
            callback=callback,
            error_callback=error_callback
        )
        
        # Add the task to the tasks dictionary
        with self.lock:
            self.tasks[task.id] = task
        
        # Add the task to the queue
        self.task_queue.put((-priority, task.id))  # Negate priority for priority queue (higher values have higher priority)
        
        # Notify of task submission
        self.publish_event('task:submitted', {
            'task_id': task.id,
            'name': task.name,
            'description': task.description,
            'priority': priority
        })
        
        return task.id
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task if it's still pending.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                
                # Only cancel if the task is still pending
                if task.status == "pending":
                    task.status = "cancelled"
                    
                    # Notify of task cancellation
                    self.publish_event('task:cancelled', {
                        'task_id': task.id,
                        'name': task.name
                    })
                    
                    # Remove from tasks dict
                    del self.tasks[task_id]
                    
                    return True
                    
        return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary with task status information, or None if task not found
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                return {
                    'id': task.id,
                    'name': task.name,
                    'description': task.description,
                    'status': task.status,
                    'progress': task.progress,
                    'result': task.result,
                    'error': task.error,
                    'created_at': task.created_at,
                    'started_at': task.started_at,
                    'completed_at': task.completed_at
                }
                
        return None
    
    def update_task_progress(self, task_id: str, progress: float) -> bool:
        """
        Update the progress of a task.
        
        Args:
            task_id: ID of the task
            progress: Progress value (0-100)
            
        Returns:
            True if the progress was updated, False otherwise
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                
                # Only update if the task is running
                if task.status == "running":
                    # Clamp progress value
                    progress = max(0, min(100, progress))
                    
                    # Only update if progress has changed by at least 1%
                    if abs(task.progress - progress) >= 1:
                        task.progress = progress
                        
                        # Notify of progress update
                        self.publish_event('task:progress', {
                            'task_id': task.id,
                            'name': task.name,
                            'progress': progress
                        })
                        
                    return True
                    
        return False
    
    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get statistics about the task queue.
        
        Returns:
            Dictionary with queue statistics
        """
        pending_count = 0
        running_count = 0
        completed_count = 0
        failed_count = 0
        cancelled_count = 0
        
        with self.lock:
            for task in self.tasks.values():
                if task.status == "pending":
                    pending_count += 1
                elif task.status == "running":
                    running_count += 1
                elif task.status == "completed":
                    completed_count += 1
                elif task.status == "failed":
                    failed_count += 1
                elif task.status == "cancelled":
                    cancelled_count += 1
        
        return {
            'pending': pending_count,
            'running': running_count,
            'completed': completed_count,
            'failed': failed_count,
            'cancelled': cancelled_count,
            'total': pending_count + running_count + completed_count + failed_count + cancelled_count,
            'queue_size': self.task_queue.qsize()
        }
    
    def clear_completed_tasks(self, age_seconds: float = 60.0) -> int:
        """
        Clear completed, failed, and cancelled tasks from the tasks dictionary.
        
        Args:
            age_seconds: Minimum age in seconds for tasks to be cleared
            
        Returns:
            Number of tasks cleared
        """
        now = time.time()
        count = 0
        
        with self.lock:
            # Collect task IDs to remove
            to_remove = []
            
            for task_id, task in self.tasks.items():
                if task.status in ("completed", "failed", "cancelled"):
                    if task.completed_at and (now - task.completed_at) >= age_seconds:
                        to_remove.append(task_id)
            
            # Remove collected tasks
            for task_id in to_remove:
                del self.tasks[task_id]
                count += 1
        
        # Notify of tasks cleared
        if count > 0:
            self.publish_event('tasks:cleared', {
                'count': count
            })
            
        return count
    
    def _start_cleanup_timer(self):
        """Start a timer to periodically clean up completed tasks."""
        if not hasattr(self, 'root'):
            # Create a dummy Tk widget for timer
            import tkinter as tk
            self.root = tk.Tk()
            self.root.withdraw()  # Hide the window
            
        # Schedule first cleanup after 60 seconds
        self.root.after(60000, self._cleanup_completed_tasks)
        
    def _cleanup_completed_tasks(self):
        """Periodically clean up completed, failed, and cancelled tasks."""
        if self.running:
            # Clear completed tasks older than 60 seconds
            count = self.clear_completed_tasks(60.0)
            
            if count > 0:
                self.publish_event('tasks:auto_cleared', {
                    'count': count
                })
            
            # Schedule next cleanup after 60 seconds
            self.root.after(60000, self._cleanup_completed_tasks)
            
    def shutdown(self):
        """Clean up resources and shut down the service."""
        # Stop the workers
        self.running = False
        
        # Wait for all workers to exit
        for worker in self.workers:
            worker.join(timeout=0.5)  # Wait with timeout
        
        # Clear all tasks
        with self.lock:
            self.tasks.clear()
        
        # Destroy Tk root if it exists
        if hasattr(self, 'root') and self.root:
            self.root.after_cancel(self._cleanup_completed_tasks)
            self.root.destroy()
            self.root = None
        
        # Publish shutdown event
        self.publish_event('async:shutdown', {})