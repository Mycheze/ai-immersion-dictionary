#!/usr/bin/env python
"""
Migration script to convert existing JSON dictionary data to SQLite database
"""
import sys
import argparse
import os
from database_manager import DatabaseManager

def migrate_data(json_file, db_file=None):
    """Migrate data from JSON file to SQLite database"""
    
    if not os.path.exists(json_file):
        print(f"Error: {json_file} does not exist")
        return False
    
    # Create database manager
    db_manager = DatabaseManager(db_file) if db_file else DatabaseManager()
    
    print(f"Migrating data from {json_file} to database...")
    
    try:
        db_manager.migrate_from_json(json_file)
        print("Migration completed successfully!")
        
        # Check how many entries were imported
        all_entries = db_manager.search_entries()
        print(f"Total entries in database: {len(all_entries)}")
        
        return True
        
    except Exception as e:
        print(f"Error during migration: {e}")
        return False

def main():
    """Main entry point for migration script"""
    parser = argparse.ArgumentParser(description="Migrate JSON dictionary data to SQLite database")
    parser.add_argument("json_file", help="Path to the JSON file to migrate")
    parser.add_argument("--db", help="Path to the SQLite database file (default: dictionary.db)", default=None)
    parser.add_argument("--backup", action="store_true", help="Create a backup of existing database before migration")
    
    args = parser.parse_args()
    
    # Create backup if requested
    if args.backup and args.db and os.path.exists(args.db):
        backup_file = f"{args.db}.backup"
        print(f"Creating backup: {backup_file}")
        with open(args.db, 'rb') as src, open(backup_file, 'wb') as dst:
            dst.write(src.read())
    
    # Perform migration
    success = migrate_data(args.json_file, args.db)
    
    if not success:
        sys.exit(1)
    
    print("\nMigration Summary:")
    print("------------------")
    print(f"Source JSON file: {args.json_file}")
    print(f"Target database: {args.db or 'dictionary.db'}")
    print("\nYou can now run your application with the new database backend.")

if __name__ == "__main__":
    main()