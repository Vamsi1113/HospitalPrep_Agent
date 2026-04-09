"""
Integration tests for validation with models.

Tests the integration between validation.py and models.py to ensure
they work together correctly.
"""

import pytest
from datetime import datetime, timedelta
from services.validation import validate_appointment_data
from services.models import AppointmentData


class TestValidationIntegration:
    """Integration tests for validation with AppointmentData model."""
    
    def test_valid_data_can_create_appointment_data_object(self):
        """Test that validated data can be used to create AppointmentData object."""
        data = {
            "patient_name": "John Smith",
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": datetime.now() + timedelta(days=7),
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is True
        assert errors == []
        
        # Should be able to create AppointmentData object
        appointment = AppointmentData(
            patient_name=data["patient_name"],
            appointment_type=data["appointment_type"],
            procedure=data["procedure"],
            clinician_name=data["clinician_name"],
            appointment_datetime=data["appointment_datetime"],
            channel_preference=data["channel_preference"]
        )
        
        assert appointment.patient_name == "John Smith"
        assert appointment.appointment_type == "Surgery"
        assert appointment.procedure == "Colonoscopy"
    
    def test_validation_catches_issues_before_model_creation(self):
        """Test that validation catches issues before attempting to create model."""
        data = {
            "patient_name": "A" * 101,  # Too long
            "appointment_type": "InvalidType",
            "procedure": "Test",
            "clinician_name": "Dr. Smith",
            "appointment_datetime": datetime.now() - timedelta(days=1),  # Past date
            "channel_preference": "fax"  # Invalid
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert len(errors) > 0
        
        # Should not attempt to create AppointmentData with invalid data
        # This demonstrates validation prevents bad data from reaching the model
    
    def test_optional_fields_validation(self):
        """Test validation works with optional fields included."""
        data = {
            "patient_name": "John Smith",
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": datetime.now() + timedelta(days=7),
            "channel_preference": "email",
            "fasting_requirement": "8 hours",
            "items_to_bring": "Photo ID, Insurance Card",
            "special_notes": "Patient has latex allergy"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is True
        assert errors == []
        
        # Should be able to create AppointmentData with optional fields
        appointment = AppointmentData(
            patient_name=data["patient_name"],
            appointment_type=data["appointment_type"],
            procedure=data["procedure"],
            clinician_name=data["clinician_name"],
            appointment_datetime=data["appointment_datetime"],
            channel_preference=data["channel_preference"],
            fasting_requirement=data.get("fasting_requirement"),
            items_to_bring=data.get("items_to_bring"),
            special_notes=data.get("special_notes")
        )
        
        assert appointment.special_notes == "Patient has latex allergy"
