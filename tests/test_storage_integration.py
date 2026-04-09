"""
Integration tests for StorageService with data models.

Tests the interaction between StorageService and the AppointmentData/PrepRules models.
"""

import pytest
import tempfile
import os
from datetime import datetime

from services.storage import StorageService
from services.models import AppointmentData, PrepRules


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    yield path
    
    # Cleanup
    try:
        if os.path.exists(path):
            os.unlink(path)
    except PermissionError:
        pass  # Windows file lock issue


@pytest.fixture
def storage(temp_db):
    """Create StorageService instance with temporary database."""
    service = StorageService(db_path=temp_db)
    service.init_db()
    return service


@pytest.fixture
def appointment_data():
    """Create sample AppointmentData instance."""
    return AppointmentData(
        patient_name="Jane Doe",
        appointment_type="Surgery",
        procedure="Knee Replacement Surgery",
        clinician_name="Dr. Michael Chen",
        appointment_datetime=datetime(2024, 3, 15, 10, 30),
        channel_preference="email",
        special_notes="Patient has metal allergy"
    )


@pytest.fixture
def prep_rules():
    """Create sample PrepRules instance."""
    return PrepRules(
        fasting_required=True,
        fasting_hours=8,
        items_to_bring=["Photo ID", "Insurance Card", "List of medications"],
        arrival_minutes_early=60,
        medication_instructions="Do not take blood thinners 24 hours before surgery",
        requires_responsible_adult=True,
        special_warnings=["Arrange transportation", "No food or drink after midnight"],
        category="surgery"
    )


