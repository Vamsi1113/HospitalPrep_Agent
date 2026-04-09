"""
Unit tests for MessageBuilder class.

Tests cover:
- Preview generation
- Full message generation with LLM
- Template fallback message generation
- Rules explanation formatting
- Fasting start time calculation
- Message completeness and structure
"""

import pytest
from datetime import datetime, timedelta
from services.message_builder import MessageBuilder
from services.models import PrepRules
from services.llm_client import LLMClient


@pytest.fixture
def llm_client_unavailable():
    """LLM client without API key (fallback mode)."""
    return LLMClient(api_key=None)


@pytest.fixture
def llm_client_available():
    """LLM client with mock API key."""
    return LLMClient(api_key="test-key-123")


@pytest.fixture
def message_builder_no_llm(llm_client_unavailable):
    """MessageBuilder with unavailable LLM."""
    return MessageBuilder(llm_client_unavailable)


@pytest.fixture
def message_builder_with_llm(llm_client_available):
    """MessageBuilder with available LLM."""
    return MessageBuilder(llm_client_available)


@pytest.fixture
def sample_appointment_data():
    """Sample appointment data for testing."""
    return {
        "patient_name": "John Smith",
        "appointment_type": "Surgery",
        "procedure": "Colonoscopy",
        "clinician_name": "Dr. Sarah Johnson",
        "appointment_datetime": datetime(2024, 12, 15, 9, 0, 0),
        "channel_preference": "email"
    }


@pytest.fixture
def sample_rules_fasting():
    """Sample PrepRules with fasting required."""
    return PrepRules(
        fasting_required=True,
        fasting_hours=12,
        items_to_bring=["Photo ID", "Insurance Card", "Prep kit instructions"],
        arrival_minutes_early=30,
        medication_instructions="Take regular medications unless instructed otherwise",
        requires_responsible_adult=True,
        special_warnings=["Complete bowel prep as instructed"],
        category="endoscopy"
    )


@pytest.fixture
def sample_rules_no_fasting():
    """Sample PrepRules without fasting."""
    return PrepRules(
        fasting_required=False,
        fasting_hours=0,
        items_to_bring=["Photo ID", "Insurance Card"],
        arrival_minutes_early=15,
        medication_instructions="Take regular medications unless instructed otherwise",
        requires_responsible_adult=False,
        special_warnings=[],
        category="consultation"
    )


class TestBuildPreview:
    """Tests for build_preview() method."""
    
    def test_preview_with_fasting(self, message_builder_no_llm, sample_appointment_data, 
                                  sample_rules_fasting):
        """Test preview generation with fasting requirement."""
        preview = message_builder_no_llm.build_preview(
            sample_appointment_data, sample_rules_fasting
        )
        
        assert isinstance(preview, str)
        assert len(preview) > 0
        assert len(preview) <= 200
        assert "Surgery" in preview
        assert "December 15, 2024" in preview
        assert "09:00 AM" in preview
        assert "12 hours" in preview or "fast" in preview.lower()
    
    def test_preview_with_driver_requirement(self, message_builder_no_llm, 
                                            sample_appointment_data, sample_rules_fasting):
        """Test preview mentions driver requirement."""
        preview = message_builder_no_llm.build_preview(
            sample_appointment_data, sample_rules_fasting
        )
        
        # Should mention either fasting or driver (fasting takes priority)
        assert "fast" in preview.lower() or "driver" in preview.lower()
    
    def test_preview_without_special_requirements(self, message_builder_no_llm, 
                                                  sample_appointment_data, 
                                                  sample_rules_no_fasting):
        """Test preview without fasting or driver requirements."""
        preview = message_builder_no_llm.build_preview(
            sample_appointment_data, sample_rules_no_fasting
        )
        
        assert isinstance(preview, str)
        assert len(preview) > 0
        assert len(preview) <= 200
        assert "Surgery" in preview
        assert "December 15, 2024" in preview
    
    def test_preview_with_string_datetime(self, message_builder_no_llm, sample_rules_fasting):
        """Test preview handles ISO string datetime."""
        data = {
            "patient_name": "Jane Doe",
            "appointment_type": "Imaging",
            "procedure": "MRI with contrast",
            "clinician_name": "Dr. Smith",
            "appointment_datetime": "2024-12-20T14:30:00",
            "channel_preference": "email"
        }
        
        preview = message_builder_no_llm.build_preview(data, sample_rules_fasting)
        
        assert isinstance(preview, str)
        assert len(preview) <= 200
        assert "Imaging" in preview
    
    def test_preview_length_constraint(self, message_builder_no_llm, sample_rules_fasting):
        """Test preview is truncated if too long."""
        data = {
            "patient_name": "Very Long Patient Name That Goes On And On",
            "appointment_type": "Very Long Appointment Type Description",
            "procedure": "Very Long Procedure Description That Exceeds Normal Length",
            "clinician_name": "Dr. Very Long Clinician Name",
            "appointment_datetime": datetime(2024, 12, 15, 9, 0, 0),
            "channel_preference": "email"
        }
        
        preview = message_builder_no_llm.build_preview(data, sample_rules_fasting)
        
        assert len(preview) <= 200


