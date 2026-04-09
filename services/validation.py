"""
Validation logic for appointment data.

This module provides validation functions to ensure appointment data
meets all requirements before processing.
"""

from datetime import datetime
from typing import Dict, List, Tuple


def validate_appointment_data(data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate appointment data completeness and correctness.
    
    INPUT: data (dict) - appointment data to validate
    OUTPUT: (is_valid, errors) - tuple of bool and list of error messages
    
    PRECONDITIONS:
    - data is a dictionary (may be empty or incomplete)
    
    POSTCONDITIONS:
    - Returns (True, []) if all validations pass
    - Returns (False, error_list) if any validation fails
    - error_list contains descriptive error messages
    - No side effects on input data
    
    Validates:
    - Required fields: patient_name, appointment_type, procedure, 
      clinician_name, appointment_datetime, channel_preference
    - Field length constraints
    - Date validation (future dates only)
    - appointment_type whitelist validation
    - channel_preference whitelist validation
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10
    """
    errors = []
    
    # Required fields validation (Requirement 1.1)
    required_fields = [
        "patient_name",
        "appointment_type",
        "procedure",
        "clinician_name",
        "appointment_datetime",
        "channel_preference"
    ]
    
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")
    
    # Early return if required fields missing
    if errors:
        return (False, errors)
    
    # Patient name validation (Requirement 1.2)
    if len(data["patient_name"]) > 100:
        errors.append("Patient name must be 100 characters or less")
    
    # Appointment type validation (Requirement 1.3)
    valid_types = ["Surgery", "Consultation", "Imaging", "Lab Work", "Procedure"]
    if data["appointment_type"] not in valid_types:
        errors.append(
            f"Invalid appointment type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Procedure validation (Requirement 1.4)
    if len(data["procedure"]) > 200:
        errors.append("Procedure description must be 200 characters or less")
    
    # Clinician name validation (Requirement 1.5)
    if len(data["clinician_name"]) > 100:
        errors.append("Clinician name must be 100 characters or less")
    
    # Appointment datetime validation (Requirements 1.6, 1.7)
    try:
        # Handle both string and datetime objects
        if isinstance(data["appointment_datetime"], str):
            apt_dt = datetime.fromisoformat(data["appointment_datetime"])
        elif isinstance(data["appointment_datetime"], datetime):
            apt_dt = data["appointment_datetime"]
        else:
            raise ValueError("Invalid datetime type")
        
        if apt_dt <= datetime.now():
            errors.append("Appointment date must be in the future")
    except (ValueError, TypeError):
        errors.append("Invalid appointment datetime format")
    
    # Channel preference validation (Requirement 1.8)
    valid_channels = ["email", "sms", "print"]
    if data["channel_preference"] not in valid_channels:
        errors.append(
            f"Invalid channel preference. Must be one of: {', '.join(valid_channels)}"
        )
    
    # Return validation result (Requirements 1.9, 1.10)
    is_valid = len(errors) == 0
    return (is_valid, errors)
