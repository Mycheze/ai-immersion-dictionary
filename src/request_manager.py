import threading
import queue
import time
import uuid
from typing import Dict, List, Any, Callable, Optional, Tuple

class APIRequest:
    """
    Represents an API request with a unique ID, parameters, and callback functions
    """
    def __init__(self, 
                 request_type: str, 
                 params: Dict[str, Any], 
                 success_callback: Callable,
                 error_callback: Callable = None,
                 request_id: str = None):
        """Initialize an API request"""
        self.request_id = request_id if request_id else str(uuid.uuid4())
        self.request_type = request_type  # 'lemma', 'entry', etc.
        self.params = params
        self.success_callback = success_callback
        self.error_callback = error_callback
        self.status = 'pending'  # pending, processing, completed, failed, cancelled
        self.result = None
        self.error = None
        self.timestamp = time.time()
        self.completion_time = None
    
    def complete(self, result):
        """Mark the request as completed with a result"""
        self.status = 'completed'
        self.result = result
        self.completion_time = time.time()
    
    def fail(self, error):
        """Mark the request as failed with an error"""
        self.status = 'failed'
        self.error = error
        self.completion_time = time.time()
    
    def cancel(self):
        """Mark the request as cancelled"""
        self.status = 'cancelled'
        self.completion_time = time.time()
    
    def __str__(self):
        return f"Request[{self.request_id[:8]}] ({self.request_type}) - {self.status}"