class TestBuildTemplateMessage:
    """Tests for build_template_message() method."""
    
    def test_template_contains_all_mandatory_sections(self, message_builder_no_llm, 
                                                      sample_appointment_data, 
                                                      sample_rules_fasting):
        """Test template message contains all required sections."""
        message = message_builder_no_llm.build_template_message(
            sample_appointment_data, sample_rules_fasting
        )
        
        # Requirement 3.1: Greeting
        assert "Dear John Smith" in message
        
        # Requirement 3.2: Appointment details
        assert "Surgery" in message
        assert "Colonoscopy" in message
        assert "Dr. Sarah Johnson" in message
        assert "December 15, 2024" in message
        
        # Requirement 3.3: Fasting instructions (when required)
        assert "12 hours" in message
        assert "do not eat or drink" in message.lower()
        
        # Requirement 3.4: Items to bring
        assert "Photo ID" in message
        assert "Insurance Card" in message
        assert "Prep kit instructions" in message
        
        # Requirement 3.5: Arrival time
        assert "30 minutes early" in message
        
        # Requirement 3.6: Medication instructions
        assert "medications" in message.lower()
        
        # Requirement 3.7: Responsible adult
        assert "responsible adult" in message.lower()
        assert "drive you home" in message.lower()
        
        # Requirement 3.8: Special warnings
        assert "IMPORTANT" in message
        assert "Complete bowel prep" in message
        
        # Requirement 3.9: Closing
        assert "questions" in message.lower()
        assert "contact" in message.lower()
    
    def test_template_without_fasting(self, message_builder_no_llm, sample_appointment_data, 
                                     sample_rules_no_fasting):
        """Test template message without fasting instructions."""
        message = message_builder_no_llm.build_template_message(
            sample_appointment_data, sample_rules_no_fasting
        )
        
        # Should not contain fasting instructions
        assert "fast" not in message.lower() or "breakfast" in message.lower()
        
        # Should still contain other sections
        assert "Dear John Smith" in message
        assert "Photo ID" in message
        assert "15 minutes early" in message
    
    def test_template_without_responsible_adult(self, message_builder_no_llm, 
                                               sample_appointment_data, 
                                               sample_rules_no_fasting):
        """Test template message without responsible adult requirement."""
        message = message_builder_no_llm.build_template_message(
            sample_appointment_data, sample_rules_no_fasting
        )
        
        # Should not contain transportation warning
        assert "responsible adult" not in message.lower()
        assert "drive you home" not in message.lower()
    
    def test_template_message_length(self, message_builder_no_llm, sample_appointment_data, 
                                    sample_rules_fasting):
        """Test template message length is within bounds (Requirement 3.10)."""
        message = message_builder_no_llm.build_template_message(
            sample_appointment_data, sample_rules_fasting
        )
        
        assert len(message) >= 200
        assert len(message) <= 2000
    
    def test_template_with_string_datetime(self, message_builder_no_llm, sample_rules_fasting):
        """Test template handles ISO string datetime."""
        data = {
            "patient_name": "Jane Doe",
            "appointment_type": "Imaging",
            "procedure": "MRI",
            "clinician_name": "Dr. Smith",
            "appointment_datetime": "2024-12-20T14:30:00",
            "channel_preference": "email"
        }
        
        message = message_builder_no_llm.build_template_message(data, sample_rules_fasting)
        
        assert "Dear Jane Doe" in message
        assert "December 20, 2024" in message
        assert "02:30 PM" in message
    
    def test_template_with_multiple_warnings(self, message_builder_no_llm, 
                                           sample_appointment_data):
        """Test template includes all special warnings."""
        rules = PrepRules(
            fasting_required=True,
            fasting_hours=8,
            items_to_bring=["Photo ID", "Insurance Card"],
            arrival_minutes_early=60,
            medication_instructions="Do not take blood thinners",
            requires_responsible_adult=True,
            special_warnings=[
                "Do not drive yourself home",
                "Inform technician of allergies",
                "Bring completed forms"
            ],
            category="surgery"
        )
        
        message = message_builder_no_llm.build_template_message(
            sample_appointment_data, rules
        )
        
        assert "Do not drive yourself home" in message
        assert "Inform technician of allergies" in message
        assert "Bring completed forms" in message
        assert message.count("IMPORTANT") >= 3


