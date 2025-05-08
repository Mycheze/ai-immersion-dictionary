"""
Common type definitions used throughout the application.

This module defines TypedDict classes and other type aliases for consistent
type annotations across the codebase.
"""

from typing import Dict, List, Any, Optional, Union, TypedDict, Callable

# Dictionary Entry Related Types
class GrammarInfo(TypedDict, total=False):
    """Grammar information for a dictionary entry meaning."""
    noun_type: Optional[str]
    verb_type: Optional[str]
    comparison: Optional[str]

class Example(TypedDict):
    """Example sentence for a dictionary entry meaning."""
    sentence: str
    translation: Optional[str]
    is_context_sentence: Optional[bool]

class Meaning(TypedDict):
    """Meaning/definition within a dictionary entry."""
    definition: str
    grammar: GrammarInfo
    examples: List[Example]

class EntryMetadata(TypedDict):
    """Metadata for a dictionary entry."""
    source_language: str
    target_language: str
    definition_language: str
    has_context: Optional[bool]
    context_sentence: Optional[str]

class DictionaryEntry(TypedDict):
    """Complete dictionary entry."""
    metadata: EntryMetadata
    headword: str
    part_of_speech: Union[str, List[str]]
    meanings: List[Meaning]

# API and Request Related Types
class APIRequestParams(TypedDict, total=False):
    """Parameters for an API request."""
    word: str
    target_lang: Optional[str]
    source_lang: Optional[str]
    definition_lang: Optional[str]
    sentence_context: Optional[str]
    variation_prompt: Optional[str]
    variation_seed: Optional[str]
    language_name: Optional[str]

# UI Component Types
class UIComponentProps(TypedDict, total=False):
    """Common properties for UI components."""
    parent: Any  # Tkinter parent widget
    event_bus: Any  # EventBus instance
    width: Optional[int]
    height: Optional[int]
    padding: Optional[Union[int, tuple]]
    scale_factor: Optional[float]

# Callback Types
ErrorCallback = Callable[[str], None]
SuccessCallback = Callable[[Any], None]
ProgressCallback = Callable[[int, int], None]

# Configuration Types
class AnkiFieldMapping(TypedDict):
    """Mapping of Anki note fields to dictionary entry data."""
    field: str
    path: str
    default: Optional[str]

class AnkiNoteTypeConfig(TypedDict):
    """Configuration for an Anki note type."""
    deck: str
    field_mappings: Dict[str, str]
    empty_field_handling: Dict[str, Any]

# Search and Filter Types
class SearchFilters(TypedDict, total=False):
    """Filters for dictionary entry searches."""
    search_term: Optional[str]
    target_language: Optional[str]
    source_language: Optional[str]
    definition_language: Optional[str]
    has_context: Optional[bool]