class RequestManager:
    """
    Manages a queue of API requests, processing them asynchronously
    """
    def __init__(self, dictionary_engine, max_concurrent_requests=3):
        """Initialize the request manager"""
        self.dictionary_engine = dictionary_engine
        self.request_queue = queue.Queue()
        self.active_requests: Dict[str, APIRequest] = {}
        self.completed_requests: Dict[str, APIRequest] = {}
        self.max_concurrent_requests = max_concurrent_requests
        self.worker_thread = None
        self.shutdown_flag = threading.Event()
        self.ui_callback = None  # Callback to update UI with queue status
        
        # Start the worker thread
        self.start_worker()
    
    def start_worker(self):
        """Start the worker thread to process requests"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.shutdown_flag.clear()
            self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()
    
    def shutdown(self):
        """Shut down the worker thread"""
        self.shutdown_flag.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
    
    def _process_queue(self):
        """Process requests from the queue"""
        while not self.shutdown_flag.is_set():
            # Check if we can process more requests
            if len(self.active_requests) < self.max_concurrent_requests:
                try:
                    # Get a request from the queue (non-blocking)
                    request = self.request_queue.get(block=False)
                    self._process_request(request)
                except queue.Empty:
                    # No requests in queue, sleep briefly
                    time.sleep(0.1)
            else:
                # Max concurrent requests reached, wait
                time.sleep(0.1)
            
            # Update UI if callback is set
            if self.ui_callback:
                self.ui_callback()
    
    def _process_request(self, request: APIRequest):
        """Process a single request in a separate thread"""
        # Mark as processing and add to active requests
        request.status = 'processing'
        self.active_requests[request.request_id] = request
        
        # Update UI if callback is set
        if self.ui_callback:
            self.ui_callback()
        
        # Process the request in a separate thread
        thread = threading.Thread(
            target=self._execute_request,
            args=(request,),
            daemon=True
        )
        thread.start()
    
    def _execute_request(self, request: APIRequest):
        """Execute a request and handle the result"""
        try:
            if request.status == 'cancelled':
                return
            
            # Call the appropriate dictionary engine method based on request type
            if request.request_type == 'lemma':
                word = request.params.get('word', '')
                sentence_context = request.params.get('sentence_context')
                result = self.dictionary_engine.get_lemma(word, sentence_context)
                request.complete(result)
                
            elif request.request_type == 'entry':
                word = request.params.get('word', '')
                target_lang = request.params.get('target_lang')
                source_lang = request.params.get('source_lang')
                sentence_context = request.params.get('sentence_context')
                variation_prompt = request.params.get('variation_prompt')
                result = self.dictionary_engine.create_new_entry(
                    word, target_lang, source_lang, sentence_context, variation_prompt
                )
                request.complete(result)
                
            elif request.request_type == 'regenerate':
                headword = request.params.get('headword', '')
                target_lang = request.params.get('target_lang')
                source_lang = request.params.get('source_lang')
                definition_lang = request.params.get('definition_lang')
                variation_seed = request.params.get('variation_seed')
                result = self.dictionary_engine.regenerate_entry(
                    headword, target_lang, source_lang, definition_lang, variation_seed
                )
                request.complete(result)
                
            elif request.request_type == 'validate_language':
                language_name = request.params.get('language_name', '')
                result = self.dictionary_engine.validate_language(language_name)
                request.complete(result)
            
            else:
                request.fail(f"Unknown request type: {request.request_type}")
        
        except Exception as e:
            # Mark request as failed
            request.fail(str(e))
        
        finally:
            # Move from active to completed
            if request.request_id in self.active_requests:
                del self.active_requests[request.request_id]
            
            # Store in completed requests (limited history)
            self.completed_requests[request.request_id] = request
            
            # Trim completed requests if needed
            if len(self.completed_requests) > 100:  # Keep last 100 requests
                oldest = sorted(self.completed_requests.items(), key=lambda x: x[1].timestamp)
                for req_id, _ in oldest[:len(self.completed_requests) - 100]:
                    del self.completed_requests[req_id]
            
            # Mark task as done in the queue
            self.request_queue.task_done()
            
            # Call appropriate callback
            if request.status == 'completed' and request.success_callback:
                request.success_callback(request.result)
            elif request.status == 'failed' and request.error_callback:
                request.error_callback(request.error)
            
            # Update UI if callback is set
            if self.ui_callback:
                self.ui_callback()
    
    def add_request(self, request_type: str, params: Dict[str, Any], 
                   success_callback: Callable, error_callback: Callable = None) -> str:
        """Add a request to the queue and return its ID"""
        request = APIRequest(request_type, params, success_callback, error_callback)
        self.request_queue.put(request)
        return request.request_id
    
    def cancel_request(self, request_id: str) -> bool:
        """Cancel a request by ID"""
        # Check active requests
        if request_id in self.active_requests:
            self.active_requests[request_id].cancel()
            return True
        
        # Check for request in queue
        new_queue = queue.Queue()
        cancelled = False
        
        # Go through the queue
        try:
            while True:
                request = self.request_queue.get(block=False)
                if request.request_id == request_id:
                    request.cancel()
                    self.completed_requests[request_id] = request
                    cancelled = True
                    self.request_queue.task_done()
                else:
                    new_queue.put(request)
        except queue.Empty:
            pass
        
        # Restore remaining requests
        try:
            while True:
                request = new_queue.get(block=False)
                self.request_queue.put(request)
                new_queue.task_done()
        except queue.Empty:
            pass
        
        # Update UI if callback is set
        if self.ui_callback and cancelled:
            self.ui_callback()
            
        return cancelled
    
    def cancel_all_requests(self) -> int:
        """Cancel all pending and active requests"""
        # Cancel requests in queue
        cancelled_count = 0
        new_queue = queue.Queue()
        
        try:
            while True:
                request = self.request_queue.get(block=False)
                request.cancel()
                self.completed_requests[request.request_id] = request
                cancelled_count += 1
                self.request_queue.task_done()
        except queue.Empty:
            pass
        
        # Cancel active requests
        for request_id, request in list(self.active_requests.items()):
            request.cancel()
            cancelled_count += 1
        
        # Update UI if callback is set
        if self.ui_callback and cancelled_count > 0:
            self.ui_callback()
            
        return cancelled_count
    
    def get_request_status(self, request_id: str) -> Optional[str]:
        """Get the status of a request by ID"""
        if request_id in self.active_requests:
            return self.active_requests[request_id].status
        if request_id in self.completed_requests:
            return self.completed_requests[request_id].status
        return None
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get statistics about the queue"""
        stats = {
            'pending': self.request_queue.qsize(),
            'active': len(self.active_requests),
            'completed': len([r for r in self.completed_requests.values() if r.status == 'completed']),
            'failed': len([r for r in self.completed_requests.values() if r.status == 'failed']),
            'cancelled': len([r for r in self.completed_requests.values() if r.status == 'cancelled']),
        }
        return stats
    
    def get_active_requests(self) -> List[APIRequest]:
        """Get a list of active requests"""
        return list(self.active_requests.values())
    
    def get_pending_count(self) -> int:
        """Get the number of pending requests"""
        return self.request_queue.qsize()
    
    def get_active_count(self) -> int:
        """Get the number of active requests"""
        return len(self.active_requests)
    
    def set_ui_callback(self, callback: Callable):
        """Set a callback function for UI updates"""
        self.ui_callback = callback