class TestBuildFullMessage:
    """Tests for build_full_message() method."""
    
    def test_full_message_with_unavailable_llm(self, message_builder_no_llm, 
                                               sample_appointment_data, 
                                               sample_rules_fasting):
        """Test full message falls back to template when LLM unavailable."""
        message = message_builder_no_llm.build_full_message(
            sample_appointment_data, sample_rules_fasting, use_llm=True
        )
        
        # Should return template message
        assert isinstance(message, str)
        assert len(message) >= 200
        assert "Dear John Smith" in message
    
    def test_full_message_with_use_llm_false(self, message_builder_with_llm, 
                                            sample_appointment_data, 
                                            sample_rules_fasting):
        """Test full message uses template when use_llm=False."""
        message = message_builder_with_llm.build_full_message(
            sample_appointment_data, sample_rules_fasting, use_llm=False
        )
        
        # Should return template message even if LLM available
        assert isinstance(message, str)
        assert len(message) >= 200
    
    def test_full_message_equivalence_to_template(self, message_builder_no_llm, 
                                                  sample_appointment_data, 
                                                  sample_rules_fasting):
        """Test full message equals template when LLM unavailable (Requirement 4.6)."""
        full_message = message_builder_no_llm.build_full_message(
            sample_appointment_data, sample_rules_fasting, use_llm=True
        )
        
        template_message = message_builder_no_llm.build_template_message(
            sample_appointment_data, sample_rules_fasting
        )
        
        assert full_message == template_message


