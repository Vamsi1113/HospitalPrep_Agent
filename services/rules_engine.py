"""
Rules Engine for deterministic appointment preparation requirements.

This module provides the RulesEngine class that applies safety-critical
preparation rules based on appointment type and procedure. All medical
instructions must come from this deterministic engine - no AI invention allowed.
"""

from typing import Dict, List, Tuple
from services.models import PrepRules
from services.validation import validate_appointment_data


class RulesEngine:
    """
    Deterministic rule-based logic for medical appointment preparation requirements.
    
    This class is safety-critical: all medical instructions (fasting, items to bring,
    arrival time, warnings) must be determined by these rules, not invented by AI.
    """
    
    def __init__(self):
        """Initialize the rules engine."""
        pass
    
    def apply_rules(self, appointment_type: str, procedure: str) -> PrepRules:
        """
        Apply deterministic rules based on appointment type and procedure.
        
        INPUT: appointment_type (str), procedure (str)
        OUTPUT: PrepRules object with all preparation requirements
        
        PRECONDITIONS:
        - appointment_type is non-empty string
        - procedure is non-empty string
        
        POSTCONDITIONS:
        - Returns PrepRules with all fields populated
        - fasting_hours is 0 if fasting_required is False
        - items_to_bring contains at least ["Photo ID", "Insurance Card"]
        - arrival_minutes_early is between 10 and 60
        - category is one of: "surgery", "endoscopy", "imaging", "lab", "consultation"
        
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10
        """
        # Initialize default rules with mandatory items (Requirement 2.7)
        rules = PrepRules(
            fasting_required=False,
            fasting_hours=0,
            items_to_bring=["Photo ID", "Insurance Card"],
            arrival_minutes_early=15,
            medication_instructions="Take regular medications unless instructed otherwise",
            requires_responsible_adult=False,
            special_warnings=[],
            category="consultation"
        )
        
        # Normalize inputs for case-insensitive matching
        apt_type_lower = appointment_type.lower()
        proc_lower = procedure.lower()
        
        # Apply surgery rules (Requirement 2.1)
        if apt_type_lower == "surgery" or "surgery" in proc_lower:
            rules.fasting_required = True
            rules.fasting_hours = 8
            rules.arrival_minutes_early = 60
            rules.requires_responsible_adult = True
            rules.items_to_bring.extend([
                "List of current medications",
                "Completed pre-op forms"
            ])
            rules.special_warnings.append(
                "Do not drive yourself home after surgery"
            )
            rules.category = "surgery"
        
        # Apply endoscopy/colonoscopy rules (Requirement 2.2)
        elif "colonoscopy" in proc_lower or "endoscopy" in proc_lower:
            rules.fasting_required = True
            rules.fasting_hours = 12
            rules.arrival_minutes_early = 30
            rules.requires_responsible_adult = True
            rules.items_to_bring.append("Prep kit instructions")
            rules.special_warnings.append(
                "Complete bowel prep as instructed"
            )
            rules.category = "endoscopy"
        
        # Apply imaging rules (Requirement 2.3, 2.4)
        elif apt_type_lower == "imaging" or any(
            img in proc_lower for img in ["mri", "ct", "x-ray", "ultrasound"]
        ):
            rules.arrival_minutes_early = 15
            # Contrast-specific rules (Requirement 2.4)
            if "contrast" in proc_lower:
                rules.fasting_required = True
                rules.fasting_hours = 4
                rules.special_warnings.append(
                    "Inform technician of any allergies"
                )
            rules.category = "imaging"
        
        # Apply lab work rules (Requirement 2.5, 2.6)
        elif "blood" in proc_lower or "lab" in proc_lower:
            rules.arrival_minutes_early = 10
            # Fasting blood work (Requirement 2.6)
            if "fasting" in proc_lower:
                rules.fasting_required = True
                rules.fasting_hours = 8
            rules.category = "lab"
        
        # Default consultation rules
        else:
            rules.category = "consultation"
            rules.items_to_bring.append("List of current medications")
        
        # Ensure fasting consistency (Requirements 2.8, 2.9)
        if not rules.fasting_required:
            rules.fasting_hours = 0
        
        return rules
    
    def validate_appointment_data(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate required fields and return (is_valid, errors).
        
        This is a convenience wrapper around the validation module.
        
        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10
        """
        return validate_appointment_data(data)
    
    def get_mandatory_items(self, appointment_type: str) -> List[str]:
        """
        Get mandatory items for appointment type.
        
        All appointment types require Photo ID and Insurance Card (Requirement 2.7).
        Additional items depend on the appointment type.
        """
        # Base mandatory items for all appointments
        mandatory = ["Photo ID", "Insurance Card"]
        
        apt_type_lower = appointment_type.lower()
        
        if apt_type_lower == "surgery":
            mandatory.extend([
                "List of current medications",
                "Completed pre-op forms"
            ])
        elif apt_type_lower in ["consultation", "imaging", "lab work", "procedure"]:
            mandatory.append("List of current medications")
        
        return mandatory
    
    def requires_fasting(self, procedure: str) -> Tuple[bool, int]:
        """
        Check if fasting required and return (required, hours).
        
        This is a helper method to determine fasting requirements
        based on procedure keywords.
        """
        proc_lower = procedure.lower()
        
        # Surgery procedures
        if "surgery" in proc_lower:
            return (True, 8)
        
        # Endoscopy/colonoscopy procedures
        if "colonoscopy" in proc_lower or "endoscopy" in proc_lower:
            return (True, 12)
        
        # Imaging with contrast
        if "contrast" in proc_lower and any(
            img in proc_lower for img in ["mri", "ct", "x-ray", "ultrasound"]
        ):
            return (True, 4)
        
        # Fasting blood work
        if "fasting" in proc_lower and ("blood" in proc_lower or "lab" in proc_lower):
            return (True, 8)
        
        # No fasting required
        return (False, 0)
