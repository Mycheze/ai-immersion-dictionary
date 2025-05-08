"""
DeepDict Application

This is the main entry point for the DeepDict application, implementing
an MVC architecture for better maintainability and organization.
"""

import tkinter as tk
import os
import sys
from pathlib import Path

# Add the source directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import components
from src.utils.event_bus import EventBus
from src.utils.error_handler import ErrorHandler, ErrorSeverity
from src.utils.logger import configure as configure_logger
from src.utils.log_handler import create_log_handler

# Models
from src.models.dictionary_model import DictionaryModel
from src.models.user_model import UserModel
from src.models.api_model import APIModel
from src.models.anki_model import AnkiModel

# Views
from src.views.main_window import MainWindowView
from src.views.search_panel import SearchPanelView
from src.views.entry_display import EntryDisplayView
from src.views.language_filter import LanguageFilterView

# Controllers
from src.controllers.app_controller import AppController
from src.controllers.search_controller import SearchController
from src.controllers.entry_controller import EntryController
from src.controllers.settings_controller import SettingsController

# Services
from src.services.anki_service import AnkiService
from src.services.async_service import AsyncService
from src.services.database_service import DatabaseService
from src.services.request_service import RequestService


def main():
    """Initialize and run the DeepDict application."""
    # Create the root window
    root = tk.Tk()
    
    # Create the event bus
    event_bus = EventBus()
    
    # Configure logging system
    configure_logger({
        'console_level': 'INFO',
        'file_level': 'DEBUG'
    })
    
    # Create log handler to connect events to logs
    log_handler = create_log_handler(event_bus)
    
    # Create the error handler
    error_handler = ErrorHandler(event_bus)
    
    try:
        # Initialize services first
        from src.utils import logger
        logger.info("Starting DeepDict application", "main")
        logger.info("Initializing services", "main")
        
        async_service = AsyncService(max_workers=4, event_bus=event_bus)
        database_service = DatabaseService(event_bus=event_bus)
        anki_service = AnkiService(event_bus=event_bus)
        
        # Initialize models
        logger.info("Initializing models", "main")
        
        # Create models
        user_model = UserModel(event_bus=event_bus)
        dictionary_model = DictionaryModel(database_service, async_service=async_service, event_bus=event_bus)
        api_model = APIModel(event_bus=event_bus)
        anki_model = AnkiModel(anki_service=anki_service, event_bus=event_bus)
        
        # Create additional services that depend on models
        request_service = RequestService(dictionary_engine=api_model.client, event_bus=event_bus)
        
        # Create views
        logger.info("Initializing views", "main")
        main_window = MainWindowView(root, event_bus=event_bus)
        search_panel = SearchPanelView(main_window.frame, event_bus=event_bus)
        entry_display = EntryDisplayView(main_window.frame, event_bus=event_bus)
        language_filter = LanguageFilterView(main_window.frame, event_bus=event_bus)
        
        # Create controllers
        logger.info("Initializing controllers", "main")
        models = {
            'user': user_model,
            'dictionary': dictionary_model,
            'api': api_model,
            'anki': anki_model,
            'async_service': async_service,
            'request_service': request_service
        }
        
        views = {
            'main_window': main_window,
            'search_panel': search_panel,
            'entry_display': entry_display,
            'language_filter': language_filter
        }
        
        # Create controllers
        search_controller = SearchController(models, views, event_bus)
        entry_controller = EntryController(models, views, event_bus)
        settings_controller = SettingsController(models, views, event_bus)
        
        # Create the main app controller
        app_controller = AppController(root, models, views, event_bus)
        
        # Add child controllers to app controller
        app_controller.add_controller('search', search_controller)
        app_controller.add_controller('entry', entry_controller)
        app_controller.add_controller('settings', settings_controller)
        
        # Start the application
        logger.info("Starting DeepDict UI", "main")
        app_controller.start()
        
    except Exception as e:
        # Handle fatal errors
        error_handler.handle_exception(
            e,
            "Fatal error during application startup",
            ErrorSeverity.FATAL
        )


if __name__ == "__main__":
    main()