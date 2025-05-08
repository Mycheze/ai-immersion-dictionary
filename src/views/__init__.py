"""
Views Package

This package contains view components for the DeepDict application,
representing the visual elements and user interface.

Views included:
- base_view: Base class for all view components
- main_window: Main application window
- search_panel: Search interface for dictionary lookups
- entry_display: Dictionary entry display component
- language_filter: Language filtering component
"""

from .base_view import BaseView
from .main_window import MainWindowView
from .search_panel import SearchPanelView
from .entry_display import EntryDisplayView
from .language_filter import LanguageFilterView

__all__ = [
    'BaseView',
    'MainWindowView',
    'SearchPanelView',
    'EntryDisplayView',
    'LanguageFilterView'
]