"""
Unit tests for StorageService.

Tests cover:
- Database initialization
- Message save and retrieve
- History retrieval with pagination
- Message deletion
- Error handling
"""

import pytest
import sqlite3
import json
import tempfile
import os
from datetime import datetime
from pathlib import Path

from services.storage import StorageService


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create temporary file
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    yield path
    
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def storage(temp_db):
    """Create StorageService instance with temporary database."""
    service = StorageService(db_path=temp_db)
    service.init_db()
    return service


@pytest.fixture
def sample_appointment_data():
    """Sample appointment data for testing."""
    return {
        "patient_name": "John Smith",
        "appointment_type": "Surgery",
        "procedure": "Colonoscopy",
        "clinician_name": "Dr. Sarah Johnson",
        "appointment_datetime": "2024-02-15T09:00:00",
        "channel_preference": "email",
        "llm_used": 1
    }


@pytest.fixture
def sample_rules():
    """Sample rules data for testing."""
    return {
        "fasting_required": True,
        "fasting_hours": 12,
        "items_to_bring": ["Photo ID", "Insurance Card"],
        "arrival_minutes_early": 30,
        "medication_instructions": "Take regular medications",
        "requires_responsible_adult": True,
        "special_warnings": ["Complete bowel prep"],
        "category": "endoscopy"
    }


class TestStorageServiceInit:
    """Tests for StorageService initialization."""
    
    def test_init_creates_data_directory(self):
        """Test that init creates data directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "subdir", "test.db")
            storage = StorageService(db_path=db_path)
            
            assert Path(db_path).parent.exists()
    
    def test_init_db_creates_schema(self, temp_db):
        """Test that init_db creates the messages table."""
        storage = StorageService(db_path=temp_db)
        storage.init_db()
        
        # Verify table exists
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='messages'
        """)
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == "messages"
    
    def test_init_db_creates_index(self, temp_db):
        """Test that init_db creates index on generated_at."""
        storage = StorageService(db_path=temp_db)
        storage.init_db()
        
        # Verify index exists
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_generated_at'
        """)
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == "idx_generated_at"
    
    def test_init_db_idempotent(self, temp_db):
        """Test that init_db can be called multiple times safely."""
        storage = StorageService(db_path=temp_db)
        storage.init_db()
        storage.init_db()  # Should not raise error
        
        # Verify table still exists
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='messages'
        """)
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None