class TestStorageIntegration:
    """Integration tests for StorageService with models."""
    
    def test_save_and_retrieve_with_dataclass_models(
        self, storage, appointment_data, prep_rules
    ):
        """Test saving and retrieving using dataclass models."""
        # Convert models to dicts for storage
        appointment_dict = {
            "patient_name": appointment_data.patient_name,
            "appointment_type": appointment_data.appointment_type,
            "procedure": appointment_data.procedure,
            "clinician_name": appointment_data.clinician_name,
            "appointment_datetime": appointment_data.appointment_datetime.isoformat(),
            "channel_preference": appointment_data.channel_preference,
            "llm_used": 1
        }
        
        rules_dict = {
            "fasting_required": prep_rules.fasting_required,
            "fasting_hours": prep_rules.fasting_hours,
            "items_to_bring": prep_rules.items_to_bring,
            "arrival_minutes_early": prep_rules.arrival_minutes_early,
            "medication_instructions": prep_rules.medication_instructions,
            "requires_responsible_adult": prep_rules.requires_responsible_adult,
            "special_warnings": prep_rules.special_warnings,
            "category": prep_rules.category
        }
        
        message_text = "Dear Jane Doe, your surgery is scheduled..."
        
        # Save
        message_id = storage.save_message(
            appointment_dict,
            message_text,
            rules_dict
        )
        
        # Retrieve
        result = storage.get_message(message_id)
        
        # Verify all data matches
        assert result["patient_name"] == appointment_data.patient_name
        assert result["appointment_type"] == appointment_data.appointment_type
        assert result["procedure"] == appointment_data.procedure
        assert result["full_message"] == message_text
        assert result["rules_used"]["fasting_required"] == prep_rules.fasting_required
        assert result["rules_used"]["fasting_hours"] == prep_rules.fasting_hours
        assert result["rules_used"]["category"] == prep_rules.category
    
    def test_database_round_trip_preserves_data(
        self, storage, appointment_data, prep_rules
    ):
        """Test that data survives round-trip to database unchanged."""
        appointment_dict = {
            "patient_name": appointment_data.patient_name,
            "appointment_type": appointment_data.appointment_type,
            "procedure": appointment_data.procedure,
            "clinician_name": appointment_data.clinician_name,
            "appointment_datetime": appointment_data.appointment_datetime.isoformat(),
            "channel_preference": appointment_data.channel_preference,
            "llm_used": 0
        }
        
        rules_dict = {
            "fasting_required": prep_rules.fasting_required,
            "fasting_hours": prep_rules.fasting_hours,
            "items_to_bring": prep_rules.items_to_bring,
            "arrival_minutes_early": prep_rules.arrival_minutes_early,
            "medication_instructions": prep_rules.medication_instructions,
            "requires_responsible_adult": prep_rules.requires_responsible_adult,
            "special_warnings": prep_rules.special_warnings,
            "category": prep_rules.category
        }
        
        original_message = "This is the complete appointment preparation message."
        
        # Save
        message_id = storage.save_message(
            appointment_dict,
            original_message,
            rules_dict
        )
        
        # Retrieve
        retrieved = storage.get_message(message_id)
        
        # Verify exact match
        assert retrieved["full_message"] == original_message
        assert retrieved["rules_used"] == rules_dict
    
    def test_multiple_messages_with_different_rules(self, storage):
        """Test storing multiple messages with different rule configurations."""
        # Surgery appointment
        surgery_data = {
            "patient_name": "Patient A",
            "appointment_type": "Surgery",
            "procedure": "Appendectomy",
            "clinician_name": "Dr. Smith",
            "appointment_datetime": "2024-04-01T08:00:00",
            "channel_preference": "email",
            "llm_used": 1
        }
        surgery_rules = {
            "fasting_required": True,
            "fasting_hours": 8,
            "items_to_bring": ["Photo ID", "Insurance Card"],
            "arrival_minutes_early": 60,
            "medication_instructions": "No medications",
            "requires_responsible_adult": True,
            "special_warnings": ["Arrange ride home"],
            "category": "surgery"
        }
        
        # Lab appointment
        lab_data = {
            "patient_name": "Patient B",
            "appointment_type": "Lab Work",
            "procedure": "Fasting Blood Work",
            "clinician_name": "Dr. Jones",
            "appointment_datetime": "2024-04-02T07:00:00",
            "channel_preference": "sms",
            "llm_used": 0
        }
        lab_rules = {
            "fasting_required": True,
            "fasting_hours": 8,
            "items_to_bring": ["Photo ID", "Insurance Card"],
            "arrival_minutes_early": 10,
            "medication_instructions": "Take regular medications",
            "requires_responsible_adult": False,
            "special_warnings": [],
            "category": "lab"
        }
        
        # Save both
        id1 = storage.save_message(surgery_data, "Surgery message", surgery_rules)
        id2 = storage.save_message(lab_data, "Lab message", lab_rules)
        
        # Retrieve and verify
        msg1 = storage.get_message(id1)
        msg2 = storage.get_message(id2)
        
        assert msg1["rules_used"]["category"] == "surgery"
        assert msg1["rules_used"]["requires_responsible_adult"] == True
        
        assert msg2["rules_used"]["category"] == "lab"
        assert msg2["rules_used"]["requires_responsible_adult"] == False
    
    def test_history_returns_most_recent_first(self, storage):
        """Test that history is ordered by most recent first."""
        # Create 3 messages with slight delays
        for i in range(3):
            data = {
                "patient_name": f"Patient {i}",
                "appointment_type": "Consultation",
                "procedure": f"Procedure {i}",
                "clinician_name": "Dr. Test",
                "appointment_datetime": "2024-05-01T10:00:00",
                "channel_preference": "email",
                "llm_used": 0
            }
            rules = {
                "fasting_required": False,
                "fasting_hours": 0,
                "items_to_bring": ["Photo ID"],
                "arrival_minutes_early": 15,
                "medication_instructions": "None",
                "requires_responsible_adult": False,
                "special_warnings": [],
                "category": "consultation"
            }
            storage.save_message(data, f"Message {i}", rules)
        
        history = storage.get_history()
        
        # Most recent should be first
        assert history[0]["patient_name"] == "Patient 2"
        assert history[1]["patient_name"] == "Patient 1"
        assert history[2]["patient_name"] == "Patient 0"
