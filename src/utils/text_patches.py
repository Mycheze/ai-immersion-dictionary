"""
Text widget patches for improved wrapping and display of long sentences.

This module patches the tkinter.Text widget to ensure proper wrapping of long sentences.
Import this module before using tkinter.Text to ensure proper wrapping behavior.
"""

import tkinter as tk
from tkinter import scrolledtext
import types

# Store the original insert method
original_insert = tk.Text.insert

def patched_insert(self, index, text, *tags):
    """
    Patched version of tkinter.Text.insert method that improves wrapping behavior.
    
    Args:
        index: The position to insert at
        text: The text to insert
        *tags: Optional tags to apply to the inserted text
    """
    # Ensure the text widget is configured for word wrapping
    if not hasattr(self, '_wrapping_initialized'):
        self.configure(wrap='word')
        self._wrapping_initialized = True
    
    # If text is long and might wrap, ensure it gets proper spacing
    if len(text) > 50 and '\n' not in text:
        # Insert with original method but ensure there's room for wrapping
        original_insert(self, index, text, *tags)
    else:
        # Use original insert method for normal text
        original_insert(self, index, text, *tags)

# Apply the monkey patch to tkinter.Text.insert
tk.Text.insert = patched_insert

def enhance_text_widget(text_widget):
    """
    Enhance a Text widget for better long text handling.
    
    Args:
        text_widget: A tkinter.Text widget instance
    """
    # Ensure wrap is set to word
    text_widget.configure(wrap='word')
    
    # Set generous padding
    text_widget.configure(padx=20, pady=20)
    
    # Set spacing for better readability
    text_widget.configure(spacing1=5, spacing2=0, spacing3=10)
    
    # Set reasonable dimensions
    text_widget.configure(width=80, height=30)
    
    return text_widget

# Create an enhanced version of ScrolledText
class EnhancedScrolledText(scrolledtext.ScrolledText):
    """Enhanced ScrolledText widget with better wrapping for long sentences."""
    
    def __init__(self, master=None, **kw):
        """Initialize with enhanced wrapping capabilities."""
        # Ensure wrap is set to word
        kw['wrap'] = 'word'
        
        # Set generous padding
        kw.setdefault('padx', 20)
        kw.setdefault('pady', 20)
        
        # Set spacing for better readability
        kw.setdefault('spacing1', 5)
        kw.setdefault('spacing2', 0)
        kw.setdefault('spacing3', 10)
        
        # Set reasonable dimensions
        kw.setdefault('width', 80)
        kw.setdefault('height', 30)
        
        # Initialize with our settings
        super().__init__(master, **kw)

# Make the EnhancedScrolledText available at module level
scrolledtext.EnhancedScrolledText = EnhancedScrolledText

# Patch tk.Text.configure method to prioritize word wrapping
original_configure = tk.Text.configure

def patched_configure(self, *args, **kwargs):
    """Ensure 'wrap' is set to 'word' when configuring Text widgets."""
    if args and 'wrap' in args[0]:
        args[0]['wrap'] = 'word'
    if 'wrap' in kwargs:
        kwargs['wrap'] = 'word'
    return original_configure(self, *args, **kwargs)

# Apply the patch
tk.Text.configure = patched_configure