class TestSaveMessage:
    """Tests for save_message functionality."""
    
    def test_save_message_returns_positive_id(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that save_message returns a positive integer ID."""
        message_id = storage.save_message(
            sample_appointment_data,
            "Test message content",
            sample_rules
        )
        
        assert isinstance(message_id, int)
        assert message_id > 0
    
    def test_save_message_stores_all_fields(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that all fields are stored correctly."""
        message_text = "Complete test message"
        message_id = storage.save_message(
            sample_appointment_data,
            message_text,
            sample_rules
        )
        
        # Retrieve and verify
        conn = sqlite3.connect(storage.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        row = cursor.fetchone()
        conn.close()
        
        assert row["patient_name"] == sample_appointment_data["patient_name"]
        assert row["appointment_type"] == sample_appointment_data["appointment_type"]
        assert row["procedure"] == sample_appointment_data["procedure"]
        assert row["clinician_name"] == sample_appointment_data["clinician_name"]
        assert row["appointment_datetime"] == sample_appointment_data["appointment_datetime"]
        assert row["channel_preference"] == sample_appointment_data["channel_preference"]
        assert row["full_message"] == message_text
        assert row["llm_used"] == 1
    
    def test_save_message_stores_rules_as_json(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that rules are stored as valid JSON."""
        message_id = storage.save_message(
            sample_appointment_data,
            "Test message",
            sample_rules
        )
        
        # Retrieve and parse JSON
        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT rules_used FROM messages WHERE id = ?", (message_id,))
        rules_json = cursor.fetchone()[0]
        conn.close()
        
        # Should be valid JSON
        parsed_rules = json.loads(rules_json)
        assert parsed_rules == sample_rules
    
    def test_save_message_auto_generates_timestamp(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that generated_at timestamp is automatically set."""
        before = datetime.now()
        
        message_id = storage.save_message(
            sample_appointment_data,
            "Test message",
            sample_rules
        )
        
        after = datetime.now()
        
        # Retrieve timestamp
        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT generated_at FROM messages WHERE id = ?", (message_id,))
        timestamp_str = cursor.fetchone()[0]
        conn.close()
        
        timestamp = datetime.fromisoformat(timestamp_str)
        assert before <= timestamp <= after
    
    def test_save_message_uses_parameterized_queries(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that SQL injection is prevented via parameterized queries."""
        # Try to inject SQL
        malicious_data = sample_appointment_data.copy()
        malicious_data["patient_name"] = "'; DROP TABLE messages; --"
        
        message_id = storage.save_message(
            malicious_data,
            "Test message",
            sample_rules
        )
        
        # Table should still exist
        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert message_id > 0
    
    def test_save_message_handles_missing_llm_used(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that llm_used defaults to 0 if not provided."""
        data = sample_appointment_data.copy()
        del data["llm_used"]
        
        message_id = storage.save_message(
            data,
            "Test message",
            sample_rules
        )
        
        # Retrieve and verify
        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT llm_used FROM messages WHERE id = ?", (message_id,))
        llm_used = cursor.fetchone()[0]
        conn.close()
        
        assert llm_used == 0


class TestGetMessage:
    """Tests for get_message functionality."""
    
    def test_get_message_returns_complete_record(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that get_message returns all fields."""
        message_text = "Test message content"
        message_id = storage.save_message(
            sample_appointment_data,
            message_text,
            sample_rules
        )
        
        result = storage.get_message(message_id)
        
        assert result is not None
        assert result["id"] == message_id
        assert result["patient_name"] == sample_appointment_data["patient_name"]
        assert result["full_message"] == message_text
        assert result["rules_used"] == sample_rules
    
    def test_get_message_returns_none_for_invalid_id(self, storage):
        """Test that get_message returns None for non-existent ID."""
        result = storage.get_message(99999)
        assert result is None
    
    def test_get_message_parses_rules_json(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that rules_used is parsed from JSON to dict."""
        message_id = storage.save_message(
            sample_appointment_data,
            "Test message",
            sample_rules
        )
        
        result = storage.get_message(message_id)
        
        assert isinstance(result["rules_used"], dict)
        assert result["rules_used"]["fasting_required"] == True
        assert result["rules_used"]["fasting_hours"] == 12


class TestGetHistory:
    """Tests for get_history functionality."""
    
    def test_get_history_returns_recent_messages(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that get_history returns saved messages."""
        # Save multiple messages
        id1 = storage.save_message(sample_appointment_data, "Message 1", sample_rules)
        id2 = storage.save_message(sample_appointment_data, "Message 2", sample_rules)
        id3 = storage.save_message(sample_appointment_data, "Message 3", sample_rules)
        
        history = storage.get_history()
        
        assert len(history) == 3
        # Should be ordered by most recent first
        assert history[0]["id"] == id3
        assert history[1]["id"] == id2
        assert history[2]["id"] == id1
    
    def test_get_history_respects_limit(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that get_history respects the limit parameter."""
        # Save 5 messages
        for i in range(5):
            storage.save_message(
                sample_appointment_data,
                f"Message {i}",
                sample_rules
            )
        
        history = storage.get_history(limit=3)
        
        assert len(history) == 3
    
    def test_get_history_returns_empty_list_when_no_messages(self, storage):
        """Test that get_history returns empty list when database is empty."""
        history = storage.get_history()
        assert history == []
    
    def test_get_history_parses_rules_json(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that rules_used is parsed for all messages in history."""
        storage.save_message(sample_appointment_data, "Message 1", sample_rules)
        
        history = storage.get_history()
        
        assert len(history) == 1
        assert isinstance(history[0]["rules_used"], dict)
        assert history[0]["rules_used"]["category"] == "endoscopy"


class TestDeleteMessage:
    """Tests for delete_message functionality."""
    
    def test_delete_message_removes_record(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that delete_message removes the record."""
        message_id = storage.save_message(
            sample_appointment_data,
            "Test message",
            sample_rules
        )
        
        result = storage.delete_message(message_id)
        
        assert result is True
        
        # Verify message is gone
        retrieved = storage.get_message(message_id)
        assert retrieved is None
    
    def test_delete_message_returns_false_for_invalid_id(self, storage):
        """Test that delete_message returns False for non-existent ID."""
        result = storage.delete_message(99999)
        assert result is False
    
    def test_delete_message_does_not_affect_other_records(
        self, storage, sample_appointment_data, sample_rules
    ):
        """Test that deleting one message doesn't affect others."""
        id1 = storage.save_message(sample_appointment_data, "Message 1", sample_rules)
        id2 = storage.save_message(sample_appointment_data, "Message 2", sample_rules)
        id3 = storage.save_message(sample_appointment_data, "Message 3", sample_rules)
        
        storage.delete_message(id2)
        
        # Other messages should still exist
        assert storage.get_message(id1) is not None
        assert storage.get_message(id2) is None
        assert storage.get_message(id3) is not None


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_save_message_raises_on_database_error(self, temp_db):
        """Test that save_message raises exception on database error."""
        storage = StorageService(db_path=temp_db)
        # Don't initialize database - should cause error
        
        with pytest.raises(Exception) as exc_info:
            storage.save_message(
                {"patient_name": "Test"},
                "Message",
                {}
            )
        
        assert "Database error" in str(exc_info.value) or "Failed to save" in str(exc_info.value)
    
    def test_get_message_handles_database_error_gracefully(self):
        """Test that get_message returns None on database error."""
        storage = StorageService(db_path="/invalid/path/db.db")
        result = storage.get_message(1)
        assert result is None
    
    def test_get_history_handles_database_error_gracefully(self):
        """Test that get_history returns empty list on database error."""
        storage = StorageService(db_path="/invalid/path/db.db")
        result = storage.get_history()
        assert result == []
    
    def test_delete_message_handles_database_error_gracefully(self):
        """Test that delete_message returns False on database error."""
        storage = StorageService(db_path="/invalid/path/db.db")
        result = storage.delete_message(1)
        assert result is False
