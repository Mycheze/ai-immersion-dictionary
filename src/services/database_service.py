"""
Database Service

This module provides a service for database operations, following the MVC pattern
by abstracting database operations from the models. It handles connection pooling,
transaction management, and all CRUD operations for the dictionary data.
"""

import sqlite3
import json
import os
import threading
import queue
from pathlib import Path
from contextlib import contextmanager
from typing import List, Dict, Optional, Any, Union, Tuple, Callable

from .base_service import BaseService

class DatabaseService(BaseService):
    """
    Service for database operations.
    
    This class provides a clean interface for database operations, with proper
    connection pooling, prepared statements, and transaction management.
    
    Attributes:
        db_path: Path to the SQLite database file
        connection_pool: Pool of database connections
        pool_size: Maximum number of connections in the pool
        event_bus: Event system for service-related notifications
    """
    
    def __init__(self, db_path: Union[str, Path] = None, pool_size: int = 5, event_bus=None):
        """
        Initialize the database service.
        
        Args:
            db_path: Path to the SQLite database file. If None, uses default location.
            pool_size: Maximum number of connections in the pool
            event_bus: Optional event bus for notifications
        """
        self.pool_size = pool_size
        
        # If no db_path is provided, use default data directory in app root
        if db_path is None:
            # Get the application root directory
            app_root = Path(__file__).parent.parent.parent.absolute()
            self.db_path = app_root / "data" / "dictionary.db"
        else:
            # Convert string path to Path object if needed
            self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        
        # Call parent initializer
        super().__init__(event_bus)
    
    def _initialize(self):
        """Initialize the database service."""
        # Ensure data directory exists
        data_dir = self.db_path.parent
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            self.publish_event('database:directory_created', {'path': str(data_dir)})
        
        # Initialize connection pool
        self.connection_pool = queue.Queue(maxsize=self.pool_size)
        self._fill_connection_pool()
        
        # Initialize database schema
        self._init_database()
        
        # Prepare common SQL statements
        self._prepare_statements()
    
    def _fill_connection_pool(self):
        """Fill the connection pool with new connections."""
        for _ in range(self.pool_size):
            conn = self._create_connection()
            self.connection_pool.put(conn)
    
    def _create_connection(self):
        """Create a new database connection."""
        # Convert Path to string for sqlite3.connect
        db_path_str = str(self.db_path)
        conn = sqlite3.connect(db_path_str)
        
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Return dictionary results
        conn.row_factory = sqlite3.Row
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Yields:
            SQLite connection from the pool
        """
        conn = None
        try:
            # Get connection from pool, or create a new one if pool is empty
            try:
                conn = self.connection_pool.get(block=False)
            except queue.Empty:
                conn = self._create_connection()
                self.publish_event('database:connection_created', {
                    'pool_empty': True,
                    'reason': 'Connection pool empty'
                })
            
            yield conn
        finally:
            # Return connection to pool if valid
            if conn:
                try:
                    # Test if connection is still valid
                    conn.execute("SELECT 1")
                    self.connection_pool.put(conn)
                except sqlite3.Error:
                    # If connection is not valid, create a new one for the pool
                    try:
                        conn.close()
                    except:
                        pass
                    
                    # Add a new connection to the pool
                    new_conn = self._create_connection()
                    self.connection_pool.put(new_conn)
                    
                    self.publish_event('database:connection_replaced', {
                        'reason': 'Invalid connection'
                    })
    
    def _prepare_statements(self):
        """Prepare common SQL statements for reuse."""
        # These statements will be used with parameter binding for efficiency
        self.statements = {
            # Entries
            'get_entry_by_id': """
                SELECT * FROM entries WHERE id = ?
            """,
            'get_entry_by_headword': """
                SELECT * FROM entries 
                WHERE headword = ?
                AND (source_language = ? OR ? IS NULL)
                AND (target_language = ? OR ? IS NULL)
                AND (definition_language = ? OR ? IS NULL)
            """,
            'insert_entry': """
                INSERT INTO entries 
                (headword, part_of_speech, source_language, target_language, definition_language, has_context)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
            'delete_entry': """
                DELETE FROM entries 
                WHERE headword = ?
                AND (source_language = ? OR ? IS NULL)
                AND (target_language = ? OR ? IS NULL)
                AND (definition_language = ? OR ? IS NULL)
            """,
            
            # Meanings
            'insert_meaning': """
                INSERT INTO meanings 
                (entry_id, definition, noun_type, verb_type, comparison)
                VALUES (?, ?, ?, ?, ?)
            """,
            'get_meanings_by_entry_id': """
                SELECT * FROM meanings WHERE entry_id = ?
            """,
            
            # Examples
            'insert_example': """
                INSERT INTO examples 
                (meaning_id, sentence, translation, is_context_sentence)
                VALUES (?, ?, ?, ?)
            """,
            'get_examples_by_meaning_id': """
                SELECT * FROM examples WHERE meaning_id = ?
            """,
            
            # Lemma cache
            'get_cached_lemma': """
                SELECT lemma FROM lemma_cache 
                WHERE word = ? AND target_language = ?
            """,
            'insert_lemma_cache': """
                INSERT OR REPLACE INTO lemma_cache 
                (word, lemma, target_language)
                VALUES (?, ?, ?)
            """,
            
            # Sentence context
            'save_sentence_context': """
                INSERT INTO sentence_contexts 
                (entry_id, sentence, selected_text)
                VALUES (?, ?, ?)
            """,
            'get_sentence_context': """
                SELECT * FROM sentence_contexts 
                WHERE entry_id = ? 
                ORDER BY created_at DESC LIMIT 1
            """
        }
    
    def _init_database(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if the entries table needs to be updated
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
            if cursor.fetchone():
                # Check if the table has the correct UNIQUE constraint
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='entries'")
                create_sql = cursor.fetchone()['sql']
                
                if "UNIQUE(headword, source_language, target_language, definition_language)" not in create_sql:
                    # Drop and recreate the entries table with the correct constraint
                    self.publish_event('database:schema_update_needed', {
                        'reason': 'Missing UNIQUE constraint'
                    })
                    
                    # Backup existing data
                    cursor.execute("SELECT * FROM entries")
                    backup_entries = [dict(row) for row in cursor.fetchall()]
                    
                    # Drop foreign key tables first
                    cursor.execute("DROP TABLE IF EXISTS examples")
                    cursor.execute("DROP TABLE IF EXISTS meanings")
                    cursor.execute("DROP TABLE IF EXISTS entries")
                    cursor.execute("DROP TABLE IF EXISTS lemma_cache")
                    cursor.execute("DROP TABLE IF EXISTS sentence_contexts")
            
            # Create entries table with correct constraint
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    headword TEXT NOT NULL,
                    part_of_speech TEXT,
                    source_language TEXT,
                    target_language TEXT,
                    definition_language TEXT,
                    has_context BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(headword, source_language, target_language, definition_language)
                )
            """)
            
            # Create meanings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meanings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER,
                    definition TEXT,
                    noun_type TEXT,
                    verb_type TEXT,
                    comparison TEXT,
                    FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
                )
            """)
            
            # Create examples table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS examples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meaning_id INTEGER,
                    sentence TEXT,
                    translation TEXT,
                    is_context_sentence BOOLEAN DEFAULT 0,
                    FOREIGN KEY(meaning_id) REFERENCES meanings(id) ON DELETE CASCADE
                )
            """)
            
            # Create lemma cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lemma_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    lemma TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(word, target_language)
                )
            """)
            
            # Create sentence context table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sentence_contexts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER,
                    sentence TEXT NOT NULL,
                    selected_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for faster searching
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_headword ON entries(headword)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_language ON entries(source_language)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_target_language ON entries(target_language)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_definition_language ON entries(definition_language)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lemma_word ON lemma_cache(word, target_language)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entry_sentence ON sentence_contexts(entry_id)")
            
            # If we had backup data, restore it
            if 'backup_entries' in locals():
                self.publish_event('database:restoring_data', {
                    'count': len(backup_entries)
                })
                
                for entry in backup_entries:
                    # Re-insert only with proper UNIQUE constraint
                    cursor.execute("""
                        INSERT OR IGNORE INTO entries 
                        (id, headword, part_of_speech, source_language, target_language, definition_language, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry['id'],
                        entry['headword'],
                        entry['part_of_speech'],
                        entry['source_language'],
                        entry['target_language'],
                        entry['definition_language'],
                        entry['created_at']
                    ))
            
            # Commit the changes
            conn.commit()
            
            self.publish_event('database:initialized', {
                'path': str(self.db_path)
            })
    
    def add_entry(self, entry: Dict[str, Any], progress_callback: Callable = None) -> Optional[int]:
        """
        Add a dictionary entry to the database.
        
        Args:
            entry: Dictionary entry to add
            progress_callback: Optional callback for reporting progress
            
        Returns:
            ID of the new entry, or None if insertion failed
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Start a transaction
                cursor.execute("BEGIN TRANSACTION")
                
                try:
                    # Extract entry data
                    headword = entry.get('headword', '')
                    metadata = entry.get('metadata', {})
                    part_of_speech = entry.get('part_of_speech', '')
                    
                    # Get language data
                    source_language = metadata.get('source_language', '')
                    target_language = metadata.get('target_language', '')
                    definition_language = metadata.get('definition_language', '')
                    
                    # Check if entry has context sentence
                    has_context = 0
                    if 'context_sentence' in metadata and metadata['context_sentence']:
                        has_context = 1
                    
                    # Insert entry
                    cursor.execute(self.statements['insert_entry'], (
                        headword,
                        part_of_speech,
                        source_language,
                        target_language,
                        definition_language,
                        has_context
                    ))
                    
                    # Get the ID of the new entry
                    entry_id = cursor.lastrowid
                    
                    # Add meanings
                    meanings = entry.get('meanings', [])
                    for meaning in meanings:
                        # Get meaning data
                        definition = meaning.get('definition', '')
                        noun_type = meaning.get('noun_type', '')
                        verb_type = meaning.get('verb_type', '')
                        comparison = meaning.get('comparison', '')
                        
                        # Insert meaning
                        cursor.execute(self.statements['insert_meaning'], (
                            entry_id,
                            definition,
                            noun_type,
                            verb_type,
                            comparison
                        ))
                        
                        # Get the ID of the new meaning
                        meaning_id = cursor.lastrowid
                        
                        # Add examples
                        examples = meaning.get('examples', [])
                        for example in examples:
                            # Get example data
                            sentence = example.get('sentence', '')
                            translation = example.get('translation', '')
                            is_context = example.get('is_context', 0)
                            
                            # Insert example
                            cursor.execute(self.statements['insert_example'], (
                                meaning_id,
                                sentence,
                                translation,
                                is_context
                            ))
                    
                    # Add context sentence if present
                    if has_context:
                        context_sentence = metadata.get('context_sentence', '')
                        selected_text = metadata.get('selected_text', headword)
                        
                        if context_sentence and selected_text:
                            cursor.execute(self.statements['save_sentence_context'], (
                                entry_id,
                                context_sentence,
                                selected_text
                            ))
                    
                    # Commit the transaction
                    conn.commit()
                    
                    self.publish_event('database:entry_added', {
                        'entry_id': entry_id,
                        'headword': headword
                    })
                    
                    return entry_id
                    
                except Exception as e:
                    # Roll back the transaction on error
                    conn.rollback()
                    
                    self.publish_event('database:error', {
                        'operation': 'add_entry',
                        'error': str(e),
                        'headword': entry.get('headword', '')
                    })
                    
                    return None
        
        except Exception as e:
            self.publish_event('database:connection_error', {
                'operation': 'add_entry',
                'error': str(e)
            })
            
            return None
    
    def get_entry_by_headword(
        self, 
        headword: str, 
        source_lang: str = None, 
        target_lang: str = None, 
        definition_lang: str = None,
        progress_callback: Callable = None
    ) -> Optional[Dict]:
        """
        Retrieve a dictionary entry by headword.
        
        Args:
            headword: The headword to retrieve
            source_lang: Optional source language filter
            target_lang: Optional target language filter
            definition_lang: Optional definition language filter
            
        Returns:
            Dictionary entry or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Execute the query with parameters
                cursor.execute(self.statements['get_entry_by_headword'], (
                    headword,
                    source_lang, source_lang,
                    target_lang, target_lang,
                    definition_lang, definition_lang
                ))
                
                # Fetch the entry
                entry_row = cursor.fetchone()
                
                if not entry_row:
                    return None
                
                # Convert entry row to dictionary
                entry_id = entry_row['id']
                
                # Construct full entry with meanings and examples
                return self._construct_entry_dict(entry_id, cursor)
                
        except Exception as e:
            self.publish_event('database:error', {
                'operation': 'get_entry_by_headword',
                'error': str(e),
                'headword': headword
            })
            
            return None
    
    def search_entries(
        self, 
        search_term: str = None, 
        source_lang: str = None, 
        target_lang: str = None, 
        definition_lang: str = None,
        limit: int = 50,
        offset: int = 0,
        progress_callback: Callable = None
    ) -> List[Dict]:
        """
        Search for dictionary entries.
        
        Args:
            search_term: Optional search term (substring of headword)
            source_lang: Optional source language filter
            target_lang: Optional target language filter
            definition_lang: Optional definition language filter
            limit: Maximum number of results to return
            offset: Number of results to skip
            progress_callback: Optional callback for reporting progress
            
        Returns:
            List of matching entries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build the query dynamically
                query = "SELECT * FROM entries WHERE 1=1"
                params = []
                
                # Add filters if provided
                if search_term:
                    query += " AND headword LIKE ?"
                    params.append(f"%{search_term}%")
                
                if source_lang:
                    query += " AND source_language = ?"
                    params.append(source_lang)
                
                if target_lang:
                    query += " AND target_language = ?"
                    params.append(target_lang)
                
                if definition_lang:
                    query += " AND definition_language = ?"
                    params.append(definition_lang)
                
                # First count total results to calculate progress
                count_query = f"SELECT COUNT(*) as count FROM ({query})"
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()['count']
                
                # Report initial progress
                if progress_callback:
                    progress_callback(0)
                
                # Add sorting and pagination
                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.append(limit)
                params.append(offset)
                
                # Execute the query
                cursor.execute(query, params)
                
                # Construct entries
                entries = []
                processed_count = 0
                
                # Fetch all matching entry rows first
                entry_rows = cursor.fetchall()
                
                for entry_row in entry_rows:
                    entry_id = entry_row['id']
                    entry = self._construct_entry_dict(entry_id, cursor)
                    entries.append(entry)
                    
                    # Update progress after processing each entry
                    processed_count += 1
                    if progress_callback and total_count > 0:
                        progress = min(95, (processed_count / len(entry_rows)) * 100)
                        progress_callback(progress)
                
                # Final progress update
                if progress_callback:
                    progress_callback(100)
                
                # Publish event with search results
                self.publish_event('database:search_completed', {
                    'search_term': search_term,
                    'count': len(entries)
                })
                
                return entries
                
        except Exception as e:
            self.publish_event('database:error', {
                'operation': 'search_entries',
                'error': str(e),
                'search_term': search_term
            })
            
            return []
            
    def search_entries_async(
        self,
        async_service,
        search_term: str = None, 
        source_lang: str = None, 
        target_lang: str = None, 
        definition_lang: str = None,
        limit: int = 50,
        offset: int = 0,
        callback: Callable = None,
        error_callback: Callable = None
    ) -> str:
        """
        Search for dictionary entries asynchronously.
        
        Args:
            async_service: The async service to use
            search_term: Optional search term (substring of headword)
            source_lang: Optional source language filter
            target_lang: Optional target language filter
            definition_lang: Optional definition language filter
            limit: Maximum number of results to return
            offset: Number of results to skip
            callback: Function to call with result on success
            error_callback: Function to call with error on failure
            
        Returns:
            Task ID for the async operation
        """
        search_desc = f"'{search_term}'" if search_term else "all entries"
        if target_lang:
            search_desc += f" in {target_lang}"
            
        return async_service.submit_task(
            self.search_entries,
            search_term,
            source_lang,
            target_lang,
            definition_lang,
            limit,
            offset,
            name=f"Search Entries: {search_desc}",
            description=f"Searching for {search_desc} in the dictionary",
            callback=callback,
            error_callback=error_callback
        )
    
    def get_all_languages(self) -> Dict[str, List[str]]:
        """
        Get all languages used in the dictionary.
        
        Returns:
            Dictionary with source_languages, target_languages, and definition_languages
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                result = {
                    'source_languages': [],
                    'target_languages': [],
                    'definition_languages': []
                }
                
                # Get unique source languages
                cursor.execute("SELECT DISTINCT source_language FROM entries WHERE source_language IS NOT NULL")
                result['source_languages'] = [row['source_language'] for row in cursor.fetchall()]
                
                # Get unique target languages
                cursor.execute("SELECT DISTINCT target_language FROM entries WHERE target_language IS NOT NULL")
                result['target_languages'] = [row['target_language'] for row in cursor.fetchall()]
                
                # Get unique definition languages
                cursor.execute("SELECT DISTINCT definition_language FROM entries WHERE definition_language IS NOT NULL")
                result['definition_languages'] = [row['definition_language'] for row in cursor.fetchall()]
                
                return result
                
        except Exception as e:
            self.publish_event('database:error', {
                'operation': 'get_all_languages',
                'error': str(e)
            })
            
            return {
                'source_languages': [],
                'target_languages': [],
                'definition_languages': []
            }
    
    def get_all_languages_async(self, async_service, callback: Callable = None, error_callback: Callable = None) -> str:
        """
        Get all languages used in the dictionary asynchronously.
        
        Args:
            async_service: The async service to use
            callback: Function to call with result on success
            error_callback: Function to call with error on failure
            
        Returns:
            Task ID for the async operation
        """
        return async_service.submit_task(
            self.get_all_languages,
            name="Get All Languages",
            description="Retrieving all languages from the database",
            callback=callback,
            error_callback=error_callback
        )
        
    def add_entry_async(
        self, 
        async_service, 
        entry: Dict[str, Any], 
        callback: Callable = None, 
        error_callback: Callable = None
    ) -> str:
        """
        Add a dictionary entry to the database asynchronously.
        
        Args:
            async_service: The async service to use
            entry: Dictionary entry to add
            callback: Function to call with result on success
            error_callback: Function to call with error on failure
            
        Returns:
            Task ID for the async operation
        """
        headword = entry.get('headword', 'unknown')
        metadata = entry.get('metadata', {})
        language = metadata.get('target_language', 'unknown')
        
        return async_service.submit_task(
            self.add_entry,
            entry,
            name=f"Add Entry: {headword}",
            description=f"Adding {headword} ({language}) to dictionary",
            callback=callback,
            error_callback=error_callback
        )
    
    def get_entry_by_headword_async(
        self,
        async_service,
        headword: str,
        source_lang: str = None,
        target_lang: str = None,
        definition_lang: str = None,
        callback: Callable = None,
        error_callback: Callable = None
    ) -> str:
        """
        Retrieve a dictionary entry by headword asynchronously.
        
        Args:
            async_service: The async service to use
            headword: The headword to retrieve
            source_lang: Optional source language filter
            target_lang: Optional target language filter
            definition_lang: Optional definition language filter
            callback: Function to call with result on success
            error_callback: Function to call with error on failure
            
        Returns:
            Task ID for the async operation
        """
        lang_desc = ""
        if target_lang:
            lang_desc = f" in {target_lang}"
            
        return async_service.submit_task(
            self.get_entry_by_headword,
            headword,
            source_lang,
            target_lang,
            definition_lang,
            name=f"Get Entry: {headword}",
            description=f"Retrieving entry for {headword}{lang_desc}",
            callback=callback,
            error_callback=error_callback
        )
    
    def delete_entry_async(
        self,
        async_service,
        headword: str,
        source_lang: str = None,
        target_lang: str = None,
        definition_lang: str = None,
        callback: Callable = None,
        error_callback: Callable = None
    ) -> str:
        """
        Delete a dictionary entry asynchronously.
        
        Args:
            async_service: The async service to use
            headword: Headword of the entry to delete
            source_lang: Optional source language filter
            target_lang: Optional target language filter
            definition_lang: Optional definition language filter
            callback: Function to call with result on success
            error_callback: Function to call with error on failure
            
        Returns:
            Task ID for the async operation
        """
        lang_desc = ""
        if target_lang:
            lang_desc = f" in {target_lang}"
            
        return async_service.submit_task(
            self.delete_entry,
            headword,
            source_lang,
            target_lang,
            definition_lang,
            name=f"Delete Entry: {headword}",
            description=f"Deleting entry for {headword}{lang_desc}",
            callback=callback,
            error_callback=error_callback
        )
    
    def get_cached_lemma_async(
        self,
        async_service,
        word: str,
        target_language: str,
        callback: Callable = None,
        error_callback: Callable = None
    ) -> str:
        """
        Get a cached lemma asynchronously.
        
        Args:
            async_service: The async service to use
            word: Word to get lemma for
            target_language: Target language
            callback: Function to call with result on success
            error_callback: Function to call with error on failure
            
        Returns:
            Task ID for the async operation
        """
        return async_service.submit_task(
            self.get_cached_lemma,
            word,
            target_language,
            name=f"Get Lemma: {word}",
            description=f"Retrieving lemma for {word} in {target_language}",
            callback=callback,
            error_callback=error_callback
        )
    
    def cache_lemma_async(
        self,
        async_service,
        word: str,
        lemma: str,
        target_language: str,
        callback: Callable = None,
        error_callback: Callable = None
    ) -> str:
        """
        Cache a lemma asynchronously.
        
        Args:
            async_service: The async service to use
            word: Word to cache lemma for
            lemma: Lemma to cache
            target_language: Target language
            callback: Function to call with result on success
            error_callback: Function to call with error on failure
            
        Returns:
            Task ID for the async operation
        """
        return async_service.submit_task(
            self.cache_lemma,
            word,
            lemma,
            target_language,
            name=f"Cache Lemma: {word}",
            description=f"Caching lemma {lemma} for {word} in {target_language}",
            callback=callback,
            error_callback=error_callback
        )
    
    def clear_lemma_cache_async(
        self,
        async_service,
        callback: Callable = None,
        error_callback: Callable = None
    ) -> str:
        """
        Clear the lemma cache asynchronously.
        
        Args:
            async_service: The async service to use
            callback: Function to call with result on success
            error_callback: Function to call with error on failure
            
        Returns:
            Task ID for the async operation
        """
        return async_service.submit_task(
            self.clear_lemma_cache,
            name="Clear Lemma Cache",
            description="Clearing lemma cache",
            callback=callback,
            error_callback=error_callback
        )
    
    def save_sentence_context_async(
        self,
        async_service,
        entry_id: int,
        sentence: str,
        selected_text: str,
        callback: Callable = None,
        error_callback: Callable = None
    ) -> str:
        """
        Save a sentence context for an entry asynchronously.
        
        Args:
            async_service: The async service to use
            entry_id: ID of the entry
            sentence: Context sentence
            selected_text: Selected text in the sentence
            callback: Function to call with result on success
            error_callback: Function to call with error on failure
            
        Returns:
            Task ID for the async operation
        """
        return async_service.submit_task(
            self.save_sentence_context,
            entry_id,
            sentence,
            selected_text,
            name=f"Save Context: {selected_text}",
            description=f"Saving context for entry {entry_id}",
            callback=callback,
            error_callback=error_callback
        )
    
    def get_sentence_context_async(
        self,
        async_service,
        entry_id: int,
        callback: Callable = None,
        error_callback: Callable = None
    ) -> str:
        """
        Get the sentence context for an entry asynchronously.
        
        Args:
            async_service: The async service to use
            entry_id: ID of the entry
            callback: Function to call with result on success
            error_callback: Function to call with error on failure
            
        Returns:
            Task ID for the async operation
        """
        return async_service.submit_task(
            self.get_sentence_context,
            entry_id,
            name=f"Get Context: Entry {entry_id}",
            description=f"Retrieving context for entry {entry_id}",
            callback=callback,
            error_callback=error_callback
        )
    
    def _construct_entry_dict(self, entry_id: int, cursor) -> Dict:
        """
        Construct a complete entry dictionary from database records.
        
        Args:
            entry_id: ID of the entry
            cursor: Database cursor
            
        Returns:
            Complete entry dictionary
        """
        # Get entry data
        cursor.execute(self.statements['get_entry_by_id'], (entry_id,))
        entry_row = cursor.fetchone()
        
        # Create entry dictionary
        entry = {
            'id': entry_row['id'],
            'headword': entry_row['headword'],
            'part_of_speech': entry_row['part_of_speech'],
            'metadata': {
                'source_language': entry_row['source_language'],
                'target_language': entry_row['target_language'],
                'definition_language': entry_row['definition_language'],
                'created_at': entry_row['created_at']
            },
            'meanings': []
        }
        
        # Get meanings
        cursor.execute(self.statements['get_meanings_by_entry_id'], (entry_id,))
        meaning_rows = cursor.fetchall()
        
        for meaning_row in meaning_rows:
            meaning_id = meaning_row['id']
            
            # Create meaning dictionary
            meaning = {
                'definition': meaning_row['definition'],
                'examples': []
            }
            
            # Add additional properties if present
            if meaning_row['noun_type']:
                meaning['noun_type'] = meaning_row['noun_type']
                
            if meaning_row['verb_type']:
                meaning['verb_type'] = meaning_row['verb_type']
                
            if meaning_row['comparison']:
                meaning['comparison'] = meaning_row['comparison']
            
            # Get examples
            cursor.execute(self.statements['get_examples_by_meaning_id'], (meaning_id,))
            example_rows = cursor.fetchall()
            
            for example_row in example_rows:
                # Create example dictionary
                example = {
                    'sentence': example_row['sentence'],
                    'translation': example_row['translation']
                }
                
                if example_row['is_context_sentence']:
                    example['is_context'] = True
                
                meaning['examples'].append(example)
            
            entry['meanings'].append(meaning)
        
        # Get sentence context if present
        if entry_row['has_context']:
            context = self.get_sentence_context(entry_id)
            if context:
                entry['metadata']['context_sentence'] = context['sentence']
                entry['metadata']['selected_text'] = context['selected_text']
        
        return entry
    
    def get_cached_lemma(self, word: str, target_language: str, progress_callback: Callable = None) -> Optional[str]:
        """
        Get a cached lemma.
        
        Args:
            word: Word to get lemma for
            target_language: Target language
            progress_callback: Optional callback for reporting progress
            
        Returns:
            Cached lemma or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(self.statements['get_cached_lemma'], (
                    word.lower(), target_language
                ))
                
                result = cursor.fetchone()
                return result['lemma'] if result else None
                
        except Exception as e:
            self.publish_event('database:error', {
                'operation': 'get_cached_lemma',
                'error': str(e),
                'word': word
            })
            
            return None
    
    def cache_lemma(self, word: str, lemma: str, target_language: str, progress_callback: Callable = None):
        """
        Cache a lemma.
        
        Args:
            word: Word to cache lemma for
            lemma: Lemma to cache
            target_language: Target language
            progress_callback: Optional callback for reporting progress
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(self.statements['insert_lemma_cache'], (
                    word.lower(), lemma, target_language
                ))
                
                conn.commit()
                
        except Exception as e:
            self.publish_event('database:error', {
                'operation': 'cache_lemma',
                'error': str(e),
                'word': word
            })
    
    def clear_lemma_cache(self, progress_callback: Callable = None):
        """Clear the lemma cache.
        
        Args:
            progress_callback: Optional callback for reporting progress
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM lemma_cache")
                conn.commit()
                
                self.publish_event('database:cache_cleared', {
                    'cache_type': 'lemma'
                })
                
        except Exception as e:
            self.publish_event('database:error', {
                'operation': 'clear_lemma_cache',
                'error': str(e)
            })
    
    def save_sentence_context(self, entry_id: int, sentence: str, selected_text: str, progress_callback: Callable = None) -> bool:
        """
        Save a sentence context for an entry.
        
        Args:
            entry_id: ID of the entry
            sentence: Context sentence
            selected_text: Selected text in the sentence
            progress_callback: Optional callback for reporting progress
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(self.statements['save_sentence_context'], (
                    entry_id, sentence, selected_text
                ))
                
                # Update the has_context flag in the entry
                cursor.execute("""
                    UPDATE entries SET has_context = 1 WHERE id = ?
                """, (entry_id,))
                
                conn.commit()
                
                return True
                
        except Exception as e:
            self.publish_event('database:error', {
                'operation': 'save_sentence_context',
                'error': str(e),
                'entry_id': entry_id
            })
            
            return False
    
    def get_sentence_context(self, entry_id: int, progress_callback: Callable = None) -> Optional[Dict]:
        """
        Get the sentence context for an entry.
        
        Args:
            entry_id: ID of the entry
            progress_callback: Optional callback for reporting progress
            
        Returns:
            Sentence context dictionary or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(self.statements['get_sentence_context'], (entry_id,))
                
                result = cursor.fetchone()
                
                if result:
                    return {
                        'id': result['id'],
                        'entry_id': result['entry_id'],
                        'sentence': result['sentence'],
                        'selected_text': result['selected_text'],
                        'created_at': result['created_at']
                    }
                    
                return None
                
        except Exception as e:
            self.publish_event('database:error', {
                'operation': 'get_sentence_context',
                'error': str(e),
                'entry_id': entry_id
            })
            
            return None
    
    def delete_entry(
        self, 
        headword: str, 
        source_lang: str = None, 
        target_lang: str = None, 
        definition_lang: str = None,
        progress_callback: Callable = None
    ) -> bool:
        """
        Delete a dictionary entry.
        
        Args:
            headword: Headword of the entry to delete
            source_lang: Optional source language filter
            target_lang: Optional target language filter
            definition_lang: Optional definition language filter
            
        Returns:
            True if entry was deleted, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get the entry ID first (for notification)
                cursor.execute(self.statements['get_entry_by_headword'], (
                    headword,
                    source_lang, source_lang,
                    target_lang, target_lang,
                    definition_lang, definition_lang
                ))
                
                entry_row = cursor.fetchone()
                if not entry_row:
                    return False
                
                entry_id = entry_row['id']
                
                # Delete the entry
                cursor.execute(self.statements['delete_entry'], (
                    headword,
                    source_lang, source_lang,
                    target_lang, target_lang,
                    definition_lang, definition_lang
                ))
                
                # Check if any rows were affected
                affected_rows = cursor.rowcount
                
                if affected_rows > 0:
                    conn.commit()
                    
                    self.publish_event('database:entry_deleted', {
                        'entry_id': entry_id,
                        'headword': headword
                    })
                    
                    return True
                    
                return False
                
        except Exception as e:
            self.publish_event('database:error', {
                'operation': 'delete_entry',
                'error': str(e),
                'headword': headword
            })
            
            return False
    
    def shutdown(self):
        """Clean up resources and shut down the service."""
        # Close all connections in the pool
        while not self.connection_pool.empty():
            try:
                conn = self.connection_pool.get(block=False)
                conn.close()
            except:
                pass
        
        self.publish_event('database:shutdown', {})