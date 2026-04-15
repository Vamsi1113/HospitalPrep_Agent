"""
FHIR Normalization Layer

Converts FHIR resources into the internal intake schema used by the system.
Maps FHIR data structures to the format expected by RulesEngine and other components.

Mappings:
- Patient → demographics (name, age, contact)
- AllergyIntolerance → allergies list
- MedicationStatement → current_medications list
- Procedure → prior_conditions/procedures
- Observation → vitals/labs (if needed)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FHIRNormalizer:
    """
    Normalizes FHIR resources to internal intake schema.
    """
    
    @staticmethod
    def normalize_patient(patient_resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert FHIR Patient resource to internal demographics format.
        
        Args:
            patient_resource: FHIR Patient resource
            
        Returns:
            Dict with patient_name, age_group, contact info
        """
        try:
            # Extract name
            name_parts = []
            if "name" in patient_resource and patient_resource["name"]:
                name_obj = patient_resource["name"][0]
                if "given" in name_obj:
                    name_parts.extend(name_obj["given"])
                if "family" in name_obj:
                    name_parts.append(name_obj["family"])
            
            patient_name = " ".join(name_parts) if name_parts else "Unknown Patient"
            
            # Calculate age group from birthDate
            age_group = None
            if "birthDate" in patient_resource:
                try:
                    birth_date = datetime.strptime(patient_resource["birthDate"], "%Y-%m-%d")
                    age = (datetime.now() - birth_date).days // 365
                    
                    if age < 30:
                        age_group = "18-30"
                    elif age < 40:
                        age_group = "30-40"
                    elif age < 50:
                        age_group = "40-50"
                    elif age < 60:
                        age_group = "50-60"
                    elif age < 70:
                        age_group = "60-70"
                    elif age < 80:
                        age_group = "70-80"
                    else:
                        age_group = "80+"
                except:
                    pass
            
            # Extract contact info
            phone = None
            email = None
            if "telecom" in patient_resource:
                for telecom in patient_resource["telecom"]:
                    if telecom.get("system") == "phone" and not phone:
                        phone = telecom.get("value")
                    elif telecom.get("system") == "email" and not email:
                        email = telecom.get("value")
            
            return {
                "patient_name": patient_name,
                "age_group": age_group,
                "phone": phone,
                "email": email,
                "gender": patient_resource.get("gender"),
                "fhir_patient_id": patient_resource.get("id")
            }
            
        except Exception as e:
            logger.error(f"Error normalizing patient resource: {e}")
            return {"patient_name": "Unknown Patient"}
    
    @staticmethod
    def normalize_allergies(allergy_resources: List[Dict[str, Any]]) -> List[str]:
        """
        Convert FHIR AllergyIntolerance resources to allergy list.
        
        Args:
            allergy_resources: List of FHIR AllergyIntolerance bundle entries
            
        Returns:
            List of allergy names
        """
        allergies = []
        
        try:
            for entry in allergy_resources:
                resource = entry.get("resource", {})
                
                # Check if active
                clinical_status = resource.get("clinicalStatus", {})
                status_code = None
                if "coding" in clinical_status and clinical_status["coding"]:
                    status_code = clinical_status["coding"][0].get("code")
                
                if status_code != "active":
                    continue
                
                # Extract allergy name
                code = resource.get("code", {})
                if "coding" in code and code["coding"]:
                    display = code["coding"][0].get("display")
                    if display:
                        allergies.append(display)
                elif "text" in code:
                    allergies.append(code["text"])
                    
        except Exception as e:
            logger.error(f"Error normalizing allergies: {e}")
        
        return allergies
    
    @staticmethod
    def normalize_medications(medication_resources: List[Dict[str, Any]]) -> List[str]:
        """
        Convert FHIR MedicationStatement resources to medication list.
        
        Args:
            medication_resources: List of FHIR MedicationStatement bundle entries
            
        Returns:
            List of medication names
        """
        medications = []
        
        try:
            for entry in medication_resources:
                resource = entry.get("resource", {})
                
                # Check if active
                if resource.get("status") != "active":
                    continue
                
                # Extract medication name
                med_name = None
                
                # Try medicationCodeableConcept
                if "medicationCodeableConcept" in resource:
                    code = resource["medicationCodeableConcept"]
                    if "coding" in code and code["coding"]:
                        med_name = code["coding"][0].get("display")
                    elif "text" in code:
                        med_name = code["text"]
                
                # Try medicationReference
                elif "medicationReference" in resource:
                    ref = resource["medicationReference"]
                    if "display" in ref:
                        med_name = ref["display"]
                
                if med_name:
                    medications.append(med_name)
                    
        except Exception as e:
            logger.error(f"Error normalizing medications: {e}")
        
        return medications
    
    @staticmethod
    def normalize_procedures(procedure_resources: List[Dict[str, Any]]) -> List[str]:
        """
        Convert FHIR Procedure resources to prior conditions/procedures list.
        
        Args:
            procedure_resources: List of FHIR Procedure bundle entries
            
        Returns:
            List of procedure names
        """
        procedures = []
        
        try:
            for entry in procedure_resources:
                resource = entry.get("resource", {})
                
                # Check if completed
                if resource.get("status") != "completed":
                    continue
                
                # Extract procedure name
                code = resource.get("code", {})
                if "coding" in code and code["coding"]:
                    display = code["coding"][0].get("display")
                    if display:
                        procedures.append(display)
                elif "text" in code:
                    procedures.append(code["text"])
                    
        except Exception as e:
            logger.error(f"Error normalizing procedures: {e}")
        
        return procedures
    
    @staticmethod
    def normalize_observations(observation_resources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convert FHIR Observation resources to vitals/labs dict.
        
        Args:
            observation_resources: List of FHIR Observation bundle entries
            
        Returns:
            Dict with vital signs and lab values
        """
        vitals = {}
        
        try:
            for entry in observation_resources:
                resource = entry.get("resource", {})
                
                # Check if final
                if resource.get("status") != "final":
                    continue
                
                # Extract observation code
                code = resource.get("code", {})
                code_value = None
                code_display = None
                
                if "coding" in code and code["coding"]:
                    code_value = code["coding"][0].get("code")
                    code_display = code["coding"][0].get("display")
                
                # Extract value
                value = None
                if "valueQuantity" in resource:
                    value = resource["valueQuantity"].get("value")
                    unit = resource["valueQuantity"].get("unit", "")
                    value = f"{value} {unit}".strip()
                elif "valueString" in resource:
                    value = resource["valueString"]
                elif "component" in resource:
                    # Handle multi-component observations (e.g., blood pressure)
                    components = []
                    for comp in resource["component"]:
                        comp_code = comp.get("code", {})
                        comp_display = None
                        if "coding" in comp_code and comp_code["coding"]:
                            comp_display = comp_code["coding"][0].get("display")
                        
                        comp_value = None
                        if "valueQuantity" in comp:
                            comp_value = comp["valueQuantity"].get("value")
                            comp_unit = comp["valueQuantity"].get("unit", "")
                            comp_value = f"{comp_value} {comp_unit}".strip()
                        
                        if comp_display and comp_value:
                            components.append(f"{comp_display}: {comp_value}")
                    
                    if components:
                        value = ", ".join(components)
                
                if code_display and value:
                    vitals[code_display] = value
                    
        except Exception as e:
            logger.error(f"Error normalizing observations: {e}")
        
        return vitals
    
    @staticmethod
    def fhir_to_intake(
        patient_resource: Optional[Dict[str, Any]] = None,
        allergy_resources: Optional[List[Dict[str, Any]]] = None,
        medication_resources: Optional[List[Dict[str, Any]]] = None,
        procedure_resources: Optional[List[Dict[str, Any]]] = None,
        observation_resources: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Convert complete FHIR data set to internal intake schema.
        
        Args:
            patient_resource: FHIR Patient resource
            allergy_resources: List of AllergyIntolerance resources
            medication_resources: List of MedicationStatement resources
            procedure_resources: List of Procedure resources
            observation_resources: List of Observation resources
            
        Returns:
            Complete intake dict ready for RulesEngine
        """
        intake = {}
        
        # Normalize patient demographics
        if patient_resource:
            patient_data = FHIRNormalizer.normalize_patient(patient_resource)
            intake.update(patient_data)
        
        # Normalize allergies
        if allergy_resources:
            intake["allergies"] = FHIRNormalizer.normalize_allergies(allergy_resources)
        else:
            intake["allergies"] = []
        
        # Normalize medications
        if medication_resources:
            intake["current_medications"] = FHIRNormalizer.normalize_medications(medication_resources)
        else:
            intake["current_medications"] = []
        
        # Normalize procedures (map to prior_conditions)
        if procedure_resources:
            intake["prior_conditions"] = FHIRNormalizer.normalize_procedures(procedure_resources)
        else:
            intake["prior_conditions"] = []
        
        # Normalize observations (vitals/labs)
        if observation_resources:
            intake["vitals"] = FHIRNormalizer.normalize_observations(observation_resources)
        else:
            intake["vitals"] = {}
        
        # Add metadata
        intake["data_source"] = "FHIR"
        intake["fhir_fetch_timestamp"] = datetime.now().isoformat()
        
        return intake
