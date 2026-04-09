"""
Integration tests for MessageBuilder with RulesEngine and LLMClient.

Tests the complete workflow of generating appointment prep messages
using real rules engine output and LLM client integration.
"""

import pytest
from datetime import datetime
from services.message_builder import MessageBuilder
from services.rules_engine import RulesEngine
from services.llm_client import LLMClient


@pytest.fixture
def rules_engine():
    """RulesEngine instance."""
    return RulesEngine()


@pytest.fixture
def llm_client():
    """LLMClient instance without API key (fallback mode)."""
    return LLMClient(api_key=None)


@pytest.fixture
def message_builder(llm_client):
    """MessageBuilder instance."""
    return MessageBuilder(llm_client)


class TestMessageBuilderIntegration:
    """Integration tests for complete message generation workflow."""
    
    def test_surgery_appointment_message(self, rules_engine, message_builder):
        """Test complete message generation for surgery appointment."""
        # Appointment data
        appointment_data = {
            "patient_name": "Alice Johnson",
            "appointment_type": "Surgery",
            "procedure": "Knee surgery",
            "clinician_name": "Dr. Michael Brown",
            "appointment_datetime": datetime(2024, 12, 20, 8, 0, 0),
            "channel_preference": "email"
        }
        
        # Apply rules
        rules = rules_engine.apply_rules(
            appointment_data["appointment_type"],
            appointment_data["procedure"]
        )
        
        # Generate preview
        preview = message_builder.build_preview(appointment_data, rules)
        assert len(preview) > 0
        assert len(preview) <= 200
        assert "Surgery" in preview
        
        # Generate full message
        message = message_builder.build_full_message(appointment_data, rules)
        assert len(message) >= 200
        assert len(message) <= 2000
        assert "Alice Johnson" in message
        assert "8 hours" in message  # Fasting requirement
        assert "60 minutes early" in message  # Arrival time
        assert "responsible adult" in message.lower()
        
        # Generate rules explanation
        explanations = message_builder.format_rules_explanation(rules)
        assert len(explanations) > 0
        assert any("Fasting" in e["rule"] for e in explanations)
    
    def test_colonoscopy_appointment_message(self, rules_engine, message_builder):
        """Test complete message generation for colonoscopy."""
        appointment_data = {
            "patient_name": "Bob Smith",
            "appointment_type": "Procedure",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Sarah Lee",
            "appointment_datetime": datetime(2024, 12, 18, 10, 30, 0),
            "channel_preference": "email"
        }
        
        rules = rules_engine.apply_rules(
            appointment_data["appointment_type"],
            appointment_data["procedure"]
        )
        
        message = message_builder.build_full_message(appointment_data, rules)
        
        # Verify colonoscopy-specific requirements
        assert "12 hours" in message  # Longer fasting
        assert "30 minutes early" in message
        assert "responsible adult" in message.lower()
        assert "bowel prep" in message.lower()
    
    def test_imaging_with_contrast_message(self, rules_engine, message_builder):
        """Test message generation for imaging with contrast."""
        appointment_data = {
            "patient_name": "Carol White",
            "appointment_type": "Imaging",
            "procedure": "CT scan with contrast",
            "clinician_name": "Dr. James Wilson",
            "appointment_datetime": datetime(2024, 12, 22, 14, 0, 0),
            "channel_preference": "email"
        }
        
        rules = rules_engine.apply_rules(
            appointment_data["appointment_type"],
            appointment_data["procedure"]
        )
        
        message = message_builder.build_full_message(appointment_data, rules)
        
        # Verify contrast-specific requirements
        assert "4 hours" in message  # Shorter fasting for contrast
        assert "15 minutes early" in message
        assert "allergies" in message.lower()
    
    def test_lab_work_fasting_message(self, rules_engine, message_builder):
        """Test message generation for fasting blood work."""
        appointment_data = {
            "patient_name": "David Green",
            "appointment_type": "Lab Work",
            "procedure": "Fasting blood work",
            "clinician_name": "Dr. Emily Davis",
            "appointment_datetime": datetime(2024, 12, 16, 7, 30, 0),
            "channel_preference": "email"
        }
        
        rules = rules_engine.apply_rules(
            appointment_data["appointment_type"],
            appointment_data["procedure"]
        )
        
        message = message_builder.build_full_message(appointment_data, rules)
        
        # Verify lab work requirements
        assert "8 hours" in message  # Fasting for blood work
        assert "10 minutes early" in message
        assert "Photo ID" in message
        assert "Insurance Card" in message
    
    def test_consultation_message(self, rules_engine, message_builder):
        """Test message generation for simple consultation."""
        appointment_data = {
            "patient_name": "Emma Taylor",
            "appointment_type": "Consultation",
            "procedure": "Follow-up visit",
            "clinician_name": "Dr. Robert Martinez",
            "appointment_datetime": datetime(2024, 12, 19, 11, 0, 0),
            "channel_preference": "email"
        }
        
        rules = rules_engine.apply_rules(
            appointment_data["appointment_type"],
            appointment_data["procedure"]
        )
        
        message = message_builder.build_full_message(appointment_data, rules)
        
        # Verify consultation has minimal requirements
        assert "Emma Taylor" in message
        assert "15 minutes early" in message
        assert "Photo ID" in message
        # Should not have fasting or responsible adult
        assert "fast" not in message.lower() or "breakfast" in message.lower()
        assert "responsible adult" not in message.lower()
    
    def test_preview_matches_full_message_content(self, rules_engine, message_builder):
        """Test preview is consistent with full message."""
        appointment_data = {
            "patient_name": "Frank Harris",
            "appointment_type": "Surgery",
            "procedure": "Endoscopy",
            "clinician_name": "Dr. Lisa Anderson",
            "appointment_datetime": datetime(2024, 12, 21, 9, 30, 0),
            "channel_preference": "email"
        }
        
        rules = rules_engine.apply_rules(
            appointment_data["appointment_type"],
            appointment_data["procedure"]
        )
        
        preview = message_builder.build_preview(appointment_data, rules)
        message = message_builder.build_full_message(appointment_data, rules)
        
        # Preview should mention key elements that are in full message
        if "fast" in preview.lower():
            assert "12 hours" in message or "8 hours" in message
        
        # Date should be consistent
        assert "December 21, 2024" in preview
        assert "December 21, 2024" in message
    
    def test_rules_explanation_matches_message_content(self, rules_engine, message_builder):
        """Test rules explanation is consistent with message."""
        appointment_data = {
            "patient_name": "Grace Thompson",
            "appointment_type": "Procedure",
            "procedure": "Colonoscopy",
            "clinician_name": "Dr. Kevin Moore",
            "appointment_datetime": datetime(2024, 12, 23, 8, 30, 0),
            "channel_preference": "email"
        }
        
        rules = rules_engine.apply_rules(
            appointment_data["appointment_type"],
            appointment_data["procedure"]
        )
        
        message = message_builder.build_full_message(appointment_data, rules)
        explanations = message_builder.format_rules_explanation(rules)
        
        # Check that explanation items are reflected in message
        for explanation in explanations:
            if "Fasting" in explanation["rule"]:
                # Verify the fasting hours from rules match the message
                assert str(rules.fasting_hours) + " hours" in message
            elif "Arrival" in explanation["rule"]:
                # Verify the arrival time from rules match the message
                assert str(rules.arrival_minutes_early) + " minutes early" in message
            elif "Transportation" in explanation["rule"]:
                assert "responsible adult" in message.lower()
    
    def test_message_with_all_rules_applied(self, rules_engine, message_builder):
        """Test message includes all rules from rules engine."""
        appointment_data = {
            "patient_name": "Henry Wilson",
            "appointment_type": "Surgery",
            "procedure": "Surgery with anesthesia",
            "clinician_name": "Dr. Nancy Clark",
            "appointment_datetime": datetime(2024, 12, 24, 7, 0, 0),
            "channel_preference": "email"
        }
        
        rules = rules_engine.apply_rules(
            appointment_data["appointment_type"],
            appointment_data["procedure"]
        )
        
        message = message_builder.build_full_message(appointment_data, rules)
        
        # Verify all rule components are in message
        assert str(rules.fasting_hours) in message
        assert str(rules.arrival_minutes_early) in message
        
        for item in rules.items_to_bring:
            assert item in message
        
        assert rules.medication_instructions in message
        
        for warning in rules.special_warnings:
            assert warning in message
        
        if rules.requires_responsible_adult:
            assert "responsible adult" in message.lower()
