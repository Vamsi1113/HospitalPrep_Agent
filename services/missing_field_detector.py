"""
Missing Field Detector

Identifies missing required fields in patient intake data and calculates
confidence score based on completeness.
"""

import logging
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)


def detect_missing_fields(
    intake_data: Dict[str, Any],
    appointment_type: str = ""
) -> Dict[str, Any]:
    """
    Detect missing required fields and calculate confidence score.
    
    Args:
        intake_data: Patient intake dictionary
        appointment_type: Type of appointment (Surgery, Consultation, etc.)
    
    Returns:
        Dict with missing_fields, confidence_score, confidence_scores, suggested_options
    """
    # Define required fields with weights
    required_fields = {
        "chief_complaint": 0.3,
        "appointment_type": 0.3,
        "symptoms_description": 0.2,
        "age_group": 0.1,
        "current_medications": 0.05,
        "allergies": 0.05
    }
    
    # Adjust weights based on appointment type
    apt_type_lower = appointment_type.lower() if appointment_type else ""
    
    if any(term in apt_type_lower for term in ["surgery", "procedure"]):
        # For surgery/procedures, medications and allergies are more critical
        required_fields["current_medications"] = 0.15
        required_fields["allergies"] = 0.15
        required_fields["symptoms_description"] = 0.1
    
    # Calculate confidence
    missing_fields = []
    confidence_scores = {}
    total_weight = 0.0
    present_weight = 0.0
    
    for field, weight in required_fields.items():
        total_weight += weight
        
        value = intake_data.get(field)
        is_present = _is_field_present(value)
        
        if is_present:
            present_weight += weight
            confidence_scores[field] = 1.0
        else:
            missing_fields.append(field)
            confidence_scores[field] = 0.0
    
    confidence_score = present_weight / total_weight if total_weight > 0 else 1.0
    
    # Generate suggested options for missing fields
    suggested_options = _generate_suggested_options(missing_fields)
    
    logger.info(
        f"Missing field detection: {len(missing_fields)} missing, "
        f"confidence={confidence_score:.2f}"
    )
    
    return {
        "missing_fields": missing_fields,
        "confidence_score": confidence_score,
        "confidence_scores": confidence_scores,
        "suggested_options": suggested_options
    }


def calculate_confidence(
    intake_data: Dict[str, Any],
    appointment_type: str = ""
) -> float:
    """
    Calculate confidence score based on field completeness.
    
    Args:
        intake_data: Patient intake dictionary
        appointment_type: Type of appointment
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    result = detect_missing_fields(intake_data, appointment_type)
    return result["confidence_score"]


def _is_field_present(value: Any) -> bool:
    """
    Check if a field value is present and non-empty.
    
    Args:
        value: Field value to check
    
    Returns:
        True if field is present and non-empty
    """
    if value is None:
        return False
    
    if isinstance(value, str):
        return len(value.strip()) > 0
    
    if isinstance(value, list):
        return len(value) > 0
    
    # For other types, consider present if not None
    return True


def _generate_suggested_options(missing_fields: List[str]) -> Dict[str, List[str]]:
    """
    Generate suggested options for missing fields.
    
    Args:
        missing_fields: List of missing field names
    
    Returns:
        Dict mapping field names to suggested options
    """
    suggestions = {}
    
    for field in missing_fields:
        if field == "chief_complaint":
            suggestions[field] = [
                "Chest pain",
                "Shortness of breath",
                "Abdominal pain",
                "Headache",
                "Fever",
                "Fatigue",
                "Other"
            ]
        
        elif field == "appointment_type":
            suggestions[field] = [
                "Consultation",
                "Surgery",
                "Imaging",
                "Lab Work",
                "Procedure",
                "Follow-up"
            ]
        
        elif field == "age_group":
            suggestions[field] = [
                "18-30",
                "30-40",
                "40-50",
                "50-60",
                "60-70",
                "70-80",
                "80+"
            ]
        
        elif field == "symptoms_description":
            suggestions[field] = [
                "Describe when symptoms started",
                "Describe severity (mild/moderate/severe)",
                "Describe what makes it better or worse"
            ]
        
        elif field == "current_medications":
            suggestions[field] = [
                "None",
                "List all medications you're currently taking"
            ]
        
        elif field == "allergies":
            suggestions[field] = [
                "None",
                "Penicillin",
                "Sulfa drugs",
                "Aspirin",
                "Other"
            ]
    
    return suggestions