class TestFormatRulesExplanation:
    """Tests for format_rules_explanation() method."""
    
    def test_rules_explanation_structure(self, message_builder_no_llm, sample_rules_fasting):
        """Test rules explanation returns proper structure."""
        explanations = message_builder_no_llm.format_rules_explanation(sample_rules_fasting)
        
        assert isinstance(explanations, list)
        assert len(explanations) > 0
        
        for explanation in explanations:
            assert isinstance(explanation, dict)
            assert "rule" in explanation
            assert "reason" in explanation
            assert isinstance(explanation["rule"], str)
            assert isinstance(explanation["reason"], str)
            assert len(explanation["rule"]) > 0
            assert len(explanation["reason"]) > 0
    
    def test_rules_explanation_includes_fasting(self, message_builder_no_llm, 
                                               sample_rules_fasting):
        """Test rules explanation includes fasting when required."""
        explanations = message_builder_no_llm.format_rules_explanation(sample_rules_fasting)
        
        fasting_rules = [e for e in explanations if "Fasting" in e["rule"]]
        assert len(fasting_rules) == 1
        assert "12 hours" in fasting_rules[0]["reason"]
    
    def test_rules_explanation_includes_arrival(self, message_builder_no_llm, 
                                               sample_rules_fasting):
        """Test rules explanation includes arrival time."""
        explanations = message_builder_no_llm.format_rules_explanation(sample_rules_fasting)
        
        arrival_rules = [e for e in explanations if "Arrival" in e["rule"]]
        assert len(arrival_rules) == 1
        assert "30 minutes" in arrival_rules[0]["reason"]
    
    def test_rules_explanation_includes_items(self, message_builder_no_llm, 
                                             sample_rules_fasting):
        """Test rules explanation includes items to bring."""
        explanations = message_builder_no_llm.format_rules_explanation(sample_rules_fasting)
        
        items_rules = [e for e in explanations if "Items" in e["rule"]]
        assert len(items_rules) == 1
        assert "3 required items" in items_rules[0]["reason"]
    
    def test_rules_explanation_includes_transportation(self, message_builder_no_llm, 
                                                      sample_rules_fasting):
        """Test rules explanation includes transportation when required."""
        explanations = message_builder_no_llm.format_rules_explanation(sample_rules_fasting)
        
        transport_rules = [e for e in explanations if "Transportation" in e["rule"]]
        assert len(transport_rules) == 1
        assert "driver" in transport_rules[0]["reason"].lower()
    
    def test_rules_explanation_includes_warnings(self, message_builder_no_llm, 
                                                sample_rules_fasting):
        """Test rules explanation includes special warnings."""
        explanations = message_builder_no_llm.format_rules_explanation(sample_rules_fasting)
        
        warning_rules = [e for e in explanations if "Special" in e["rule"]]
        assert len(warning_rules) == 1
        assert "1 important warning" in warning_rules[0]["reason"]
    
    def test_rules_explanation_includes_category(self, message_builder_no_llm, 
                                                 sample_rules_fasting):
        """Test rules explanation includes appointment category."""
        explanations = message_builder_no_llm.format_rules_explanation(sample_rules_fasting)
        
        category_rules = [e for e in explanations if "Category" in e["rule"]]
        assert len(category_rules) == 1
        assert "Endoscopy" in category_rules[0]["reason"]
    
    def test_rules_explanation_without_optional_items(self, message_builder_no_llm, 
                                                     sample_rules_no_fasting):
        """Test rules explanation without fasting or transportation."""
        explanations = message_builder_no_llm.format_rules_explanation(
            sample_rules_no_fasting
        )
        
        # Should not include fasting
        fasting_rules = [e for e in explanations if "Fasting" in e["rule"]]
        assert len(fasting_rules) == 0
        
        # Should not include transportation
        transport_rules = [e for e in explanations if "Transportation" in e["rule"]]
        assert len(transport_rules) == 0
        
        # Should still include arrival, items, category
        assert len(explanations) >= 3


