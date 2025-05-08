"""
Search Panel View

This module provides the search panel view component, which handles user input
for dictionary searches and displays the search history.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Dict, Any, Optional, List, Callable, Tuple

from .base_view import BaseView

class SearchPanelView(BaseView):
    """
    Search panel view component.
    
    This class represents the search panel of the application, providing UI
    elements for entering search terms, context sentences, and viewing
    search history.
    
    Attributes:
        parent: The parent widget or window
        event_bus: Event system for view-related notifications
        search_var: Variable holding the current search term
        context_text: Text widget for entering context sentences
        history_listbox: Listbox for displaying search history
    """
    
    def __init__(
        self,
        parent,
        event_bus=None,
        **kwargs
    ):
        """
        Initialize the search panel view.
        
        Args:
            parent: The parent widget or window
            event_bus: Optional event bus for notifications
            **kwargs: Additional keyword arguments
        """
        super().__init__(parent, event_bus, **kwargs)
        
        # Search variables
        self.search_var = tk.StringVar()
        self.monitor_clipboard_var = tk.BooleanVar(value=False)
        self.last_clipboard_content = ""
        
        # Create UI components
        self._create_search_bar()
        self._create_context_area()
        self._create_history_area()
        
        # Set up clipboard monitoring
        self._setup_clipboard_monitoring()
        
        # Configure grid layout
        self.frame.grid_rowconfigure(2, weight=1)  # History area takes remaining space
        self.frame.grid_columnconfigure(0, weight=1)
    
    def _create_search_bar(self):
        """Create the search bar area."""
        search_frame = ttk.Frame(self.frame)
        search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Search entry
        search_label = ttk.Label(search_frame, text="Search:")
        search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=30
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Bind Enter key to search
        self.search_entry.bind("<Return>", self._on_search)
        
        # Search button
        self.search_button = ttk.Button(
            search_frame,
            text="Search",
            command=self._on_search
        )
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        # Clear button
        self.clear_button = ttk.Button(
            search_frame,
            text="✕",
            width=2,
            command=self._on_clear_search
        )
        self.clear_button.pack(side=tk.LEFT)
        
        # Store in widgets dict for later access
        self.widgets['search_entry'] = self.search_entry
        self.widgets['search_button'] = self.search_button
        self.widgets['clear_button'] = self.clear_button
    
    def _create_context_area(self):
        """Create the context input area."""
        context_frame = ttk.LabelFrame(self.frame, text="Context (Optional)")
        context_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        # Context text area
        self.context_text = scrolledtext.ScrolledText(
            context_frame,
            height=4,
            wrap=tk.WORD
        )
        self.context_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add text selection handling
        self.context_text.bind("<ButtonRelease-1>", self._on_context_selection)
        
        # Bottom controls
        controls_frame = ttk.Frame(context_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Monitor clipboard option
        self.clipboard_check = ttk.Checkbutton(
            controls_frame,
            text="Monitor clipboard",
            variable=self.monitor_clipboard_var,
            command=self._on_toggle_clipboard_monitoring
        )
        self.clipboard_check.pack(side=tk.LEFT)
        
        # Clear context button
        self.clear_context_button = ttk.Button(
            controls_frame,
            text="Clear Context",
            command=self._on_clear_context
        )
        self.clear_context_button.pack(side=tk.RIGHT)
        
        # Store in widgets dict for later access
        self.widgets['context_text'] = self.context_text
        self.widgets['clipboard_check'] = self.clipboard_check
        self.widgets['clear_context_button'] = self.clear_context_button
    
    def _create_history_area(self):
        """Create the search history area."""
        history_frame = ttk.LabelFrame(self.frame, text="Recent Lookups")
        history_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure grid layout
        history_frame.grid_rowconfigure(0, weight=1)
        history_frame.grid_columnconfigure(0, weight=1)
        
        # Create history listbox with scrollbar
        self.history_listbox = tk.Listbox(
            history_frame,
            selectmode=tk.SINGLE,
            activestyle=tk.DOTBOX
        )
        self.history_scrollbar = ttk.Scrollbar(
            history_frame,
            orient=tk.VERTICAL,
            command=self.history_listbox.yview
        )
        self.history_listbox.configure(yscrollcommand=self.history_scrollbar.set)
        
        # Pack into frame
        self.history_listbox.grid(row=0, column=0, sticky="nsew")
        self.history_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bind events
        self.history_listbox.bind("<Double-1>", self._on_history_item_selected)
        self.history_listbox.bind("<Return>", self._on_history_item_selected)
        
        # Button frame for history actions
        button_frame = ttk.Frame(history_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Clear history button
        self.clear_history_button = ttk.Button(
            button_frame,
            text="Clear History",
            command=self._on_clear_history
        )
        self.clear_history_button.pack(side=tk.RIGHT)
        
        # Store in widgets dict for later access
        self.widgets['history_listbox'] = self.history_listbox
        self.widgets['clear_history_button'] = self.clear_history_button
    
    def _setup_clipboard_monitoring(self):
        """Set up clipboard monitoring functionality."""
        self.clipboard_monitoring_active = False
        self.clipboard_after_id = None
    
    def start_clipboard_monitoring(self):
        """Start monitoring the clipboard for changes."""
        if not self.clipboard_monitoring_active:
            self.clipboard_monitoring_active = True
            self._check_clipboard()
    
    def stop_clipboard_monitoring(self):
        """Stop monitoring the clipboard."""
        self.clipboard_monitoring_active = False
        if self.clipboard_after_id:
            self.frame.after_cancel(self.clipboard_after_id)
            self.clipboard_after_id = None
    
    def _check_clipboard(self):
        """Check for changes in the clipboard content."""
        if not self.clipboard_monitoring_active:
            return
            
        try:
            # This requires the 'tk' module and not ttk
            clipboard_content = self.frame.clipboard_get()
            
            # Check if clipboard content has changed and is not empty
            if (clipboard_content != self.last_clipboard_content and 
                clipboard_content.strip() and 
                len(clipboard_content) < 100):  # Limit to reasonable length
                
                self.search_var.set(clipboard_content.strip())
                self.last_clipboard_content = clipboard_content
                
                # Optionally auto-trigger search
                # self._on_search()
        except Exception:
            # Clipboard might be empty or contain non-text content
            pass
            
        # Schedule next check
        self.clipboard_after_id = self.frame.after(500, self._check_clipboard)
    
    def set_search_term(self, term: str):
        """
        Set the search term in the search bar.
        
        Args:
            term: The search term to set
        """
        self.search_var.set(term)
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)
    
    def set_context_text(self, context: str):
        """
        Set the text in the context area.
        
        Args:
            context: The context text to set
        """
        self.context_text.delete(1.0, tk.END)
        self.context_text.insert(tk.END, context)
    
    def get_search_term(self) -> str:
        """
        Get the current search term.
        
        Returns:
            The current search term
        """
        return self.search_var.get().strip()
    
    def get_context_text(self) -> str:
        """
        Get the current context text.
        
        Returns:
            The current context text
        """
        return self.context_text.get(1.0, tk.END).strip()
    
    def get_selected_context_text(self) -> Tuple[str, str]:
        """
        Get the selected text in the context area and its surrounding context.
        
        Returns:
            Tuple of (selected_text, full_context)
        """
        try:
            # Get selection if any
            selected_text = self.context_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            full_context = self.get_context_text()
            return selected_text.strip(), full_context
        except tk.TclError:
            # No selection
            return "", self.get_context_text()
    
    def update_history_list(self, history_items: List[Dict[str, str]]):
        """
        Update the history listbox with new items.
        
        Args:
            history_items: List of history items to display
        """
        # Clear the listbox
        self.history_listbox.delete(0, tk.END)
        
        # Add items to the listbox
        for item in history_items:
            headword = item.get('headword', '')
            target_language = item.get('target_language', '')
            definition_language = item.get('definition_language', '')
            
            # Format as "headword (target_lang → definition_lang)"
            display_text = f"{headword} ({target_language} → {definition_language})"
            
            # Add to listbox
            self.history_listbox.insert(tk.END, display_text)
            
        # Update listbox appearance
        self._update_listbox_appearance()
    
    def _update_listbox_appearance(self):
        """Update the appearance of the history listbox based on scale factor."""
        # Calculate font size based on scale factor
        base_font_size = 10
        scaled_font_size = int(base_font_size * self.scale_factor)
        
        # Apply font to listbox
        font = ('TkDefaultFont', scaled_font_size)
        self.history_listbox.configure(font=font)
        
        # Update row height based on font size
        row_height = scaled_font_size + 6  # Add padding
        self.history_listbox.configure(height=min(10, self.history_listbox.size()))
        
        # Set item height using a dummy item if needed
        if self.history_listbox.size() == 0:
            self.history_listbox.insert(tk.END, "")
            self.history_listbox.configure(height=1)
    
    def update_scale(self):
        """Update UI elements based on the current scale factor."""
        # Update base view scaling
        super().update_scale()
        
        # Calculate font sizes
        base_font_size = 10
        scaled_font_size = int(base_font_size * self.scale_factor)
        
        # Update search entry
        self.search_entry.configure(font=('TkDefaultFont', scaled_font_size))
        
        # Update context text area
        self.context_text.configure(font=('TkDefaultFont', scaled_font_size))
        
        # Update history listbox
        self._update_listbox_appearance()
    
    def set_loading_state(self, is_loading: bool):
        """
        Set the loading state of the search panel.
        
        Args:
            is_loading: Whether the panel is in a loading state
        """
        if is_loading:
            # Disable controls during loading
            self.search_button.configure(state=tk.DISABLED)
            self.search_entry.configure(state=tk.DISABLED)
            self.history_listbox.configure(state=tk.DISABLED)
        else:
            # Re-enable controls
            self.search_button.configure(state=tk.NORMAL)
            self.search_entry.configure(state=tk.NORMAL)
            self.history_listbox.configure(state=tk.NORMAL)
    
    # Event handlers
    
    def _on_search(self, event=None):
        """Handle search button click or Enter key in search entry."""
        search_term = self.get_search_term()
        if not search_term:
            return
            
        # Get context if any
        selected_text, full_context = self.get_selected_context_text()
        
        # If text is selected in the context area, use that as the search term
        if selected_text:
            search_term = selected_text
            self.set_search_term(search_term)
            
        # Prepare search data
        search_data = {
            'term': search_term,
            'context': full_context if full_context else None
        }
        
        # Notify of search request
        if self.event_bus:
            self.event_bus.publish('search:requested', search_data)
    
    def _on_clear_search(self):
        """Handle clear search button click."""
        self.search_var.set("")
        self.search_entry.focus_set()
    
    def _on_clear_context(self):
        """Handle clear context button click."""
        self.context_text.delete(1.0, tk.END)
        self.context_text.focus_set()
    
    def _on_context_selection(self, event=None):
        """Handle text selection in the context area."""
        try:
            # Get selected text
            selected_text = self.context_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            
            # If text is selected, update search entry
            if selected_text:
                self.search_var.set(selected_text)
                
                # Notify of selection
                if self.event_bus:
                    self.event_bus.publish('context:text_selected', {
                        'selected_text': selected_text,
                        'context': self.get_context_text()
                    })
        except tk.TclError:
            # No selection
            pass
    
    def _on_toggle_clipboard_monitoring(self):
        """Handle toggle of clipboard monitoring checkbox."""
        if self.monitor_clipboard_var.get():
            self.start_clipboard_monitoring()
        else:
            self.stop_clipboard_monitoring()
            
        # Notify of change
        if self.event_bus:
            self.event_bus.publish('clipboard:monitoring_changed', {
                'active': self.monitor_clipboard_var.get()
            })
    
    def _on_history_item_selected(self, event=None):
        """Handle selection of an item in the history listbox."""
        # Get selected index
        selected_index = self.history_listbox.curselection()
        if not selected_index:
            return
            
        # Get the index as an integer
        index = int(selected_index[0])
        
        # Notify of history item selection
        if self.event_bus:
            self.event_bus.publish('history:item_selected', {
                'index': index
            })
    
    def _on_clear_history(self):
        """Handle clear history button click."""
        # Notify of history clear request
        if self.event_bus:
            self.event_bus.publish('history:clear_requested', {})
    
    def destroy(self):
        """Clean up resources and destroy the view."""
        # Stop clipboard monitoring
        self.stop_clipboard_monitoring()
        
        # Call parent destroy
        super().destroy()