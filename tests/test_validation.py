"""
Unit tests for services/validation.py

Tests cover all validation requirements including:
- Required field validation
- Field length validation
- Date validation (future dates only)
- appointment_type whitelist validation
- channel_preference whitelist validation
"""

import pytest
from datetime import datetime, timedelta
from services.validation import validate_appointment_data


class TestValidateAppointmentData:
    """Test suite for validate_appointment_data function."""
    
    def test_valid_appointment_data(self):
        """Test validation passes with all valid fields."""
        data = {
            "patient_name": "John Smith",
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is True
        assert errors == []
    
    def test_missing_patient_name(self):
        """Test validation fails when patient_name is missing."""
        data = {
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert "Missing required field: patient_name" in errors
    
    def test_empty_patient_name(self):
        """Test validation fails when patient_name is empty string."""
        data = {
            "patient_name": "",
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert "Missing required field: patient_name" in errors
    
    def test_patient_name_too_long(self):
        """Test validation fails when patient_name exceeds 100 characters."""
        data = {
            "patient_name": "A" * 101,
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert "Patient name must be 100 characters or less" in errors
    
    def test_patient_name_exactly_100_chars(self):
        """Test validation passes when patient_name is exactly 100 characters."""
        data = {
            "patient_name": "A" * 100,
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is True
        assert errors == []
    
    def test_invalid_appointment_type(self):
        """Test validation fails with invalid appointment_type."""
        data = {
            "patient_name": "John Smith",
            "appointment_type": "InvalidType",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert any("Invalid appointment type" in error for error in errors)
    
    def test_valid_appointment_types(self):
        """Test all valid appointment types pass validation."""
        valid_types = ["Surgery", "Consultation", "Imaging", "Lab Work", "Procedure"]
        
        for apt_type in valid_types:
            data = {
                "patient_name": "John Smith",
                "appointment_type": apt_type,
                "procedure": "Test Procedure",
                "clinician_name": "Dr. Sarah Johnson",
                "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
                "channel_preference": "email"
            }
            
            is_valid, errors = validate_appointment_data(data)
            
            assert is_valid is True, f"Failed for appointment_type: {apt_type}"
            assert errors == []
    
    def test_procedure_too_long(self):
        """Test validation fails when procedure exceeds 200 characters."""
        data = {
            "patient_name": "John Smith",
            "appointment_type": "Surgery",
            "procedure": "A" * 201,
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert "Procedure description must be 200 characters or less" in errors
    
    def test_procedure_exactly_200_chars(self):
        """Test validation passes when procedure is exactly 200 characters."""
        data = {
            "patient_name": "John Smith",
            "appointment_type": "Surgery",
            "procedure": "A" * 200,
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is True
        assert errors == []
    
    def test_clinician_name_too_long(self):
        """Test validation fails when clinician_name exceeds 100 characters."""
        data = {
            "patient_name": "John Smith",
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. " + "A" * 98,
            "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert "Clinician name must be 100 characters or less" in errors
    
    def test_past_appointment_datetime(self):
        """Test validation fails when appointment_datetime is in the past."""
        data = {
            "patient_name": "John Smith",
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": (datetime.now() - timedelta(days=1)).isoformat(),
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert "Appointment date must be in the future" in errors
    
    def test_present_appointment_datetime(self):
        """Test validation fails when appointment_datetime is current time."""
        # This test might be flaky due to timing, but should generally work
        data = {
            "patient_name": "John Smith",
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": datetime.now().isoformat(),
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert "Appointment date must be in the future" in errors
    
    def test_invalid_datetime_format(self):
        """Test validation fails with invalid datetime format."""
        data = {
            "patient_name": "John Smith",
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": "not-a-valid-date",
            "channel_preference": "email"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert "Invalid appointment datetime format" in errors
    
    def test_datetime_object_instead_of_string(self):
        """Test validation works with datetime object instead of string."""
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
    
    def test_invalid_channel_preference(self):
        """Test validation fails with invalid channel_preference."""
        data = {
            "patient_name": "John Smith",
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "channel_preference": "fax"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert any("Invalid channel preference" in error for error in errors)
    
    def test_valid_channel_preferences(self):
        """Test all valid channel preferences pass validation."""
        valid_channels = ["email", "sms", "print"]
        
        for channel in valid_channels:
            data = {
                "patient_name": "John Smith",
                "appointment_type": "Surgery",
                "procedure": "Colonoscopy",
                "clinician_name": "Dr. Sarah Johnson",
                "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
                "channel_preference": channel
            }
            
            is_valid, errors = validate_appointment_data(data)
            
            assert is_valid is True, f"Failed for channel_preference: {channel}"
            assert errors == []
    
    def test_multiple_validation_errors(self):
        """Test validation returns all errors when multiple fields are invalid."""
        data = {
            "patient_name": "A" * 101,
            "appointment_type": "InvalidType",
            "procedure": "B" * 201,
            "clinician_name": "Dr. " + "C" * 98,
            "appointment_datetime": "invalid-date",
            "channel_preference": "fax"
        }
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert len(errors) >= 5  # Should have multiple errors
        assert any("Patient name" in error for error in errors)
        assert any("appointment type" in error for error in errors)
        assert any("Procedure" in error for error in errors)
        assert any("Clinician name" in error for error in errors)
        assert any("datetime" in error for error in errors)
        assert any("channel preference" in error for error in errors)
    
    def test_empty_dict(self):
        """Test validation fails with empty dictionary."""
        data = {}
        
        is_valid, errors = validate_appointment_data(data)
        
        assert is_valid is False
        assert len(errors) == 6  # All required fields missing
    
    def test_validation_idempotence(self):
        """Test validation produces same result when called multiple times."""
        data = {
            "patient_name": "John Smith",
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "channel_preference": "email"
        }
        
        result1 = validate_appointment_data(data)
        result2 = validate_appointment_data(data)
        result3 = validate_appointment_data(data)
        
        assert result1 == result2 == result3
    
    def test_no_side_effects_on_input(self):
        """Test validation does not modify input data."""
        data = {
            "patient_name": "John Smith",
            "appointment_type": "Surgery",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Johnson",
            "appointment_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "channel_preference": "email"
        }
        
        original_data = data.copy()
        validate_appointment_data(data)
        
        assert data == original_data
