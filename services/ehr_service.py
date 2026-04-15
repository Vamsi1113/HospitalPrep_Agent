"""
EHR Service - High-level interface for EHR/FHIR integration

Combines FHIR client and normalization layer to provide a clean interface
for fetching and normalizing patient data from EHR systems.

Usage:
    ehr = EHRService(mock_mode=True)
    intake_data = ehr.fetch_patient_data(patient_id="12345")
"""

from typing import Optional, Dict, Any
import logging
from services.fhir_client import FHIRClient
from services.fhir_normalizer import FHIRNormalizer

logger = logging.getLogger(__name__)


class EHRService:
    """
    High-level EHR service combining FHIR client and normalization.
    """
    
    def __init__(self,
                 fhir_base_url: str = "https://hapi.fhir.org/baseR4",
                 access_token: Optional[str] = None,
                 mock_mode: bool = True):
        """
        Initialize EHR service.
        
        Args:
            fhir_base_url: FHIR server base URL
            access_token: OAuth2 access token for authenticated requests
            mock_mode: If True, uses mock data instead of real API calls
        """
        self.fhir_client = FHIRClient(
            base_url=fhir_base_url,
            access_token=access_token,
            mock_mode=mock_mode
        )
        self.normalizer = FHIRNormalizer()
        self.mock_mode = mock_mode
    
    def is_available(self) -> bool:
        """Check if EHR service is available."""
        return True  # Always available in mock mode
    
    def fetch_patient_data(self, patient_id: str) -> Dict[str, Any]:
        """
        Fetch and normalize complete patient data from FHIR server.
        
        This is the main entry point for getting patient data from EHR.
        It fetches all relevant FHIR resources and normalizes them into
        the internal intake schema.
        
        Args:
            patient_id: FHIR Patient resource ID
            
        Returns:
            Normalized intake dict with patient demographics, allergies,
            medications, procedures, and vitals
        """
        try:
            logger.info(f"Fetching patient data for ID: {patient_id}")
            
            # Fetch FHIR resources
            patient = self.fhir_client.get_patient(patient_id)
            allergies = self.fhir_client.get_allergies(patient_id)
            medications = self.fhir_client.get_medications(patient_id)
            procedures = self.fhir_client.get_procedures(patient_id)
            observations = self.fhir_client.get_observations(patient_id, category="vital-signs")
            
            # Normalize to internal schema
            intake_data = self.normalizer.fhir_to_intake(
                patient_resource=patient,
                allergy_resources=allergies,
                medication_resources=medications,
                procedure_resources=procedures,
                observation_resources=observations
            )
            
            logger.info(f"Successfully fetched and normalized data for patient {patient_id}")
            return intake_data
            
        except Exception as e:
            logger.error(f"Error fetching patient data for {patient_id}: {e}")
            return {
                "patient_name": "Unknown Patient",
                "allergies": [],
                "current_medications": [],
                "prior_conditions": [],
                "vitals": {},
                "data_source": "FHIR",
                "error": str(e)
            }
    
    def search_patients(self, 
                       family_name: Optional[str] = None,
                       given_name: Optional[str] = None,
                       birthdate: Optional[str] = None) -> list:
        """
        Search for patients by demographics.
        
        Args:
            family_name: Patient family name
            given_name: Patient given name
            birthdate: Patient birth date (YYYY-MM-DD)
            
        Returns:
            List of matching patient resources
        """
        if self.mock_mode:
            # Return mock search results
            return [{
                "resource": self.fhir_client._mock_patient("mock-patient-1")
            }]
        
        try:
            import requests
            url = f"{self.fhir_client.base_url}/Patient"
            params = {}
            
            if family_name:
                params["family"] = family_name
            if given_name:
                params["given"] = given_name
            if birthdate:
                params["birthdate"] = birthdate
            
            response = requests.get(
                url,
                params=params,
                headers=self.fhir_client._get_headers(),
                timeout=self.fhir_client.timeout
            )
            
            if response.status_code == 200:
                bundle = response.json()
                return bundle.get("entry", [])
            else:
                logger.warning(f"Patient search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching patients: {e}")
            return []
    
    def enrich_intake(self, existing_intake: Dict[str, Any], patient_id: str) -> Dict[str, Any]:
        """
        Enrich existing intake data with FHIR data.
        
        Merges manually entered intake data with data from EHR,
        preferring EHR data for structured fields (allergies, medications)
        and keeping manual data for subjective fields (symptoms, complaints).
        
        Args:
            existing_intake: Manually entered intake data
            patient_id: FHIR Patient ID to fetch data from
            
        Returns:
            Enriched intake dict combining both sources
        """
        try:
            # Fetch FHIR data
            fhir_data = self.fetch_patient_data(patient_id)
            
            # Merge data - FHIR takes precedence for structured data
            enriched = existing_intake.copy()
            
            # Use FHIR data for structured fields
            if fhir_data.get("patient_name"):
                enriched["patient_name"] = fhir_data["patient_name"]
            
            if fhir_data.get("age_group"):
                enriched["age_group"] = fhir_data["age_group"]
            
            # Merge allergies (combine both sources, deduplicate)
            fhir_allergies = set(fhir_data.get("allergies", []))
            manual_allergies = set(existing_intake.get("allergies", []))
            enriched["allergies"] = list(fhir_allergies | manual_allergies)
            
            # Merge medications
            fhir_meds = set(fhir_data.get("current_medications", []))
            manual_meds = set(existing_intake.get("current_medications", []))
            enriched["current_medications"] = list(fhir_meds | manual_meds)
            
            # Merge prior conditions
            fhir_conditions = set(fhir_data.get("prior_conditions", []))
            manual_conditions = set(existing_intake.get("prior_conditions", []))
            enriched["prior_conditions"] = list(fhir_conditions | manual_conditions)
            
            # Add vitals from FHIR
            if fhir_data.get("vitals"):
                enriched["vitals"] = fhir_data["vitals"]
            
            # Add metadata
            enriched["data_source"] = "FHIR+Manual"
            enriched["fhir_patient_id"] = patient_id
            
            logger.info(f"Successfully enriched intake with FHIR data for patient {patient_id}")
            return enriched
            
        except Exception as e:
            logger.error(f"Error enriching intake with FHIR data: {e}")
            # Return original intake if enrichment fails
            return existing_intake
