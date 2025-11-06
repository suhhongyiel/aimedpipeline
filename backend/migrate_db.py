"""
Database migration script for adding new columns
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "test.db"

def migrate():
    """Apply database migrations"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if 'user' column exists
    cursor.execute("PRAGMA table_info(mica_pipeline_jobs)")
    columns = [row[1] for row in cursor.fetchall()]
    
    migrations = []
    
    if 'user' not in columns:
        migrations.append("ALTER TABLE mica_pipeline_jobs ADD COLUMN user TEXT;")
        print("✓ Migration: Add 'user' column to mica_pipeline_jobs")
    
    # Apply migrations
    for migration in migrations:
        try:
            cursor.execute(migration)
            print(f"  Applied: {migration}")
        except sqlite3.OperationalError as e:
            print(f"  Skipped (already exists): {migration}")
    
    conn.commit()
    conn.close()
    
    if migrations:
        print(f"\n✅ Applied {len(migrations)} migration(s)")
    else:
        print("\n✅ Database is up to date")

if __name__ == "__main__":
    migrate()

