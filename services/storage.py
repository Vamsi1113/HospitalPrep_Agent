"""
Storage Service for the Appointment Prep AI Agent.

This module provides SQLite persistence for generated appointment prep messages.
All data is stored locally with no cloud dependencies.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8
"""

import sqlite3
import json
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path


class StorageService:
    """
    SQLite-based persistence layer for generated messages.
    
    Schema:
    - messages table with columns:
      - id (INTEGER PRIMARY KEY)
      - patient_name (TEXT)
      - appointment_type (TEXT)
      - procedure (TEXT)
      - clinician_name (TEXT)
      - appointment_datetime (TEXT)
      - channel_preference (TEXT)
      - full_message (TEXT)
      - rules_used (TEXT - JSON)
      - generated_at (TEXT - ISO datetime)
      - llm_used (INTEGER - boolean)
    """
    
    def __init__(self, db_path: str = "data/appointments.db"):
        """
        Initialize storage service with database path.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def init_db(self) -> None:
        """
        Initialize SQLite database schema if it doesn't exist.
        
        Creates the messages table with all required columns.
        Validates: Requirement 5.1
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                appointment_type TEXT NOT NULL,
                procedure TEXT NOT NULL,
                clinician_name TEXT NOT NULL,
                appointment_datetime TEXT NOT NULL,
                channel_preference TEXT NOT NULL,
                full_message TEXT NOT NULL,
                rules_used TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                llm_used INTEGER NOT NULL
            )
        """)
        
        # Create index on generated_at for efficient history queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_generated_at 
            ON messages(generated_at DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def save_message(
        self,
        appointment_data: Dict,
        generated_text: str,
        rules_used: Dict
    ) -> int:
        """
        Save generated message to database.
        
        Args:
            appointment_data: Dictionary with patient and appointment info
            generated_text: The complete generated message text
            rules_used: Dictionary representation of PrepRules
        
        Returns:
            Positive integer message_id of saved record
        
        Raises:
            Exception: If database write fails with descriptive error
        
        Validates: Requirements 5.2, 5.3, 5.4, 5.8
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Auto-generate timestamp
            generated_at = datetime.now().isoformat()
            
            # Convert rules_used dict to JSON string
            rules_json = json.dumps(rules_used)
            
            # Use parameterized query to prevent SQL injection
            cursor.execute("""
                INSERT INTO messages (
                    patient_name,
                    appointment_type,
                    procedure,
                    clinician_name,
                    appointment_datetime,
                    channel_preference,
                    full_message,
                    rules_used,
                    generated_at,
                    llm_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                appointment_data.get("patient_name"),
                appointment_data.get("appointment_type"),
                appointment_data.get("procedure"),
                appointment_data.get("clinician_name"),
                appointment_data.get("appointment_datetime"),
                appointment_data.get("channel_preference"),
                generated_text,
                rules_json,
                generated_at,
                appointment_data.get("llm_used", 0)
            ))
            
            message_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return message_id
            
        except sqlite3.Error as e:
            raise Exception(f"Database error while saving message: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to save message: {str(e)}")
    
    def get_message(self, message_id: int) -> Optional[Dict]:
        """
        Retrieve saved message by ID.
        
        Args:
            message_id: The ID of the message to retrieve
        
        Returns:
            Dictionary with complete message record, or None if not found
        
        Validates: Requirement 5.5
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM messages WHERE id = ?
            """, (message_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row is None:
                return None
            
            # Convert row to dictionary
            message = dict(row)
            
            # Parse JSON rules_used back to dict
            message["rules_used"] = json.loads(message["rules_used"])
            
            return message
            
        except sqlite3.Error:
            return None
    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """
        Retrieve recent message history.
        
        Args:
            limit: Maximum number of messages to return (default 20)
        
        Returns:
            List of message dictionaries, ordered by most recent first
        
        Validates: Requirement 5.6
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM messages 
                ORDER BY generated_at DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert rows to list of dictionaries
            history = []
            for row in rows:
                message = dict(row)
                message["rules_used"] = json.loads(message["rules_used"])
                history.append(message)
            
            return history
            
        except sqlite3.Error:
            return []
    
    def delete_message(self, message_id: int) -> bool:
        """
        Delete message by ID.
        
        Args:
            message_id: The ID of the message to delete
        
        Returns:
            True if deletion successful, False otherwise
        
        Validates: Requirement 5.7
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM messages WHERE id = ?
            """, (message_id,))
            
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            return rows_affected > 0
            
        except sqlite3.Error:
            return False
