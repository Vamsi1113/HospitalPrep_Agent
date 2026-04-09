"""
Preparation Plan Builder Service.

This module generates structured preparation plan sections based on
validated appointment data and rules engine output.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from services.models import PrepRules


class PrepPlanBuilder:
    """
    Builds structured preparation plan sections.
    
    This service takes validated appointment data and rules output,
    then generates comprehensive, clinically-appropriate preparation
    instructions organized into structured sections.
    """
    
    def build_prep_sections(
        self,
        appointment_data: Dict,
        rules: PrepRules
    ) -> Dict:
        """
        Build structured preparation plan sections.
        
        Args:
            appointment_data: Validated appointment data
            rules: PrepRules from rules engine
        
        Returns:
            Dictionary with structured sections matching PrepPlanSections TypedDict
        """
        sections = {
            "appointment_summary": self._build_summary(appointment_data, rules),
            "fasting_plan": self._build_fasting_plan(appointment_data, rules) if rules.fasting_required else None,
            "diet_guidance": self._build_diet_guidance(appointment_data, rules),
            "medication_instructions": self._build_medication_instructions(appointment_data, rules),
            "items_to_bring": rules.items_to_bring,
            "arrival_instructions": self._build_arrival_instructions(appointment_data, rules),
            "transport_instructions": self._build_transport_instructions(rules) if rules.requires_responsible_adult else None,
            "red_flag_warnings": self._build_red_flag_warnings(appointment_data, rules),
            "procedure_specific_notes": self._build_procedure_notes(appointment_data, rules),
            "closing_note": self._build_closing_note(appointment_data)
        }
        
        return sections
    
    def _build_summary(self, data: Dict, rules: PrepRules) -> str:
        """Build appointment summary section."""
        apt_datetime = self._parse_datetime(data.get("appointment_datetime"))
        
        summary = f"Patient: {data.get('patient_name')}\n"
        summary += f"Appointment Type: {data.get('appointment_type')}\n"
        summary += f"Procedure: {data.get('procedure')}\n"
        summary += f"Clinician: {data.get('clinician_name')}\n"
        summary += f"Date & Time: {apt_datetime.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
        summary += f"Category: {rules.category.title()}"
        
        return summary
    
    def _build_fasting_plan(self, data: Dict, rules: PrepRules) -> Optional[str]:
        """Build fasting instructions section."""
        if not rules.fasting_required:
            return None
        
        apt_datetime = self._parse_datetime(data.get("appointment_datetime"))
        fasting_start = apt_datetime - timedelta(hours=rules.fasting_hours)
        
        plan = f"You must fast for {rules.fasting_hours} hours before your appointment.\n\n"
        plan += f"STOP EATING: {fasting_start.strftime('%I:%M %p on %A, %B %d')}\n"
        plan += f"APPOINTMENT TIME: {apt_datetime.strftime('%I:%M %p on %A, %B %d')}\n\n"
        
        # Clear fluids guidance
        if rules.fasting_hours >= 8:
            clear_fluids_cutoff = apt_datetime - timedelta(hours=2)
            plan += f"Clear fluids (water, clear juice, black coffee/tea) are allowed until {clear_fluids_cutoff.strftime('%I:%M %p')}.\n"
            plan += "After that time, nothing by mouth including water.\n\n"
        else:
            plan += "No food or drink after the cutoff time, including water.\n\n"
        
        plan += "IMPORTANT: If you eat or drink after the cutoff time, your procedure may need to be rescheduled for your safety."
        
        return plan
    
    def _build_diet_guidance(self, data: Dict, rules: PrepRules) -> Optional[str]:
        """Build diet guidance section."""
        # Only provide diet guidance for procedures requiring special prep
        if rules.category == "endoscopy":
            guidance = "SPECIAL DIET REQUIREMENTS:\n\n"
            guidance += "3 days before procedure:\n"
            guidance += "• Avoid seeds, nuts, popcorn, and raw vegetables\n"
            guidance += "• Stick to low-fiber foods\n\n"
            guidance += "1 day before procedure:\n"
            guidance += "• Clear liquids only (broth, clear juice, gelatin, popsicles)\n"
            guidance += "• No red or purple colored liquids\n"
            guidance += "• Complete your bowel prep as instructed\n\n"
            guidance += "These restrictions ensure the best possible visualization during your procedure."
            return guidance
        
        elif rules.category == "surgery" and rules.fasting_hours >= 8:
            guidance = "DAY BEFORE SURGERY:\n\n"
            guidance += "• Eat light, easily digestible meals\n"
            guidance += "• Avoid heavy, fatty, or spicy foods\n"
            guidance += "• Stay well hydrated until fasting begins\n"
            guidance += "• Avoid alcohol\n\n"
            guidance += "These guidelines help reduce complications and promote faster recovery."
            return guidance
        
        # No special diet guidance for other categories
        return None
    
    def _build_medication_instructions(self, data: Dict, rules: PrepRules) -> str:
        """Build medication instructions section."""
        instructions = rules.medication_instructions + "\n\n"
        
        instructions += "IMPORTANT REMINDERS:\n\n"
        instructions += "• Bring a complete list of all medications you currently take\n"
        instructions += "• Include prescription medications, over-the-counter drugs, vitamins, and supplements\n"
        instructions += "• Note any medication allergies\n\n"
        
        if rules.category in ["surgery", "endoscopy"]:
            instructions += "SPECIAL INSTRUCTIONS:\n\n"
            instructions += "• Blood thinners: Your clinician will provide specific instructions\n"
            instructions += "• Diabetes medications: May need adjustment on procedure day\n"
            instructions += "• Blood pressure medications: Usually taken with small sip of water\n\n"
            instructions += "⚠️ If you have questions about any medication, contact your clinician BEFORE your appointment."
        else:
            instructions += "If you have questions about your medications, please contact your clinician before your appointment."
        
        return instructions
    
    def _build_arrival_instructions(self, data: Dict, rules: PrepRules) -> str:
        """Build arrival instructions section."""
        apt_datetime = self._parse_datetime(data.get("appointment_datetime"))
        arrival_time = apt_datetime - timedelta(minutes=rules.arrival_minutes_early)
        
        instructions = f"Please arrive at {arrival_time.strftime('%I:%M %p')} "
        instructions += f"({rules.arrival_minutes_early} minutes before your scheduled appointment).\n\n"
        
        instructions += "WHAT TO EXPECT:\n\n"
        instructions += "• Check in at the reception desk\n"
        instructions += "• Complete any remaining paperwork\n"
        instructions += "• Verify your insurance information\n"
        
        if rules.category in ["surgery", "endoscopy"]:
            instructions += "• Change into a gown if required\n"
            instructions += "• Meet with clinical staff for pre-procedure assessment\n"
        
        instructions += "\nArriving on time helps us stay on schedule and provide the best care for all patients."
        
        return instructions
    
    def _build_transport_instructions(self, rules: PrepRules) -> Optional[str]:
        """Build transportation instructions section."""
        if not rules.requires_responsible_adult:
            return None
        
        instructions = "⚠️ YOU MUST ARRANGE TRANSPORTATION\n\n"
        instructions += "Due to sedation or anesthesia, you will NOT be able to:\n\n"
        instructions += "• Drive yourself home\n"
        instructions += "• Take public transportation alone\n"
        instructions += "• Use ride-sharing services (Uber/Lyft) alone\n\n"
        instructions += "REQUIRED:\n\n"
        instructions += "• A responsible adult must drive you home\n"
        instructions += "• They must stay at the facility during your procedure\n"
        instructions += "• They must be able to assist you at home\n\n"
        instructions += "If you do not have appropriate transportation, your procedure will be rescheduled."
        
        return instructions
    
    def _build_red_flag_warnings(self, data: Dict, rules: PrepRules) -> List[str]:
        """Build red flag warnings list."""
        warnings = [
            "Fever over 101°F (38.3°C)",
            "Severe or worsening pain",
            "Difficulty breathing or chest pain",
            "Signs of infection at any surgical site",
            "Unusual or severe symptoms"
        ]
        
        # Add category-specific warnings
        if rules.category == "surgery":
            warnings.extend([
                "Excessive bleeding or drainage",
                "Swelling, redness, or warmth at incision site",
                "Inability to keep down fluids"
            ])
        
        elif rules.category == "endoscopy":
            warnings.extend([
                "Severe abdominal pain or cramping",
                "Vomiting blood or black stools",
                "Inability to complete bowel prep"
            ])
        
        # Always add this at the end
        warnings.append("Any concerns about your ability to safely prepare for your appointment")
        
        return warnings
    
    def _build_procedure_notes(self, data: Dict, rules: PrepRules) -> Optional[str]:
        """Build procedure-specific notes."""
        procedure_lower = data.get("procedure", "").lower()
        
        # Add specific notes based on procedure keywords
        if "colonoscopy" in procedure_lower:
            return "Colonoscopy is a safe, effective screening tool. The preparation is often the most challenging part, but it's essential for a successful exam. Stay near a bathroom during prep, and don't hesitate to call if you have concerns."
        
        elif "mri" in procedure_lower:
            return "MRI uses magnetic fields and radio waves - no radiation. Remove all metal objects before the scan. The machine can be loud; earplugs or headphones will be provided. Let the technician know if you feel claustrophobic."
        
        elif "ct" in procedure_lower and "contrast" in procedure_lower:
            return "CT with contrast provides detailed images. You may feel warm or have a metallic taste when contrast is injected - this is normal and passes quickly. Drink plenty of water after the scan to help flush the contrast."
        
        elif "surgery" in procedure_lower:
            return "Your surgical team will review the procedure, risks, and benefits with you. Don't hesitate to ask questions. Follow all pre-op instructions carefully to minimize risks and promote healing."
        
        # No specific notes for other procedures
        return None
    
    def _build_closing_note(self, data: Dict) -> str:
        """Build closing note section."""
        note = "We're here to help you prepare for your appointment.\n\n"
        note += "If you have any questions or concerns, or if your health status changes before your appointment, "
        note += "please contact the clinic immediately.\n\n"
        note += "These instructions are general guidelines. Your clinician may provide additional specific instructions "
        note += "that take precedence over these general recommendations.\n\n"
        note += "We look forward to seeing you and providing excellent care!"
        
        return note
    
    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse datetime string to datetime object."""
        try:
            # Try ISO format first
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            # Fallback to common format
            try:
                return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M")
            except ValueError:
                # If all else fails, return current time + 1 day
                return datetime.now() + timedelta(days=1)
