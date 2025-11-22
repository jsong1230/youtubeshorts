#!/usr/bin/env python3
"""
Database migration script to add cpm_score column to topics table.
"""
import sqlite3
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
import config

def migrate_database():
    """Add cpm_score column to topics table if it doesn't exist."""
    db_path = "data/videos.db"  # Default path used by TopicDatabase
    
    print(f"Migrating database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(topics)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'cpm_score' in columns:
            print("✅ cpm_score column already exists")
            conn.close()
            return True
        
        # Add cpm_score column
        print("Adding cpm_score column...")
        cursor.execute('''
            ALTER TABLE topics
            ADD COLUMN cpm_score REAL DEFAULT 1.0
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ Database migration completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)
