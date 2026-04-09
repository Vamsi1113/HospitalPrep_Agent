"""
Message Builder for generating human-friendly appointment prep messages.

This module provides the MessageBuilder class that generates patient-facing
appointment preparation messages from structured rules. It coordinates between
template-based fallback and LLM-powered message generation while ensuring all
medical instructions come from the deterministic rules engine.
"""

from typing import Dict, List
from datetime import datetime, timedelta
from services.models import PrepRules
from services.llm_client import LLMClient


class MessageBuilder:
    """
    Generate human-friendly appointment prep messages from structured rules.
    
    The MessageBuilder coordinates between template-based message generation
    and optional LLM-powered rewriting. All medical instructions must come
    from the PrepRules object - the LLM only improves tone and readability.
    
    Attributes:
        llm_client: LLMClient instance for optional AI-powered message rewriting
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize MessageBuilder with LLM client.
        
        Args:
            llm_client: LLMClient instance (may or may not be available)
        
        Postconditions:
            - self.llm_client is set to provided client
        """
        self.llm_client = llm_client
    
    def build_preview(self, appointment_data: Dict, rules: PrepRules) -> str:
        """
        Generate short preview card text (2-3 sentences).
        
        The preview provides a quick summary of the appointment and key
        preparation requirements for display in preview cards.
        
        Args:
            appointment_data: Dictionary with patient and appointment information
            rules: PrepRules object with preparation requirements
        
        Returns:
            Preview text string (2-3 sentences, max 200 characters)
        
        Preconditions:
            - appointment_data contains required keys: patient_name, appointment_type,
              procedure, clinician_name, appointment_datetime
            - rules is a valid PrepRules object
        
        Postconditions:
            - Returns non-empty string
            - String length is <= 200 characters
            - Contains appointment type, date, and key requirement
        
        Requirements: 3.1, 3.2, 6.10
        """
        # Parse appointment datetime
        apt_dt = appointment_data['appointment_datetime']
        if isinstance(apt_dt, str):
            apt_dt = datetime.fromisoformat(apt_dt)
        
        # Format date and time
        date_str = apt_dt.strftime('%B %d, %Y')
        time_str = apt_dt.strftime('%I:%M %p')
        
        # Build preview with key requirement
        key_requirement = ""
        if rules.fasting_required:
            key_requirement = f" Please fast for {rules.fasting_hours} hours before."
        elif rules.requires_responsible_adult:
            key_requirement = " You will need a driver."
        
        preview = (
            f"Your {appointment_data['appointment_type']} appointment "
            f"is on {date_str} at {time_str}.{key_requirement}"
        )
        
        # Ensure preview is within character limit
        if len(preview) > 200:
            preview = preview[:197] + "..."
        
        return preview
    
    def build_full_message(self, appointment_data: Dict, rules: PrepRules, 
                          use_llm: bool = True) -> str:
        """
        Generate complete appointment prep instructions.
        
        This method generates a complete message with all required sections.
        If use_llm is True and LLM is available, it will attempt to rewrite
        the message in a friendly tone. If LLM fails or is unavailable, it
        falls back to template-based generation.
        
        Args:
            appointment_data: Dictionary with patient and appointment information
            rules: PrepRules object with preparation requirements
            use_llm: Whether to attempt LLM rewriting (default: True)
        
        Returns:
            Complete formatted message string
        
        Preconditions:
            - appointment_data contains all required fields
            - rules is valid PrepRules object with all fields populated
        
        Postconditions:
            - Returns non-empty string
            - Message length is between 200 and 2000 characters
            - Message contains all mandatory sections
            - All medical instructions come from rules (no invention)
        
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 4.4, 4.5, 4.6, 8.3
        """
        # Build structured template message
        template_message = self.build_template_message(appointment_data, rules)
        
        # Attempt LLM rewriting if requested and available
        if use_llm and self.llm_client.is_available():
            rewritten = self.llm_client.rewrite_message(template_message, tone="friendly")
            
            # If LLM succeeds, return rewritten message
            if rewritten:
                return rewritten
            else:
                # Log info when template fallback is used (Requirement 8.3)
                import logging
                logger = logging.getLogger(__name__)
                logger.info("LLM rewrite failed, using template fallback")
        
        # Fallback: return template message
        return template_message
    
    def build_template_message(self, appointment_data: Dict, rules: PrepRules) -> str:
        """
        Fallback template-based message (no LLM).
        
        This method generates a structured message using templates without
        any LLM involvement. It ensures all required sections are included
        based on the rules.
        
        Args:
            appointment_data: Dictionary with patient and appointment information
            rules: PrepRules object with preparation requirements
        
        Returns:
            Complete formatted message string
        
        Preconditions:
            - appointment_data contains all required fields
            - rules is valid PrepRules object
        
        Postconditions:
            - Returns non-empty string
            - Message contains all mandatory sections
            - Message length is between 200 and 2000 characters
        
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 4.3
        """
        sections = []
        
        # Parse appointment datetime
        apt_dt = appointment_data['appointment_datetime']
        if isinstance(apt_dt, str):
            apt_dt = datetime.fromisoformat(apt_dt)
        
        # Section 1: Greeting (Requirement 3.1)
        greeting = f"Dear {appointment_data['patient_name']},"
        sections.append(greeting)
        
        # Section 2: Appointment details (Requirement 3.2)
        apt_details = (
            f"This is a reminder about your {appointment_data['appointment_type']} "
            f"appointment for {appointment_data['procedure']} with "
            f"Dr. {appointment_data['clinician_name']} on "
            f"{apt_dt.strftime('%B %d, %Y at %I:%M %p')}."
        )
        sections.append(apt_details)
        
        # Section 3: Fasting instructions (Requirement 3.3)
        if rules.fasting_required:
            fasting_start = self.calculate_fasting_start_time(apt_dt, rules.fasting_hours)
            fasting_text = (
                f"IMPORTANT: Please do not eat or drink anything for "
                f"{rules.fasting_hours} hours before your appointment. "
                f"This means no food or beverages after "
                f"{fasting_start.strftime('%I:%M %p on %B %d, %Y')}."
            )
            sections.append(fasting_text)
        
        # Section 4: Items to bring (Requirement 3.4)
        items_text = "Please bring the following items:"
        for item in rules.items_to_bring:
            items_text += f"\n- {item}"
        sections.append(items_text)
        
        # Section 5: Arrival time (Requirement 3.5)
        arrival_text = (
            f"Please arrive {rules.arrival_minutes_early} minutes early "
            f"to complete any necessary paperwork."
        )
        sections.append(arrival_text)
        
        # Section 6: Medication instructions (Requirement 3.6)
        sections.append(rules.medication_instructions)
        
        # Section 7: Responsible adult transportation (Requirement 3.7)
        if rules.requires_responsible_adult:
            adult_text = (
                "You will need a responsible adult to drive you home after "
                "the procedure. Please arrange for transportation in advance."
            )
            sections.append(adult_text)
        
        # Section 8: Special warnings (Requirement 3.8)
        for warning in rules.special_warnings:
            sections.append(f"IMPORTANT: {warning}")
        
        # Section 9: Closing (Requirement 3.9)
        closing = (
            "If you have any questions or need to reschedule, please contact "
            "our office. We look forward to seeing you."
        )
        sections.append(closing)
        
        # Join all sections with double newlines
        message = "\n\n".join(sections)
        
        return message
    
    def format_rules_explanation(self, rules: PrepRules) -> List[Dict]:
        """
        Format rules as structured explanation list.
        
        This method converts PrepRules into a list of dictionaries suitable
        for display in the UI as a rules explanation panel.
        
        Args:
            rules: PrepRules object with preparation requirements
        
        Returns:
            List of dictionaries with 'rule' and 'reason' keys
        
        Preconditions:
            - rules is a valid PrepRules object
        
        Postconditions:
            - Returns non-empty list
            - Each dict has 'rule' and 'reason' keys with non-empty strings
        
        Requirements: 4.7, 4.8, 4.9
        """
        explanations = []
        
        # Fasting rule
        if rules.fasting_required:
            explanations.append({
                "rule": "Fasting Required",
                "reason": f"{rules.fasting_hours} hours before procedure"
            })
        
        # Arrival time rule
        explanations.append({
            "rule": "Arrival Time",
            "reason": f"Arrive {rules.arrival_minutes_early} minutes early"
        })
        
        # Items to bring rule
        explanations.append({
            "rule": "Items to Bring",
            "reason": f"{len(rules.items_to_bring)} required items"
        })
        
        # Responsible adult rule
        if rules.requires_responsible_adult:
            explanations.append({
                "rule": "Transportation Required",
                "reason": "Responsible adult driver needed"
            })
        
        # Special warnings
        if rules.special_warnings:
            explanations.append({
                "rule": "Special Instructions",
                "reason": f"{len(rules.special_warnings)} important warning(s)"
            })
        
        # Category
        explanations.append({
            "rule": "Appointment Category",
            "reason": rules.category.capitalize()
        })
        
        return explanations
    
    def calculate_fasting_start_time(self, appointment_datetime: datetime, 
                                    fasting_hours: int) -> datetime:
        """
        Calculate when fasting should start based on appointment time.
        
        This helper function calculates the exact datetime when the patient
        should stop eating and drinking before their appointment.
        
        Args:
            appointment_datetime: Datetime of the appointment
            fasting_hours: Number of hours to fast before appointment
        
        Returns:
            Datetime when fasting should begin
        
        Preconditions:
            - appointment_datetime is a valid datetime object
            - fasting_hours is a positive integer
        
        Postconditions:
            - Returns datetime that is fasting_hours before appointment_datetime
            - Returned datetime is in the past relative to appointment_datetime
        
        Requirements: 3.3
        """
        return appointment_datetime - timedelta(hours=fasting_hours)
