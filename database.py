import sqlite3
import time

DB_NAME = "chat_app.db"

def init_db():
    """Sets up the persistent SQL message table layout."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                room_code TEXT, 
                sender_name TEXT, 
                content TEXT, 
                timestamp REAL
            )
        ''')
        conn.commit()

def save_message(room_code, sender_name, content):
    """Permanently logs a text string inside the database file."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?)", 
            (room_code, sender_name, content, time.time())
        )
        conn.commit()

def get_room_history(room_code, limit=30):
    """Fetches up to 30 past log records for matching code lookups."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT sender_name, content FROM messages 
            WHERE room_code = ? 
            ORDER BY timestamp ASC LIMIT ?
        ''', (room_code, limit))
        return cursor.fetchall()
