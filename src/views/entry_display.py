"""
Entry Display View

This module provides the entry display view component, which displays dictionary
entries with their meanings, examples, and grammar information.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Dict, Any, Optional, List, Callable, Tuple
import json

# Try to import our text patches for better wrapping
try:
    from ..utils.text_patches import enhance_text_widget
except ImportError:
    # Create a dummy function if the module isn't available
    def enhance_text_widget(widget):
        return widget

from .base_view import BaseView
from ..utils.type_definitions import DictionaryEntry

class EntryDisplayView(BaseView):
    """
    Dictionary entry display view component.
    
    This class represents the entry display area of the application, providing
    a rich display of dictionary entries with meanings, examples, and grammar
    information.
    
    Attributes:
        parent: The parent widget or window
        event_bus: Event system for view-related notifications
        content_text: Text widget for displaying entry content
        current_entry: Currently displayed dictionary entry
    """
    
    def __init__(
        self,
        parent,
        event_bus=None,
        **kwargs
    ):
        """
        Initialize the entry display view.
        
        Args:
            parent: The parent widget or window
            event_bus: Optional event bus for notifications
            **kwargs: Additional keyword arguments
        """
        super().__init__(parent, event_bus, **kwargs)
        
        # Current entry data
        self.current_entry = None
        self.current_headword = None
        self.focused_meaning_index = -1
        self.focused_example_index = -1
        
        # Create UI components
        self._create_header_area()
        self._create_content_area()
        self._create_action_buttons()
        
        # Configure grid layout
        self.frame.grid_rowconfigure(1, weight=1)  # Content area takes remaining space
        self.frame.grid_columnconfigure(0, weight=1)
        
        # Tag configurations for the text widget
        self._configure_text_tags()
    
    def _create_header_area(self):
        """Create the header area with headword and language info."""
        header_frame = ttk.Frame(self.frame)
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Headword label
        self.headword_var = tk.StringVar()
        self.headword_label = ttk.Label(
            header_frame,
            textvariable=self.headword_var,
            style="Headword.TLabel"
        )
        self.headword_label.pack(side=tk.LEFT, padx=5)
        
        # Language info label
        self.language_info_var = tk.StringVar()
        self.language_info_label = ttk.Label(
            header_frame,
            textvariable=self.language_info_var
        )
        self.language_info_label.pack(side=tk.RIGHT, padx=5)
        
        # Store in widgets dict for later access
        self.widgets['headword_label'] = self.headword_label
        self.widgets['language_info_label'] = self.language_info_label
    
    def _create_content_area(self):
        """Create the main content area for displaying entry details."""
        content_frame = ttk.Frame(self.frame)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Configure layout - maximize available space
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        
        # Make sure the frame itself gets maximum space
        self.frame.grid_rowconfigure(1, weight=1)  # Make content area take all available vertical space
        self.frame.grid_columnconfigure(0, weight=1)  # Make content area take all available horizontal space
        
        # Create text widget with scrollbar with enhanced wrapping
        self.content_text = enhance_text_widget(tk.Text(
            content_frame,
            wrap=tk.WORD,  # Ensure text wrapping
            padx=20,
            pady=20,
            width=80,      # Set width in characters
            height=24,     # Set height in lines
            state=tk.DISABLED,  # Read-only initially
            cursor="arrow",
            spacing1=4,    # Increased space above paragraph
            spacing2=0,    # No extra space between wrapped lines
            spacing3=8     # Increased space below paragraph
        ))
        
        # Scrollbar
        self.scrollbar = ttk.Scrollbar(
            content_frame,
            orient=tk.VERTICAL,
            command=self.content_text.yview
        )
        self.content_text.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack into frame
        self.content_text.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bind events
        self.content_text.bind("<ButtonRelease-1>", self._on_text_click)
        self.content_text.bind("<Key>", lambda e: "break")  # Prevent editing
        self.content_text.bind("<Configure>", self._on_resize)  # Handle resize events
        
        # Store in widgets dict for later access
        self.widgets['content_text'] = self.content_text
    
    def _create_action_buttons(self):
        """Create action buttons for operations on the entry."""
        button_frame = ttk.Frame(self.frame)
        button_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        # Regenerate button
        self.regenerate_button = ttk.Button(
            button_frame,
            text="♻️ Regenerate",
            command=self._on_regenerate
        )
        self.regenerate_button.pack(side=tk.LEFT, padx=5)
        
        # Export to Anki button
        self.export_button = ttk.Button(
            button_frame,
            text="📤 Export to Anki",
            command=self._on_export_to_anki
        )
        self.export_button.pack(side=tk.LEFT, padx=5)
        
        # Copy button
        self.copy_button = ttk.Button(
            button_frame,
            text="📋 Copy",
            command=self._on_copy
        )
        self.copy_button.pack(side=tk.LEFT, padx=5)
        
        # Delete button
        self.delete_button = ttk.Button(
            button_frame,
            text="🗑️ Delete",
            command=self._on_delete
        )
        self.delete_button.pack(side=tk.RIGHT, padx=5)
        
        # Store in widgets dict for later access
        self.widgets['regenerate_button'] = self.regenerate_button
        self.widgets['export_button'] = self.export_button
        self.widgets['copy_button'] = self.copy_button
        self.widgets['delete_button'] = self.delete_button
    
    def _configure_text_tags(self):
        """Configure text tags for formatting the entry display."""
        text = self.content_text
        
        # Base font size (will be scaled)
        base_font_size = 10
        
        # Basic tags
        text.tag_configure("headword", font=("TkDefaultFont", int(base_font_size * 1.6), "bold"))
        text.tag_configure("part_of_speech", font=("TkDefaultFont", int(base_font_size * 0.9), "italic"))
        text.tag_configure("grammar", font=("TkDefaultFont", int(base_font_size * 0.9), "italic"))
        text.tag_configure("meaning_number", font=("TkDefaultFont", int(base_font_size * 1.2), "bold"))
        # Set up definition tag with guaranteed wrapping properties
        text.tag_configure("definition", font=("TkDefaultFont", int(base_font_size * 1.1)),
                          lmargin1=40, lmargin2=40,  # Use consistent margins for multi-line text
                          rmargin=20,  # Right margin to ensure text doesn't touch the scrollbar
                          wrap="word")  # Force word wrapping for this tag
        text.tag_configure("example", font=("TkDefaultFont", int(base_font_size), "italic"))
        text.tag_configure("translation", font=("TkDefaultFont", int(base_font_size)))
        text.tag_configure("section_header", font=("TkDefaultFont", int(base_font_size * 1.2), "bold"))
        
        # Colorized tags
        text.tag_configure("meaning_focus", background="#e6f3ff")
        text.tag_configure("example_focus", background="#e6fff3")
        
        # Clickable tags
        text.tag_configure("clickable", foreground="blue", underline=True)
        text.tag_configure("clickable_export", foreground="green", underline=True)
        
        # Configure bindings for clickable elements
        text.tag_bind("clickable", "<Enter>", lambda e: text.configure(cursor="hand2"))
        text.tag_bind("clickable", "<Leave>", lambda e: text.configure(cursor="arrow"))
        text.tag_bind("clickable_export", "<Enter>", lambda e: text.configure(cursor="hand2"))
        text.tag_bind("clickable_export", "<Leave>", lambda e: text.configure(cursor="arrow"))
    
    def display_entry(self, entry: DictionaryEntry):
        """
        Display a dictionary entry in the view.
        
        Args:
            entry: The dictionary entry to display
        """
        # Store the current entry
        self.current_entry = entry
        self.current_headword = entry.get('headword', '')
        
        # Reset focus indices
        self.focused_meaning_index = -1
        self.focused_example_index = -1
        
        # Update header information
        self._update_header_info(entry)
        
        # Clear and enable text widget for editing
        self.content_text.configure(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        
        # Insert the entry content
        self._insert_entry_content(entry)
        
        # Make text widget read-only again
        self.content_text.configure(state=tk.DISABLED)
        
        # Notify of entry display
        if self.event_bus:
            self.event_bus.publish('entry:displayed', {
                'headword': entry.get('headword', ''),
                'entry_id': entry.get('id')
            })
    
    def clear_display(self):
        """Clear the entry display."""
        # Reset current entry
        self.current_entry = None
        self.current_headword = None
        self.focused_meaning_index = -1
        self.focused_example_index = -1
        
        # Clear header
        self.headword_var.set("")
        self.language_info_var.set("")
        
        # Clear content
        self.content_text.configure(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        self.content_text.configure(state=tk.DISABLED)
        
        # Notify of display clear
        if self.event_bus:
            self.event_bus.publish('entry:display_cleared', {})
    
    def set_loading_state(self, is_loading: bool):
        """
        Set the loading state of the entry display.
        
        Args:
            is_loading: Whether the display is in a loading state
        """
        if is_loading:
            # Show loading message
            self.content_text.configure(state=tk.NORMAL)
            self.content_text.delete(1.0, tk.END)
            self.content_text.insert(tk.END, "Loading...", "section_header")
            self.content_text.configure(state=tk.DISABLED)
            
            # Disable buttons
            for button in [self.regenerate_button, self.export_button, 
                          self.copy_button, self.delete_button]:
                button.configure(state=tk.DISABLED)
        else:
            # Re-enable buttons if we have an entry
            button_state = tk.NORMAL if self.current_entry else tk.DISABLED
            for button in [self.regenerate_button, self.export_button, 
                          self.copy_button, self.delete_button]:
                button.configure(state=button_state)
    
    def focus_meaning(self, meaning_index: int):
        """
        Focus a specific meaning in the entry.
        
        Args:
            meaning_index: Index of the meaning to focus
        """
        if not self.current_entry or 'meanings' not in self.current_entry:
            return
            
        meanings = self.current_entry.get('meanings', [])
        if meaning_index < 0 or meaning_index >= len(meanings):
            return
            
        # Update focus indices
        self.focused_meaning_index = meaning_index
        self.focused_example_index = -1
        
        # Redisplay entry with new focus
        self.display_entry(self.current_entry)
        
        # Scroll to the focused meaning
        self._scroll_to_meaning(meaning_index)
        
        # Notify of meaning focus
        if self.event_bus:
            self.event_bus.publish('entry:meaning_focused', {
                'headword': self.current_headword,
                'meaning_index': meaning_index
            })
    
    def focus_example(self, meaning_index: int, example_index: int):
        """
        Focus a specific example in the entry.
        
        Args:
            meaning_index: Index of the meaning containing the example
            example_index: Index of the example to focus
        """
        if not self.current_entry or 'meanings' not in self.current_entry:
            return
            
        meanings = self.current_entry.get('meanings', [])
        if meaning_index < 0 or meaning_index >= len(meanings):
            return
            
        examples = meanings[meaning_index].get('examples', [])
        if example_index < 0 or example_index >= len(examples):
            return
            
        # Update focus indices
        self.focused_meaning_index = meaning_index
        self.focused_example_index = example_index
        
        # Redisplay entry with new focus
        self.display_entry(self.current_entry)
        
        # Scroll to the focused example
        self._scroll_to_example(meaning_index, example_index)
        
        # Notify of example focus
        if self.event_bus:
            self.event_bus.publish('entry:example_focused', {
                'headword': self.current_headword,
                'meaning_index': meaning_index,
                'example_index': example_index
            })
    
    def update_scale(self):
        """Update UI elements based on the current scale factor."""
        # Update base view scaling
        super().update_scale()
        
        # Reconfigure text tags with scaled font sizes
        text = self.content_text
        base_font_size = 10
        scaled_size = int(base_font_size * self.scale_factor)
        
        # Update tag configurations with scaled fonts
        text.tag_configure("headword", font=("TkDefaultFont", int(scaled_size * 1.6), "bold"))
        text.tag_configure("part_of_speech", font=("TkDefaultFont", int(scaled_size * 0.9), "italic"))
        text.tag_configure("grammar", font=("TkDefaultFont", int(scaled_size * 0.9), "italic"))
        text.tag_configure("meaning_number", font=("TkDefaultFont", int(scaled_size * 1.2), "bold"))
        # Maintain definition display configuration with scaling
        text.tag_configure("definition", font=("TkDefaultFont", int(scaled_size * 1.1)),
                          lmargin1=40, lmargin2=40,  # Use consistent margins for multi-line text 
                          rmargin=20,  # Right margin to ensure text doesn't touch the scrollbar
                          wrap="word")  # Force word wrapping for this tag
        text.tag_configure("example", font=("TkDefaultFont", int(scaled_size), "italic"))
        text.tag_configure("translation", font=("TkDefaultFont", int(scaled_size)))
        text.tag_configure("section_header", font=("TkDefaultFont", int(scaled_size * 1.2), "bold"))
        
        # Update default font for the text widget
        text.configure(font=("TkDefaultFont", scaled_size))
        
        # Update header label fonts
        self.headword_label.configure(font=("TkDefaultFont", int(scaled_size * 1.6), "bold"))
        self.language_info_label.configure(font=("TkDefaultFont", scaled_size))
        
        # Redisplay current entry with new scaling if available
        if self.current_entry:
            self.display_entry(self.current_entry)
            
    def _on_resize(self, event):
        """Handle window resize events to adjust definition wrapping."""
        # Only process events from the content text widget
        if event.widget == self.content_text:
            # Get current width
            width = event.width
            
            # Update all definition labels to match new width
            # Skip if width is too small or undefined
            if width > 100:
                # Find all embedded labels and update them
                for definition_frame in self.content_text.window_names():
                    try:
                        frame = self.content_text.nametowidget(definition_frame)
                        # Find label within the frame
                        for child in frame.winfo_children():
                            if isinstance(child, ttk.Label):
                                # Update label wrap length
                                child.configure(wraplength=width - 60)
                    except:
                        # Skip if there's any error
                        pass
    
    def _update_header_info(self, entry: DictionaryEntry):
        """
        Update the header information based on the entry.
        
        Args:
            entry: The dictionary entry
        """
        # Set headword
        headword = entry.get('headword', '')
        self.headword_var.set(headword)
        
        # Set language info
        metadata = entry.get('metadata', {})
        target_language = metadata.get('target_language', '')
        definition_language = metadata.get('definition_language', '')
        
        language_info = f"{target_language} → {definition_language}"
        self.language_info_var.set(language_info)
    
    def _insert_entry_content(self, entry: DictionaryEntry):
        """
        Insert the entry content into the text widget.
        
        Args:
            entry: The dictionary entry to display
        """
        text = self.content_text
        
        # Insert headword and part of speech
        part_of_speech = entry.get('part_of_speech', '')
        if isinstance(part_of_speech, list):
            part_of_speech = ', '.join(part_of_speech)
            
        # text.insert(tk.END, f"{entry.get('headword', '')}\n", "headword")
        if part_of_speech:
            text.insert(tk.END, f"{part_of_speech}\n\n", "part_of_speech")
        else:
            text.insert(tk.END, "\n")
        
        # Insert meanings
        meanings = entry.get('meanings', [])
        for i, meaning in enumerate(meanings):
            # Determine if this meaning is focused
            is_focused = (i == self.focused_meaning_index)
            
            # Meaning number tag
            meaning_tag = "meaning_focus" if is_focused else "meaning_number"
            
            # Insert meaning number and definition
            text.insert(tk.END, f"{i+1}. ", meaning_tag)
            
            # Get definition and ensure proper wrapping for long sentences
            definition = meaning.get('definition', '')
            
            # Insert definition with maximum wrapping area and indentation
            # Move to a new line for better separation
            text.insert(tk.END, "\n", "definition")
            
            # Insert the definition text directly with proper indentation and tag
            # The definition tag is configured with proper margins to ensure wrapping
            text.insert(tk.END, f"    {definition}\n\n", "definition")
            
            # Insert grammar information if available
            grammar = meaning.get('grammar', {})
            grammar_parts = []
            
            if grammar.get('noun_type'):
                grammar_parts.append(f"Noun type: {grammar['noun_type']}")
            if grammar.get('verb_type'):
                grammar_parts.append(f"Verb type: {grammar['verb_type']}")
            if grammar.get('comparison'):
                grammar_parts.append(f"Comparison: {grammar['comparison']}")
                
            if grammar_parts:
                grammar_text = ", ".join(grammar_parts)
                text.insert(tk.END, f"   ({grammar_text})\n", "grammar")
            
            # Insert examples
            examples = meaning.get('examples', [])
            if examples:
                text.insert(tk.END, "   Examples:\n", "section_header")
                
                for j, example in enumerate(examples):
                    # Determine if this example is focused
                    is_example_focused = (is_focused and j == self.focused_example_index)
                    example_tag = "example_focus" if is_example_focused else "example"
                    
                    # Example sentence tag includes meaning and example indices for click handler
                    example_id = f"example_{i}_{j}"
                    
                    # Insert example sentence
                    text.insert(tk.END, f"   • ", example_tag)
                    text.insert(tk.END, f"{example.get('sentence', '')}\n", (example_tag, example_id))
                    
                    # Insert translation if available
                    if 'translation' in example and example['translation']:
                        text.insert(tk.END, f"     {example.get('translation', '')}\n", "translation")
                    
                    # Add export button for this example
                    export_tag = f"export_{i}_{j}"
                    text.insert(tk.END, f"     [Export to Anki]\n", ("clickable_export", export_tag))
                    text.tag_bind(export_tag, "<Button-1>", 
                                 lambda e, m=i, ex=j: self._on_export_example(m, ex))
            
            # Add spacing between meanings
            text.insert(tk.END, "\n")
    
    def _scroll_to_meaning(self, meaning_index: int):
        """
        Scroll the text widget to show a specific meaning.
        
        Args:
            meaning_index: Index of the meaning to scroll to
        """
        text = self.content_text
        
        try:
            # Find the position of the meaning number
            start_pos = text.search(f"{meaning_index+1}. ", "1.0", tk.END)
            if start_pos:
                # Ensure visible
                text.see(start_pos)
        except Exception:
            pass
    
    def _scroll_to_example(self, meaning_index: int, example_index: int):
        """
        Scroll the text widget to show a specific example.
        
        Args:
            meaning_index: Index of the meaning containing the example
            example_index: Index of the example to scroll to
        """
        text = self.content_text
        
        try:
            # Find the position of the example
            example_id = f"example_{meaning_index}_{example_index}"
            start_pos = text.search(f"   • ", "1.0", tk.END, tag=example_id)
            if start_pos:
                # Ensure visible
                text.see(start_pos)
        except Exception:
            pass
    
    # Event handlers
    
    def _on_text_click(self, event):
        """Handle click event in the text widget."""
        text = self.content_text
        try:
            # Get the position of the click
            index = text.index(f"@{event.x},{event.y}")
            
            # Check if the click is on a tagged element
            tags = text.tag_names(index)
            
            for tag in tags:
                # Check for example tags
                if tag.startswith("example_"):
                    parts = tag.split("_")
                    if len(parts) == 3:
                        meaning_index = int(parts[1])
                        example_index = int(parts[2])
                        self.focus_example(meaning_index, example_index)
                        return
                        
                # Check for export tags
                elif tag.startswith("export_"):
                    parts = tag.split("_")
                    if len(parts) == 3:
                        meaning_index = int(parts[1])
                        example_index = int(parts[2])
                        self._on_export_example(meaning_index, example_index)
                        return
        except Exception:
            pass
    
    def _on_regenerate(self):
        """Handle regenerate button click."""
        if not self.current_entry or not self.current_headword:
            return
            
        # Notify of regenerate request
        if self.event_bus:
            self.event_bus.publish('entry:regenerate_requested', {
                'headword': self.current_headword,
                'entry': self.current_entry
            })
    
    def _on_export_to_anki(self):
        """Handle export to Anki button click."""
        if not self.current_entry or not self.current_headword:
            return
            
        # If a specific meaning and example are focused, export that
        if self.focused_meaning_index >= 0 and self.focused_example_index >= 0:
            self._on_export_example(self.focused_meaning_index, self.focused_example_index)
            return
            
        # Otherwise notify of general export request
        if self.event_bus:
            self.event_bus.publish('entry:export_requested', {
                'headword': self.current_headword,
                'entry': self.current_entry
            })
    
    def _on_export_example(self, meaning_index: int, example_index: int):
        """
        Handle export example to Anki click.
        
        Args:
            meaning_index: Index of the meaning containing the example
            example_index: Index of the example to export
        """
        if not self.current_entry or not self.current_headword:
            return
            
        # Notify of example export request
        if self.event_bus:
            self.event_bus.publish('entry:export_example_requested', {
                'headword': self.current_headword,
                'entry': self.current_entry,
                'meaning_index': meaning_index,
                'example_index': example_index
            })
    
    def _on_copy(self):
        """Handle copy button click."""
        if not self.current_entry:
            return
            
        try:
            # Format entry as JSON
            entry_json = json.dumps(self.current_entry, indent=2, ensure_ascii=False)
            
            # Copy to clipboard
            self.frame.clipboard_clear()
            self.frame.clipboard_append(entry_json)
            
            # Notify of copy
            if self.event_bus:
                self.event_bus.publish('entry:copied', {
                    'headword': self.current_headword
                })
        except Exception as e:
            # Notify of copy error
            if self.event_bus:
                self.event_bus.publish('error:copy', {
                    'message': f"Failed to copy entry: {str(e)}"
                })
    
    def _on_delete(self):
        """Handle delete button click."""
        if not self.current_entry or not self.current_headword:
            return
            
        # Notify of delete request
        if self.event_bus:
            self.event_bus.publish('entry:delete_requested', {
                'headword': self.current_headword,
                'entry': self.current_entry
            })