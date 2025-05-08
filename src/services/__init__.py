"""
Services Package

This package contains service components for the DeepDict application,
providing access to external resources and cross-cutting functionality.

Services included:
- async_service: Generic asynchronous task processing with progress reporting
- base_service: Base class for all service components
- anki_service: Integration with Anki for flashcard creation
- database_service: Database operations with connection pooling and transaction management
- request_service: Asynchronous API request handling service
"""

from .base_service import BaseService
from .anki_service import AnkiService
from .async_service import AsyncService
from .database_service import DatabaseService
from .request_service import RequestService

__all__ = [
    'AsyncService',
    'BaseService',
    'AnkiService',
    'DatabaseService',
    'RequestService'
]