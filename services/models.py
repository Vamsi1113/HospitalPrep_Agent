"""
Data models for the Appointment Prep AI Agent.

This module defines the core dataclasses used throughout the application:
- AppointmentData: Patient and appointment information with validation
- PrepRules: Deterministic preparation requirements
- GeneratedMessage: Complete message record for persistence
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict


@dataclass
class AppointmentData:
    """
    Patient and appointment information.
    
    Validation Rules:
    - patient_name: non-empty string, max 100 chars
    - appointment_type: must be in predefined list
    - procedure: non-empty string, max 200 chars
    - clinician_name: non-empty string, max 100 chars
    - appointment_datetime: must be future date
    - channel_preference: must be "email", "sms", or "print"
    """
    patient_name: str
    appointment_type: str  # e.g., "Surgery", "Consultation", "Imaging"
    procedure: str  # e.g., "Colonoscopy", "MRI", "Blood Work"
    clinician_name: str
    appointment_datetime: datetime
    channel_preference: str  # "email", "sms", "print"
    fasting_requirement: Optional[str] = None  # User override
    items_to_bring: Optional[str] = None  # User override
    special_notes: Optional[str] = None


@dataclass
class PrepRules:
    """
    Deterministic preparation requirements for an appointment.
    
    All fields are populated by the rules engine based on appointment type
    and procedure. No medical instructions should be invented beyond these rules.
    """
    fasting_required: bool
    fasting_hours: int
    items_to_bring: List[str]
    arrival_minutes_early: int
    medication_instructions: str
    requires_responsible_adult: bool
    special_warnings: List[str]
    category: str  # "surgery", "endoscopy", "imaging", "lab", "consultation"


@dataclass
class GeneratedMessage:
    """
    Complete generated message record for persistence.
    
    Validation Rules:
    - preview_text: max 200 chars
    - full_message: max 2000 chars
    - generated_at: auto-set to current timestamp
    """
    message_id: int
    appointment_data: AppointmentData
    preview_text: str
    full_message: str
    rules_used: PrepRules
    rules_explanation: List[Dict]
    generated_at: datetime
    llm_used: bool
