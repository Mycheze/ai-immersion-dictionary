"""
Language Filter View

This module provides the language filter view component, which allows users
to filter the dictionary by target and definition languages.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, List, Callable, Set

from .base_view import BaseView

class LanguageFilterView(BaseView):
    """
    Language filter view component.
    
    This class represents the language filter panel of the application, providing
    UI elements for selecting target and definition languages.
    
    Attributes:
        parent: The parent widget or window
        event_bus: Event system for view-related notifications
        target_language_var: Variable holding the selected target language
        definition_language_var: Variable holding the selected definition language
    """
    
    def __init__(
        self,
        parent,
        event_bus=None,
        **kwargs
    ):
        """
        Initialize the language filter view.
        
        Args:
            parent: The parent widget or window
            event_bus: Optional event bus for notifications
            **kwargs: Additional keyword arguments
        """
        super().__init__(parent, event_bus, **kwargs)
        
        # Filter variables
        self.target_language_var = tk.StringVar()
        self.definition_language_var = tk.StringVar()
        self.search_filter_var = tk.StringVar()
        
        # Available languages
        self.available_languages = {
            'target_languages': [],
            'definition_languages': []
        }
        
        # Create UI components
        self._create_language_selectors()
        self._create_filter_area()
        
        # Configure grid layout
        self.frame.grid_rowconfigure(2, weight=1)  # Filter takes remaining space
        self.frame.grid_columnconfigure(0, weight=1)
    
    def _create_language_selectors(self):
        """Create the language selector dropdown menus."""
        # Target language
        target_frame = ttk.LabelFrame(self.frame, text="Target Language")
        target_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.target_language_combobox = ttk.Combobox(
            target_frame,
            textvariable=self.target_language_var,
            state="readonly"
        )
        self.target_language_combobox.pack(fill=tk.X, padx=5, pady=5)
        
        # Bind selection event
        self.target_language_combobox.bind("<<ComboboxSelected>>", self._on_language_change)
        
        # Definition language
        definition_frame = ttk.LabelFrame(self.frame, text="Definition Language")
        definition_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        self.definition_language_combobox = ttk.Combobox(
            definition_frame,
            textvariable=self.definition_language_var,
            state="readonly"
        )
        self.definition_language_combobox.pack(fill=tk.X, padx=5, pady=5)
        
        # Bind selection event
        self.definition_language_combobox.bind("<<ComboboxSelected>>", self._on_language_change)
        
        # Store in widgets dict for later access
        self.widgets['target_language_combobox'] = self.target_language_combobox
        self.widgets['definition_language_combobox'] = self.definition_language_combobox
    
    def _create_filter_area(self):
        """Create the filter area for headword filtering."""
        filter_frame = ttk.LabelFrame(self.frame, text="Filter Entries")
        filter_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        
        # Filter entry
        filter_entry_frame = ttk.Frame(filter_frame)
        filter_entry_frame.pack(fill=tk.X, padx=5, pady=5)
        
        filter_label = ttk.Label(filter_entry_frame, text="Filter:")
        filter_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.filter_entry = ttk.Entry(
            filter_entry_frame,
            textvariable=self.search_filter_var
        )
        self.filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Bind key events for filtering
        self.filter_entry.bind("<KeyRelease>", self._on_filter_change)
        
        # Clear filter button
        self.clear_filter_button = ttk.Button(
            filter_entry_frame,
            text="✕",
            width=2,
            command=self._on_clear_filter
        )
        self.clear_filter_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Listbox for filtered headwords
        headword_frame = ttk.Frame(filter_frame)
        headword_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.headword_listbox = tk.Listbox(
            headword_frame,
            selectmode=tk.SINGLE,
            activestyle=tk.DOTBOX
        )
        self.headword_scrollbar = ttk.Scrollbar(
            headword_frame,
            orient=tk.VERTICAL,
            command=self.headword_listbox.yview
        )
        self.headword_listbox.configure(yscrollcommand=self.headword_scrollbar.set)
        
        self.headword_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.headword_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.headword_listbox.bind("<Double-1>", self._on_headword_selected)
        self.headword_listbox.bind("<Return>", self._on_headword_selected)
        
        # Store in widgets dict for later access
        self.widgets['filter_entry'] = self.filter_entry
        self.widgets['clear_filter_button'] = self.clear_filter_button
        self.widgets['headword_listbox'] = self.headword_listbox
    
    def set_available_languages(self, languages: Dict[str, List[str]]):
        """
        Set the available languages for the filter dropdowns.
        
        Args:
            languages: Dictionary with target_languages and definition_languages lists
        """
        # Store available languages
        self.available_languages = languages
        
        # Update target language combobox
        target_languages = ["All"] + languages.get('target_languages', [])
        self.target_language_combobox['values'] = target_languages
        
        # Update definition language combobox
        definition_languages = ["All"] + languages.get('definition_languages', [])
        self.definition_language_combobox['values'] = definition_languages
        
        # Set default selections if not already set
        if not self.target_language_var.get() and target_languages:
            self.target_language_var.set(target_languages[0])
            
        if not self.definition_language_var.get() and definition_languages:
            self.definition_language_var.set(definition_languages[0])
    
    def get_language_filters(self) -> Dict[str, str]:
        """
        Get the current language filter settings.
        
        Returns:
            Dictionary with target_language and definition_language values
        """
        target_lang = self.target_language_var.get()
        target_lang = None if target_lang == "All" else target_lang
        
        definition_lang = self.definition_language_var.get()
        definition_lang = None if definition_lang == "All" else definition_lang
        
        return {
            'target_language': target_lang,
            'definition_language': definition_lang
        }
    
    def get_search_filter(self) -> str:
        """
        Get the current search filter text.
        
        Returns:
            Current search filter text
        """
        return self.search_filter_var.get()
    
    def set_language_filters(self, target_lang: Optional[str] = None, definition_lang: Optional[str] = None):
        """
        Set the language filter values.
        
        Args:
            target_lang: Target language to select
            definition_lang: Definition language to select
        """
        # Set target language if provided and valid
        if target_lang:
            # Ensure "All" is included in the check
            valid_values = list(self.target_language_combobox['values'])
            if target_lang in valid_values:
                self.target_language_var.set(target_lang)
            elif "All" in valid_values:
                self.target_language_var.set("All")
        
        # Set definition language if provided and valid
        if definition_lang:
            # Ensure "All" is included in the check
            valid_values = list(self.definition_language_combobox['values'])
            if definition_lang in valid_values:
                self.definition_language_var.set(definition_lang)
            elif "All" in valid_values:
                self.definition_language_var.set("All")
                
        # Trigger language change event
        self._on_language_change()
    
    def update_headword_list(self, headwords: List[Dict[str, Any]]):
        """
        Update the headword listbox with filtered entries.
        
        Args:
            headwords: List of entry dictionaries with headword and metadata
        """
        # Clear the listbox
        self.headword_listbox.delete(0, tk.END)
        
        # Add headwords to the listbox
        for entry in headwords:
            headword = entry.get('headword', '')
            self.headword_listbox.insert(tk.END, headword)
            
        # Update listbox appearance
        self._update_listbox_appearance()
    
    def get_selected_headword(self) -> Optional[str]:
        """
        Get the currently selected headword from the listbox.
        
        Returns:
            Selected headword or None if nothing selected
        """
        selected = self.headword_listbox.curselection()
        if not selected:
            return None
            
        index = int(selected[0])
        return self.headword_listbox.get(index)
    
    def set_loading_state(self, is_loading: bool):
        """
        Set the loading state of the language filter.
        
        Args:
            is_loading: Whether the filter is in a loading state
        """
        state = tk.DISABLED if is_loading else tk.NORMAL
        self.target_language_combobox.configure(state="disabled" if is_loading else "readonly")
        self.definition_language_combobox.configure(state="disabled" if is_loading else "readonly")
        self.filter_entry.configure(state=state)
        self.clear_filter_button.configure(state=state)
        self.headword_listbox.configure(state=state)
    
    def update_scale(self):
        """Update UI elements based on the current scale factor."""
        # Update base view scaling
        super().update_scale()
        
        # Calculate font size
        base_font_size = 10
        scaled_font_size = int(base_font_size * self.scale_factor)
        
        # Update font for headword listbox
        self.headword_listbox.configure(font=('TkDefaultFont', scaled_font_size))
        
        # Update combobox fonts
        self.target_language_combobox.configure(font=('TkDefaultFont', scaled_font_size))
        self.definition_language_combobox.configure(font=('TkDefaultFont', scaled_font_size))
        
        # Update filter entry font
        self.filter_entry.configure(font=('TkDefaultFont', scaled_font_size))
        
        # Update listbox row height
        self._update_listbox_appearance()
    
    def _update_listbox_appearance(self):
        """Update the appearance of the headword listbox based on scale factor."""
        # Calculate row height based on font size
        base_font_size = 10
        scaled_font_size = int(base_font_size * self.scale_factor)
        row_height = scaled_font_size + 6  # Add padding
        
        # Set list height based on available items
        self.headword_listbox.configure(height=min(15, self.headword_listbox.size() or 15))
    
    # Event handlers
    
    def _on_language_change(self, event=None):
        """Handle language selection change."""
        # Get current filter values
        filters = self.get_language_filters()
        
        # Notify of language filter change
        if self.event_bus:
            self.event_bus.publish('language_filter:changed', filters)
    
    def _on_filter_change(self, event=None):
        """Handle search filter text change."""
        # Get current filter text
        filter_text = self.get_search_filter()
        
        # Notify of filter change
        if self.event_bus:
            self.event_bus.publish('search_filter:changed', {
                'filter_text': filter_text
            })
    
    def _on_clear_filter(self):
        """Handle clear filter button click."""
        self.search_filter_var.set("")
        self.filter_entry.focus_set()
        
        # Notify of filter change
        if self.event_bus:
            self.event_bus.publish('search_filter:changed', {
                'filter_text': ""
            })
    
    def _on_headword_selected(self, event=None):
        """Handle headword selection in the listbox."""
        selected_headword = self.get_selected_headword()
        if not selected_headword:
            return
            
        # Notify of headword selection
        if self.event_bus:
            self.event_bus.publish('headword:selected', {
                'headword': selected_headword
            })