"""
Storage Service for the Appointment Prep AI Agent.

This module provides SQLite persistence for generated appointment prep messages.
All data is stored locally with no cloud dependencies.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8
"""

import sqlite3
import json
import logging
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


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

    
    def save_session_state(self, session_id: str, state_data: Dict) -> bool:
        """
        Save session state for multi-phase workflows.
        
        Args:
            session_id: Unique session identifier
            state_data: Dictionary with session state
        
        Returns:
            True if save successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create sessions table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    state_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Convert state_data to JSON
            state_json = json.dumps(state_data)
            timestamp = datetime.now().isoformat()
            
            # Insert or update session
            cursor.execute("""
                INSERT INTO sessions (session_id, state_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    state_data = excluded.state_data,
                    updated_at = excluded.updated_at
            """, (session_id, state_json, timestamp, timestamp))
            
            conn.commit()
            conn.close()
            
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Session save error: {e}")
            return False
    
    def get_session_state(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve session state.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            Dictionary with session state, or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT state_data FROM sessions WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row is None:
                return None
            
            # Parse JSON state_data
            return json.loads(row["state_data"])
            
        except sqlite3.Error:
            return None
    
    def delete_session_state(self, session_id: str) -> bool:
        """
        Delete session state.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM sessions WHERE session_id = ?
            """, (session_id,))
            
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            return rows_affected > 0
            
        except sqlite3.Error:
            return False
