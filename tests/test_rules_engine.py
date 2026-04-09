"""
Unit tests for the RulesEngine class.

Tests all appointment type logic and rule application scenarios.
"""

import pytest
from services.rules_engine import RulesEngine
from services.models import PrepRules


class TestRulesEngine:
    """Test suite for RulesEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = RulesEngine()
    
    def test_surgery_rules(self):
        """Test surgery appointment rules (Requirement 2.1)."""
        rules = self.engine.apply_rules("Surgery", "Knee surgery")
        
        assert rules.fasting_required is True
        assert rules.fasting_hours == 8
        assert rules.arrival_minutes_early == 60
        assert rules.requires_responsible_adult is True
        assert "Photo ID" in rules.items_to_bring
        assert "Insurance Card" in rules.items_to_bring
        assert "List of current medications" in rules.items_to_bring
        assert "Completed pre-op forms" in rules.items_to_bring
        assert "Do not drive yourself home after surgery" in rules.special_warnings
        assert rules.category == "surgery"
    
    def test_colonoscopy_rules(self):
        """Test colonoscopy appointment rules (Requirement 2.2)."""
        rules = self.engine.apply_rules("Procedure", "colonoscopy")
        
        assert rules.fasting_required is True
        assert rules.fasting_hours == 12
        assert rules.arrival_minutes_early == 30
        assert rules.requires_responsible_adult is True
        assert "Photo ID" in rules.items_to_bring
        assert "Insurance Card" in rules.items_to_bring
        assert "Prep kit instructions" in rules.items_to_bring
        assert "Complete bowel prep as instructed" in rules.special_warnings
        assert rules.category == "endoscopy"
    
    def test_endoscopy_rules(self):
        """Test endoscopy appointment rules (Requirement 2.2)."""
        rules = self.engine.apply_rules("Procedure", "upper endoscopy")
        
        assert rules.fasting_required is True
        assert rules.fasting_hours == 12
        assert rules.arrival_minutes_early == 30
        assert rules.requires_responsible_adult is True
        assert rules.category == "endoscopy"
    
    def test_imaging_without_contrast(self):
        """Test imaging appointment without contrast (Requirement 2.3)."""
        rules = self.engine.apply_rules("Imaging", "MRI scan")
        
        assert rules.fasting_required is False
        assert rules.fasting_hours == 0
        assert rules.arrival_minutes_early == 15
        assert rules.requires_responsible_adult is False
        assert "Photo ID" in rules.items_to_bring
        assert "Insurance Card" in rules.items_to_bring
        assert rules.category == "imaging"
    
    def test_imaging_with_contrast(self):
        """Test imaging appointment with contrast (Requirement 2.4)."""
        rules = self.engine.apply_rules("Imaging", "CT scan with contrast")
        
        assert rules.fasting_required is True
        assert rules.fasting_hours == 4
        assert rules.arrival_minutes_early == 15
        assert "Inform technician of any allergies" in rules.special_warnings
        assert rules.category == "imaging"
    
    def test_lab_work_without_fasting(self):
        """Test lab work without fasting (Requirement 2.5)."""
        rules = self.engine.apply_rules("Lab Work", "blood test")
        
        assert rules.fasting_required is False
        assert rules.fasting_hours == 0
        assert rules.arrival_minutes_early == 10
        assert "Photo ID" in rules.items_to_bring
        assert "Insurance Card" in rules.items_to_bring
        assert rules.category == "lab"
    
    def test_lab_work_with_fasting(self):
        """Test lab work with fasting (Requirement 2.6)."""
        rules = self.engine.apply_rules("Lab Work", "fasting blood work")
        
        assert rules.fasting_required is True
        assert rules.fasting_hours == 8
        assert rules.arrival_minutes_early == 10
        assert rules.category == "lab"
    
    def test_mandatory_items_all_types(self):
        """Test mandatory items included for all types (Requirement 2.7)."""
        test_cases = [
            ("Surgery", "knee surgery"),
            ("Imaging", "MRI"),
            ("Lab Work", "blood test"),
            ("Consultation", "follow-up"),
            ("Procedure", "biopsy")
        ]
        
        for apt_type, procedure in test_cases:
            rules = self.engine.apply_rules(apt_type, procedure)
            assert "Photo ID" in rules.items_to_bring, f"Failed for {apt_type}"
            assert "Insurance Card" in rules.items_to_bring, f"Failed for {apt_type}"
    
    def test_fasting_consistency_false(self):
        """Test fasting_hours is 0 when fasting not required (Requirement 2.8)."""
        rules = self.engine.apply_rules("Consultation", "follow-up visit")
        
        assert rules.fasting_required is False
        assert rules.fasting_hours == 0
    
    def test_fasting_consistency_true(self):
        """Test fasting_hours > 0 when fasting required (Requirement 2.9)."""
        test_cases = [
            ("Surgery", "appendectomy", 8),
            ("Procedure", "colonoscopy", 12),
            ("Imaging", "CT with contrast", 4),
            ("Lab Work", "fasting blood work", 8)
        ]
        
        for apt_type, procedure, expected_hours in test_cases:
            rules = self.engine.apply_rules(apt_type, procedure)
            assert rules.fasting_required is True
            assert rules.fasting_hours > 0
            assert rules.fasting_hours == expected_hours
    
    def test_category_assignment(self):
        """Test category assignment for all types (Requirement 2.10)."""
        test_cases = [
            ("Surgery", "knee surgery", "surgery"),
            ("Procedure", "colonoscopy", "endoscopy"),
            ("Imaging", "MRI", "imaging"),
            ("Lab Work", "blood test", "lab"),
            ("Consultation", "follow-up", "consultation")
        ]
        
        valid_categories = {"surgery", "endoscopy", "imaging", "lab", "consultation"}
        
        for apt_type, procedure, expected_category in test_cases:
            rules = self.engine.apply_rules(apt_type, procedure)
            assert rules.category in valid_categories
            assert rules.category == expected_category
    
    def test_case_insensitive_matching(self):
        """Test that rule matching is case-insensitive."""
        rules1 = self.engine.apply_rules("SURGERY", "KNEE SURGERY")
        rules2 = self.engine.apply_rules("surgery", "knee surgery")
        rules3 = self.engine.apply_rules("Surgery", "Knee Surgery")
        
        assert rules1.category == rules2.category == rules3.category == "surgery"
        assert rules1.fasting_hours == rules2.fasting_hours == rules3.fasting_hours == 8
    
    def test_procedure_keyword_detection(self):
        """Test that procedure keywords are detected correctly."""
        # Test surgery keyword in procedure
        rules = self.engine.apply_rules("Procedure", "outpatient surgery")
        assert rules.category == "surgery"
        
        # Test MRI keyword
        rules = self.engine.apply_rules("Procedure", "brain MRI")
        assert rules.category == "imaging"
        
        # Test blood keyword
        rules = self.engine.apply_rules("Procedure", "routine blood work")
        assert rules.category == "lab"
    
    def test_get_mandatory_items(self):
        """Test get_mandatory_items helper method."""
        # Surgery
        items = self.engine.get_mandatory_items("Surgery")
        assert "Photo ID" in items
        assert "Insurance Card" in items
        assert "List of current medications" in items
        assert "Completed pre-op forms" in items
        
        # Consultation
        items = self.engine.get_mandatory_items("Consultation")
        assert "Photo ID" in items
        assert "Insurance Card" in items
        assert "List of current medications" in items
    
    def test_requires_fasting_helper(self):
        """Test requires_fasting helper method."""
        # Surgery
        required, hours = self.engine.requires_fasting("knee surgery")
        assert required is True
        assert hours == 8
        
        # Colonoscopy
        required, hours = self.engine.requires_fasting("colonoscopy")
        assert required is True
        assert hours == 12
        
        # Contrast imaging
        required, hours = self.engine.requires_fasting("CT scan with contrast")
        assert required is True
        assert hours == 4
        
        # Fasting blood work
        required, hours = self.engine.requires_fasting("fasting blood test")
        assert required is True
        assert hours == 8
        
        # No fasting
        required, hours = self.engine.requires_fasting("consultation")
        assert required is False
        assert hours == 0
    
    def test_validate_appointment_data_wrapper(self):
        """Test that validate_appointment_data wrapper works."""
        from datetime import datetime, timedelta
        future_date = (datetime.now() + timedelta(days=30)).isoformat()
        
        valid_data = {
            "patient_name": "John Doe",
            "appointment_type": "Surgery",
            "procedure": "Knee surgery",
            "clinician_name": "Dr. Smith",
            "appointment_datetime": future_date,
            "channel_preference": "email"
        }
        
        is_valid, errors = self.engine.validate_appointment_data(valid_data)
        assert is_valid is True
        assert errors == []
        
        # Test with missing field
        invalid_data = {"patient_name": "John Doe"}
        is_valid, errors = self.engine.validate_appointment_data(invalid_data)
        assert is_valid is False
        assert len(errors) > 0
