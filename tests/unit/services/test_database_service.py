"""
Tests for the DatabaseService class.

This module contains tests for the DatabaseService, which provides
a service for database operations with connection pooling.
"""

import pytest
import os
import sqlite3
from pathlib import Path
import threading
import time
from unittest.mock import Mock, patch

from src.services.database_service import DatabaseService
from src.utils.event_bus import EventBus

class TestDatabaseService:
    """Tests for the DatabaseService class."""
    
    @pytest.fixture
    def event_bus(self):
        """Fixture for creating an EventBus instance."""
        return EventBus()
    
    @pytest.fixture
    def temp_db_path(self, tmpdir):
        """Fixture for creating a temporary database path."""
        return os.path.join(tmpdir, "test_db.sqlite")
    
    @pytest.fixture
    def db_service(self, temp_db_path, event_bus):
        """Fixture for creating a DatabaseService instance with a temporary database."""
        # Create service with test database
        service = DatabaseService(db_path=temp_db_path, pool_size=3, event_bus=event_bus)
        
        # Yield the service for the test
        yield service
        
        # Cleanup after test
        service.shutdown()
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except:
                pass
    
    def test_initialization(self, temp_db_path, event_bus):
        """Test that the DatabaseService initializes correctly."""
        # Create service
        service = DatabaseService(db_path=temp_db_path, pool_size=3, event_bus=event_bus)
        
        # Check initialization
        assert service.db_path == Path(temp_db_path)
        assert service.pool_size == 3
        assert service.event_bus == event_bus
        assert service.connection_pool.maxsize == 3
        
        # Check that tables are created
        with service._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if the entries table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
            result = cursor.fetchone()
            assert result is not None
            
            # Check if the lemmas table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lemmas'")
            result = cursor.fetchone()
            assert result is not None
            
            # Check if the languages table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='languages'")
            result = cursor.fetchone()
            assert result is not None
        
        # Clean up
        service.shutdown()
    
    def test_connection_pooling(self, db_service):
        """Test that connection pooling works correctly."""
        # Get multiple connections
        conn1 = db_service._get_connection()
        conn2 = db_service._get_connection()
        conn3 = db_service._get_connection()
        
        # Check that connections are different
        assert conn1 != conn2
        assert conn1 != conn3
        assert conn2 != conn3
        
        # Return connections to pool
        db_service._release_connection(conn1)
        db_service._release_connection(conn2)
        db_service._release_connection(conn3)
        
        # Get connections again, should be reused
        conn4 = db_service._get_connection()
        conn5 = db_service._get_connection()
        conn6 = db_service._get_connection()
        
        # Check that connections are reused (not necessarily in the same order)
        assert conn4 in [conn1, conn2, conn3]
        assert conn5 in [conn1, conn2, conn3]
        assert conn6 in [conn1, conn2, conn3]
        
        # Return connections to pool
        db_service._release_connection(conn4)
        db_service._release_connection(conn5)
        db_service._release_connection(conn6)
    
    def test_connection_context_manager(self, db_service):
        """Test the connection context manager."""
        # Use context manager to get a connection
        with db_service._get_connection() as conn:
            # Check that connection is valid
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result == (1,)
        
        # Connection should be returned to pool after context exit
        assert db_service.connection_pool.qsize() == db_service.pool_size
    
    def test_add_and_get_entry(self, db_service):
        """Test adding and retrieving dictionary entries."""
        # Create a test entry
        entry = {
            "headword": "test",
            "part_of_speech": "noun",
            "metadata": {
                "source_language": "English",
                "target_language": "Czech",
                "definition_language": "English"
            },
            "meanings": [
                {
                    "definition": "A procedure to evaluate something",
                    "examples": [
                        {
                            "sentence": "We need to run a test.",
                            "translation": "Potřebujeme provést test."
                        }
                    ]
                }
            ]
        }
        
        # Add the entry
        entry_id = db_service.add_entry(entry)
        
        # Check that an ID was returned
        assert entry_id is not None
        assert isinstance(entry_id, int)
        
        # Get the entry by headword
        retrieved_entry = db_service.get_entry_by_headword(
            headword="test",
            source_lang="English",
            target_lang="Czech",
            definition_lang="English"
        )
        
        # Check that the entry was retrieved correctly
        assert retrieved_entry is not None
        assert retrieved_entry["headword"] == "test"
        assert retrieved_entry["metadata"]["target_language"] == "Czech"
        assert len(retrieved_entry["meanings"]) == 1
        assert retrieved_entry["meanings"][0]["definition"] == "A procedure to evaluate something"
    
    def test_search_entries(self, db_service):
        """Test searching for dictionary entries."""
        # Add multiple test entries
        entries = [
            {
                "headword": "apple",
                "part_of_speech": "noun",
                "metadata": {
                    "source_language": "English",
                    "target_language": "Czech",
                    "definition_language": "English"
                },
                "meanings": [{"definition": "A fruit"}]
            },
            {
                "headword": "banana",
                "part_of_speech": "noun",
                "metadata": {
                    "source_language": "English",
                    "target_language": "Czech",
                    "definition_language": "English"
                },
                "meanings": [{"definition": "A yellow fruit"}]
            },
            {
                "headword": "orange",
                "part_of_speech": "noun",
                "metadata": {
                    "source_language": "English",
                    "target_language": "Spanish",
                    "definition_language": "English"
                },
                "meanings": [{"definition": "A citrus fruit"}]
            }
        ]
        
        for entry in entries:
            db_service.add_entry(entry)
        
        # Search with no filters
        results = db_service.search_entries()
        assert len(results) == 3
        
        # Search by search term
        results = db_service.search_entries(search_term="app")
        assert len(results) == 1
        assert results[0]["headword"] == "apple"
        
        # Search by target language
        results = db_service.search_entries(target_lang="Czech")
        assert len(results) == 2
        assert sorted([r["headword"] for r in results]) == ["apple", "banana"]
        
        # Search by target language and search term
        results = db_service.search_entries(search_term="ban", target_lang="Czech")
        assert len(results) == 1
        assert results[0]["headword"] == "banana"
        
        # Search with limit and offset
        results = db_service.search_entries(limit=1)
        assert len(results) == 1
        
        results = db_service.search_entries(limit=1, offset=1)
        assert len(results) == 1
        assert results[0]["headword"] != "apple"  # Should be second entry
    
    def test_get_all_languages(self, db_service):
        """Test getting all languages."""
        # Add entries with different languages
        entries = [
            {
                "headword": "apple",
                "metadata": {
                    "source_language": "English",
                    "target_language": "Czech",
                    "definition_language": "English"
                }
            },
            {
                "headword": "banana",
                "metadata": {
                    "source_language": "English",
                    "target_language": "Spanish",
                    "definition_language": "English"
                }
            },
            {
                "headword": "orange",
                "metadata": {
                    "source_language": "German",
                    "target_language": "French",
                    "definition_language": "German"
                }
            }
        ]
        
        for entry in entries:
            db_service.add_entry(entry)
        
        # Get all languages
        languages = db_service.get_all_languages()
        
        # Check that all languages were retrieved
        assert "target_languages" in languages
        assert "source_languages" in languages
        assert "definition_languages" in languages
        
        assert set(languages["target_languages"]) == {"Czech", "Spanish", "French"}
        assert set(languages["source_languages"]) == {"English", "German"}
        assert set(languages["definition_languages"]) == {"English", "German"}
    
    def test_delete_entry(self, db_service):
        """Test deleting a dictionary entry."""
        # Add a test entry
        entry = {
            "headword": "test",
            "metadata": {
                "source_language": "English",
                "target_language": "Czech",
                "definition_language": "English"
            }
        }
        
        db_service.add_entry(entry)
        
        # Verify it exists
        result = db_service.get_entry_by_headword(
            headword="test",
            source_lang="English",
            target_lang="Czech",
            definition_lang="English"
        )
        assert result is not None
        
        # Delete the entry
        deleted = db_service.delete_entry(
            headword="test",
            source_lang="English",
            target_lang="Czech",
            definition_lang="English"
        )
        
        # Check that the entry was deleted
        assert deleted is True
        
        # Verify it doesn't exist anymore
        result = db_service.get_entry_by_headword(
            headword="test",
            source_lang="English",
            target_lang="Czech",
            definition_lang="English"
        )
        assert result is None
        
        # Try to delete a non-existent entry
        deleted = db_service.delete_entry(
            headword="nonexistent",
            source_lang="English",
            target_lang="Czech",
            definition_lang="English"
        )
        assert deleted is False
    
    def test_lemma_caching(self, db_service):
        """Test caching and retrieving lemmas."""
        # Cache a lemma
        db_service.cache_lemma("running", "run", "English")
        
        # Get the cached lemma
        lemma = db_service.get_cached_lemma("running", "English")
        
        # Check that the lemma was retrieved
        assert lemma == "run"
        
        # Try to get a non-existent lemma
        lemma = db_service.get_cached_lemma("nonexistent", "English")
        assert lemma is None
        
        # Cache multiple lemmas for the same word in different languages
        db_service.cache_lemma("running", "běh", "Czech")
        db_service.cache_lemma("running", "correr", "Spanish")
        
        # Check that the correct lemma is retrieved for each language
        assert db_service.get_cached_lemma("running", "English") == "run"
        assert db_service.get_cached_lemma("running", "Czech") == "běh"
        assert db_service.get_cached_lemma("running", "Spanish") == "correr"
    
    def test_concurrent_access(self, db_service):
        """Test concurrent access to the database."""
        # Number of concurrent operations
        num_operations = 10
        
        # Shared counter for successful operations
        success_count = 0
        
        # Lock for synchronizing access to the counter
        lock = threading.Lock()
        
        # Function to perform a database operation
        def db_operation(index):
            nonlocal success_count
            try:
                # Add an entry
                entry = {
                    "headword": f"test{index}",
                    "metadata": {
                        "source_language": "English",
                        "target_language": "Czech",
                        "definition_language": "English"
                    }
                }
                
                entry_id = db_service.add_entry(entry)
                
                # Search for entries
                results = db_service.search_entries(search_term=f"test{index}")
                
                # Verify the operation was successful
                if entry_id and len(results) == 1:
                    with lock:
                        success_count += 1
            except Exception as e:
                print(f"Error in thread {index}: {str(e)}")
        
        # Create and start threads
        threads = []
        for i in range(num_operations):
            thread = threading.Thread(target=db_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all operations were successful
        assert success_count == num_operations
        
        # Verify that all entries were added
        for i in range(num_operations):
            entry = db_service.get_entry_by_headword(
                headword=f"test{i}",
                source_lang="English",
                target_lang="Czech",
                definition_lang="English"
            )
            assert entry is not None
            assert entry["headword"] == f"test{i}"
    
    def test_async_operations(self, db_service, event_bus):
        """Test asynchronous database operations."""
        # Create a mock async service
        class MockAsyncService:
            def __init__(self):
                self.submit_task_called = False
                self.task_id = None
                self.on_complete = None
                self.on_error = None
            
            def submit_task(self, task_func, on_complete=None, on_error=None, **kwargs):
                self.submit_task_called = True
                self.on_complete = on_complete
                self.on_error = on_error
                self.task_id = "test_task_id"
                
                # Simulate async execution by running the task function
                try:
                    result = task_func()
                    if on_complete:
                        on_complete(result)
                except Exception as e:
                    if on_error:
                        on_error(e)
                
                return self.task_id
        
        mock_async_service = MockAsyncService()
        
        # Test asynchronous search
        search_result = None
        error_called = False
        
        def on_search_complete(result):
            nonlocal search_result
            search_result = result
        
        def on_search_error(error):
            nonlocal error_called
            error_called = True
        
        # Add a test entry
        entry = {
            "headword": "async_test",
            "metadata": {
                "source_language": "English",
                "target_language": "Czech",
                "definition_language": "English"
            }
        }
        
        db_service.add_entry(entry)
        
        # Call async search
        task_id = db_service.search_entries_async(
            async_service=mock_async_service,
            search_term="async_test",
            callback=on_search_complete,
            error_callback=on_search_error
        )
        
        # Check that async service was called
        assert mock_async_service.submit_task_called is True
        assert task_id == "test_task_id"
        
        # Check that search was successful
        assert search_result is not None
        assert len(search_result) == 1
        assert search_result[0]["headword"] == "async_test"
        assert error_called is False