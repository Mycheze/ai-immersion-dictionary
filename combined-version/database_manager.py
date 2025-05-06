import sqlite3
import json
import os
from contextlib import contextmanager
from typing import List, Dict, Optional, Any

class DatabaseManager:
    """
    Manages SQLite database operations for the dictionary application
    """
    
    def __init__(self, db_path: str = "data/dictionary.db"):
        """Initialize database connection and create tables if needed"""
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if the entries table needs to be updated
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
            if cursor.fetchone():
                # Check if the table has the correct UNIQUE constraint
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='entries'")
                create_sql = cursor.fetchone()[0]
                
                if "UNIQUE(headword, source_language, target_language, definition_language)" not in create_sql:
                    # Drop and recreate the entries table with the correct constraint
                    print("Database schema needs updating...")
                    
                    # Backup existing data
                    cursor.execute("SELECT * FROM entries")
                    backup_entries = cursor.fetchall()
                    
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
                print(f"Restoring {len(backup_entries)} entries...")
                for entry in backup_entries:
                    # Re-insert only with proper UNIQUE constraint
                    cursor.execute("""
                        INSERT OR IGNORE INTO entries 
                        (id, headword, part_of_speech, source_language, target_language, definition_language, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, entry)
                print("Database migration complete!")
            
            conn.commit()
        
    def add_entry(self, entry: Dict[str, Any]) -> Optional[int]:
        """Add a new dictionary entry to the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Start a transaction
                cursor.execute("BEGIN TRANSACTION")
                
                try:
                    # Ensure metadata exists
                    if "metadata" not in entry:
                        print("Error: entry missing metadata")
                        return None
                    
                    metadata = entry["metadata"]
                    
                    # Ensure required metadata fields exist
                    required_fields = ["source_language", "target_language", "definition_language"]
                    for field in required_fields:
                        if field not in metadata:
                            print(f"Error: metadata missing {field}")
                            return None
                    
                    # First check if this exact entry already exists
                    cursor.execute("""
                        SELECT id FROM entries 
                        WHERE headword = ? AND source_language = ? AND target_language = ? AND definition_language = ?
                    """, (
                        entry.get("headword", ""),
                        metadata["source_language"],
                        metadata["target_language"],
                        metadata["definition_language"]
                    ))
                    
                    existing_result = cursor.fetchone()
                    if existing_result:
                        # Entry already exists with this exact combination
                        print(f"Entry already exists with ID: {existing_result[0]}")
                        cursor.execute("ROLLBACK")
                        return existing_result[0]
                    
                    # Check if the entry has context
                    has_context = False
                    context_sentence = None
                    if metadata.get("has_context") and metadata.get("context_sentence"):
                        has_context = True
                        context_sentence = metadata.get("context_sentence")
                    
                    # Insert new entry
                    cursor.execute("""
                        INSERT INTO entries 
                        (headword, part_of_speech, source_language, target_language, definition_language, has_context)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        entry.get("headword", ""),  # Ensure headword exists
                        json.dumps(entry.get("part_of_speech")) if isinstance(entry.get("part_of_speech"), list) else entry.get("part_of_speech"),
                        metadata["source_language"],
                        metadata["target_language"],
                        metadata["definition_language"],
                        1 if has_context else 0
                    ))
                    
                    entry_id = cursor.lastrowid
                    
                    # Insert meanings
                    meanings = entry.get("meanings", [])
                    if not meanings:
                        print("Warning: entry has no meanings")
                    
                    for meaning in meanings:
                        # Ensure meaning has required fields
                        if "definition" not in meaning:
                            print("Warning: meaning missing definition, skipping")
                            continue
                            
                        grammar = meaning.get("grammar", {})
                        
                        cursor.execute("""
                            INSERT INTO meanings 
                            (entry_id, definition, noun_type, verb_type, comparison)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            entry_id,
                            meaning["definition"],
                            grammar.get("noun_type"),
                            grammar.get("verb_type"),
                            grammar.get("comparison")
                        ))
                        
                        meaning_id = cursor.lastrowid
                        
                        # Insert examples
                        examples = meaning.get("examples", [])
                        for example in examples:
                            if "sentence" not in example:
                                print("Warning: example missing sentence, skipping")
                                continue
                                
                            is_context = False
                            if example.get("is_context_sentence") is True:
                                is_context = True
                                
                            cursor.execute("""
                                INSERT INTO examples 
                                (meaning_id, sentence, translation, is_context_sentence)
                                VALUES (?, ?, ?, ?)
                            """, (
                                meaning_id,
                                example["sentence"],
                                example.get("translation"),
                                1 if is_context else 0
                            ))
                    
                    # Commit the transaction
                    cursor.execute("COMMIT")
                    return entry_id
                    
                except sqlite3.Error as e:
                    # Rollback on any error
                    cursor.execute("ROLLBACK")
                    print(f"Database error during transaction: {e}")
                    print(f"Entry data: {entry}")
                    return None
                    
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
    
    def get_entry_by_headword(self, headword: str, source_lang: str = None, target_lang: str = None, definition_lang: str = None) -> Optional[Dict]:
        """Retrieve an entry by headword"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM entries WHERE headword = ?"
            params = [headword]
            
            if source_lang:
                query += " AND source_language = ?"
                params.append(source_lang)
            
            if target_lang:
                query += " AND target_language = ?"
                params.append(target_lang)
            
            if definition_lang:
                query += " AND definition_language = ?"
                params.append(definition_lang)
            
            query += " LIMIT 1"
            
            cursor.execute(query, params)
            entry_row = cursor.fetchone()
            
            if not entry_row:
                return None
            
            return self._construct_entry_dict(entry_row[0], cursor)
    
    def search_entries(self, search_term: str = None, source_lang: str = None, target_lang: str = None, definition_lang: str = None) -> List[Dict]:
        """Search entries with optional filters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM entries WHERE 1=1"
            params = []
            
            if search_term:
                query += " AND headword LIKE ?"
                params.append(f"%{search_term}%")
            
            if source_lang and source_lang != "All":
                query += " AND source_language = ?"
                params.append(source_lang)
            
            if target_lang and target_lang != "All":
                query += " AND target_language = ?"
                params.append(target_lang)
            
            if definition_lang and definition_lang != "All":
                query += " AND definition_language = ?"
                params.append(definition_lang)
            
            query += " ORDER BY headword"
            
            cursor.execute(query, params)
            entries = []
            
            for row in cursor.fetchall():
                entry = self._construct_entry_dict(row[0], cursor)
                entries.append(entry)
            
            return entries
    
    def get_all_languages(self) -> Dict[str, List[str]]:
        """Get all unique source and target languages"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT source_language FROM entries")
            source_languages = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT DISTINCT target_language FROM entries")
            target_languages = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT DISTINCT definition_language FROM entries")
            definition_languages = [row[0] for row in cursor.fetchall()]
            
            return {
                "source_languages": source_languages,
                "target_languages": target_languages,
                "definition_languages": definition_languages
            }
    
    def _construct_entry_dict(self, entry_id: int, cursor) -> Dict:
        """Helper method to construct complete entry dictionary from database rows"""
        # Get entry details
        cursor.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        entry_row = cursor.fetchone()
        
        # Get meanings
        cursor.execute("SELECT * FROM meanings WHERE entry_id = ?", (entry_id,))
        meaning_rows = cursor.fetchall()
        
        meanings = []
        for meaning_row in meaning_rows:
            meaning_id = meaning_row[0]
            
            # Get examples for this meaning
            cursor.execute("SELECT * FROM examples WHERE meaning_id = ?", (meaning_id,))
            example_rows = cursor.fetchall()
            
            examples = []
            for example_row in example_rows:
                example = {
                    "sentence": example_row[2],
                    "translation": example_row[3]
                }
                
                # Check if this is a context sentence
                if example_row[4] == 1:  # is_context_sentence column
                    example["is_context_sentence"] = True
                
                examples.append(example)
            
            meanings.append({
                "definition": meaning_row[2],
                "grammar": {
                    "noun_type": meaning_row[3],
                    "verb_type": meaning_row[4],
                    "comparison": meaning_row[5]
                },
                "examples": examples
            })
        
        # Construct the final entry dictionary
        part_of_speech = entry_row[2]
        try:
            part_of_speech = json.loads(part_of_speech)
        except (json.JSONDecodeError, TypeError):
            pass  # Keep as string if not JSON
        
        # Get context information
        has_context = entry_row[6]  # has_context column (BOOLEAN)
        
        metadata = {
            "source_language": entry_row[3],
            "target_language": entry_row[4],
            "definition_language": entry_row[5]
        }
        
        # Add context info to metadata if present
        if has_context:
            metadata["has_context"] = True
            
            # Get context sentence from sentence_contexts table
            cursor.execute("""
                SELECT sentence FROM sentence_contexts 
                WHERE entry_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (entry_id,))
            
            context_result = cursor.fetchone()
            if context_result:
                metadata["context_sentence"] = context_result[0]
        
        entry = {
            "metadata": metadata,
            "headword": entry_row[1],
            "part_of_speech": part_of_speech,
            "meanings": meanings
        }
        
        return entry
    
    def migrate_from_json(self, json_file: str):
        """Migrate existing JSON data to the database"""
        try:
            if not os.path.exists(json_file):
                print(f"JSON file {json_file} not found")
                return
            
            with open(json_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            self.add_entry(entry)
                        except json.JSONDecodeError:
                            print(f"Skipping invalid JSON line: {line}")
            
            print(f"Migration from {json_file} completed successfully")
            
        except Exception as e:
            print(f"Error during migration: {e}")
    
    def get_cached_lemma(self, word: str, target_language: str) -> Optional[str]:
        """Get cached lemma if available"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT lemma FROM lemma_cache 
                WHERE word = ? AND target_language = ?
            """, (word, target_language))

            result = cursor.fetchone()
            return result[0] if result else None

    def cache_lemma(self, word: str, lemma: str, target_language: str):
        """Cache a word-lemma mapping"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR IGNORE INTO lemma_cache 
                    (word, lemma, target_language)
                    VALUES (?, ?, ?)
                """, (word, lemma, target_language))

                conn.commit()
        except sqlite3.Error as e:
            print(f"Error caching lemma: {e}")

    def clear_lemma_cache(self):
        """Clear the lemma cache (useful for debugging)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM lemma_cache")
            conn.commit()
    
    def save_sentence_context(self, entry_id: int, sentence: str, selected_text: str) -> bool:
        """Save a sentence context for an entry"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO sentence_contexts 
                    (entry_id, sentence, selected_text)
                    VALUES (?, ?, ?)
                """, (entry_id, sentence, selected_text))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            print(f"Database error saving sentence context: {e}")
            return False
            
    def get_sentence_context(self, entry_id: int) -> Optional[Dict]:
        """Get sentence context for an entry"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT sentence, selected_text FROM sentence_contexts 
                WHERE entry_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (entry_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    "sentence": result[0],
                    "selected_text": result[1]
                }
            
            return None
    def delete_entry(self, headword: str, source_lang: str = None, target_lang: str = None, definition_lang: str = None) -> bool:
        """Delete an entry from the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First get the entry ID to ensure we're deleting the correct entry
                select_query = "SELECT id FROM entries WHERE headword = ?"
                select_params = [headword]
                
                if source_lang:
                    select_query += " AND source_language = ?"
                    select_params.append(source_lang)
                
                if target_lang:
                    select_query += " AND target_language = ?"
                    select_params.append(target_lang)
                
                if definition_lang:
                    select_query += " AND definition_language = ?"
                    select_params.append(definition_lang)
                
                cursor.execute(select_query, select_params)
                entry_result = cursor.fetchone()
                
                if not entry_result:
                    print(f"No entry found matching headword '{headword}' with the specified languages")
                    return False
                
                entry_id = entry_result[0]
                print(f"Found entry ID {entry_id} for headword '{headword}', deleting...")
                
                # Delete in reverse order to respect foreign key constraints
                # First delete the examples
                cursor.execute("""
                    DELETE FROM examples 
                    WHERE meaning_id IN (SELECT id FROM meanings WHERE entry_id = ?)
                """, (entry_id,))
                
                # Then delete the meanings
                cursor.execute("DELETE FROM meanings WHERE entry_id = ?", (entry_id,))
                
                # Finally delete the entry
                cursor.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
                
                # Commit the transaction
                conn.commit()
                
                # Check if any rows were affected in the main entry table
                return True
                
        except sqlite3.Error as e:
            print(f"Database error during deletion: {e}")
            return False