class TestCalculateFastingStartTime:
    """Tests for calculate_fasting_start_time() helper function."""
    
    def test_fasting_start_time_calculation(self, message_builder_no_llm):
        """Test fasting start time is correctly calculated."""
        appointment_time = datetime(2024, 12, 15, 9, 0, 0)
        fasting_hours = 12
        
        start_time = message_builder_no_llm.calculate_fasting_start_time(
            appointment_time, fasting_hours
        )
        
        expected = datetime(2024, 12, 14, 21, 0, 0)
        assert start_time == expected
    
    def test_fasting_start_time_8_hours(self, message_builder_no_llm):
        """Test 8-hour fasting calculation."""
        appointment_time = datetime(2024, 12, 15, 14, 30, 0)
        fasting_hours = 8
        
        start_time = message_builder_no_llm.calculate_fasting_start_time(
            appointment_time, fasting_hours
        )
        
        expected = datetime(2024, 12, 15, 6, 30, 0)
        assert start_time == expected
    
    def test_fasting_start_time_4_hours(self, message_builder_no_llm):
        """Test 4-hour fasting calculation."""
        appointment_time = datetime(2024, 12, 15, 10, 0, 0)
        fasting_hours = 4
        
        start_time = message_builder_no_llm.calculate_fasting_start_time(
            appointment_time, fasting_hours
        )
        
        expected = datetime(2024, 12, 15, 6, 0, 0)
        assert start_time == expected
    
    def test_fasting_start_time_is_before_appointment(self, message_builder_no_llm):
        """Test fasting start time is always before appointment."""
        appointment_time = datetime(2024, 12, 15, 9, 0, 0)
        
        for hours in [4, 8, 12, 24]:
            start_time = message_builder_no_llm.calculate_fasting_start_time(
                appointment_time, hours
            )
            assert start_time < appointment_time
            
            # Verify exact time difference
            time_diff = appointment_time - start_time
            assert time_diff == timedelta(hours=hours)


class TestMessageCompleteness:
    """Integration tests for message completeness (Requirement 3.10, 3.11)."""
    
    def test_message_contains_no_invented_instructions(self, message_builder_no_llm, 
                                                       sample_appointment_data, 
                                                       sample_rules_fasting):
        """Test message contains only instructions from rules (Requirement 3.11)."""
        message = message_builder_no_llm.build_template_message(
            sample_appointment_data, sample_rules_fasting
        )
        
        # All fasting hours should match rules
        assert str(sample_rules_fasting.fasting_hours) in message
        
        # All items should be in message
        for item in sample_rules_fasting.items_to_bring:
            assert item in message
        
        # Arrival time should match rules
        assert str(sample_rules_fasting.arrival_minutes_early) in message
        
        # Medication instructions should match rules
        assert sample_rules_fasting.medication_instructions in message
        
        # All warnings should be in message
        for warning in sample_rules_fasting.special_warnings:
            assert warning in message
    
    def test_message_length_bounds(self, message_builder_no_llm):
        """Test all messages are within 200-2000 character bounds (Requirement 3.10)."""
        test_cases = [
            {
                "data": {
                    "patient_name": "John Doe",
                    "appointment_type": "Surgery",
                    "procedure": "Colonoscopy",
                    "clinician_name": "Dr. Smith",
                    "appointment_datetime": datetime(2024, 12, 15, 9, 0, 0),
                    "channel_preference": "email"
                },
                "rules": PrepRules(
                    fasting_required=True,
                    fasting_hours=12,
                    items_to_bring=["Photo ID", "Insurance Card", "Prep kit"],
                    arrival_minutes_early=30,
                    medication_instructions="Take regular medications",
                    requires_responsible_adult=True,
                    special_warnings=["Complete prep"],
                    category="endoscopy"
                )
            },
            {
                "data": {
                    "patient_name": "Jane Smith",
                    "appointment_type": "Consultation",
                    "procedure": "Follow-up",
                    "clinician_name": "Dr. Johnson",
                    "appointment_datetime": datetime(2024, 12, 20, 14, 0, 0),
                    "channel_preference": "email"
                },
                "rules": PrepRules(
                    fasting_required=False,
                    fasting_hours=0,
                    items_to_bring=["Photo ID", "Insurance Card"],
                    arrival_minutes_early=15,
                    medication_instructions="Take regular medications",
                    requires_responsible_adult=False,
                    special_warnings=[],
                    category="consultation"
                )
            }
        ]
        
        for case in test_cases:
            message = message_builder_no_llm.build_template_message(
                case["data"], case["rules"]
            )
            assert len(message) >= 200, f"Message too short: {len(message)} chars"
            assert len(message) <= 2000, f"Message too long: {len(message)} chars"
