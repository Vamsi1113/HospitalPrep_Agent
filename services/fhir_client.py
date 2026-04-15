"""
FHIR Client for EHR Integration

This module provides a client for interacting with FHIR servers (HAPI FHIR test server).
Supports SMART on FHIR OAuth2 flow for production and direct access for testing.

Key Features:
- HAPI FHIR public test server integration
- OAuth2/SMART on FHIR support for production
- Resource fetching (Patient, AllergyIntolerance, MedicationStatement, etc.)
- Mock mode for development without FHIR server
"""

from typing import Optional, Dict, List, Any
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FHIRClient:
    """
    Client for FHIR server interactions.
    
    Supports both test (HAPI FHIR) and production (SMART on FHIR) modes.
    """
    
    def __init__(self, 
                 base_url: str = "https://hapi.fhir.org/baseR4",
                 access_token: Optional[str] = None,
                 mock_mode: bool = True):
        """
        Initialize FHIR client.
        
        Args:
            base_url: FHIR server base URL (default: HAPI FHIR test server)
            access_token: OAuth2 access token for authenticated requests
            mock_mode: If True, returns mock data instead of making API calls
        """
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.mock_mode = mock_mode
        self.timeout = 10
        
    def _get_headers(self) -> Dict[str, str]:
        """Build request headers with auth if available."""
        headers = {
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch Patient resource by ID.
        
        Args:
            patient_id: FHIR Patient resource ID
            
        Returns:
            Patient resource dict or None if not found
        """
        if self.mock_mode:
            return self._mock_patient(patient_id)
        
        try:
            url = f"{self.base_url}/Patient/{patient_id}"
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Patient {patient_id} not found: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching patient {patient_id}: {e}")
            return None
    
    def get_allergies(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Fetch AllergyIntolerance resources for a patient.
        
        Args:
            patient_id: FHIR Patient resource ID
            
        Returns:
            List of AllergyIntolerance resources
        """
        if self.mock_mode:
            return self._mock_allergies(patient_id)
        
        try:
            url = f"{self.base_url}/AllergyIntolerance"
            params = {"patient": patient_id}
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            
            if response.status_code == 200:
                bundle = response.json()
                return bundle.get("entry", [])
            else:
                logger.warning(f"Allergies not found for patient {patient_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching allergies for {patient_id}: {e}")
            return []
    
    def get_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Fetch MedicationStatement resources for a patient.
        
        Args:
            patient_id: FHIR Patient resource ID
            
        Returns:
            List of MedicationStatement resources
        """
        if self.mock_mode:
            return self._mock_medications(patient_id)
        
        try:
            url = f"{self.base_url}/MedicationStatement"
            params = {"patient": patient_id, "status": "active"}
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            
            if response.status_code == 200:
                bundle = response.json()
                return bundle.get("entry", [])
            else:
                logger.warning(f"Medications not found for patient {patient_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching medications for {patient_id}: {e}")
            return []
    
    def get_procedures(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Fetch Procedure resources for a patient.
        
        Args:
            patient_id: FHIR Patient resource ID
            
        Returns:
            List of Procedure resources
        """
        if self.mock_mode:
            return self._mock_procedures(patient_id)
        
        try:
            url = f"{self.base_url}/Procedure"
            params = {"patient": patient_id}
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            
            if response.status_code == 200:
                bundle = response.json()
                return bundle.get("entry", [])
            else:
                logger.warning(f"Procedures not found for patient {patient_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching procedures for {patient_id}: {e}")
            return []
    
    def get_observations(self, patient_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch Observation resources for a patient.
        
        Args:
            patient_id: FHIR Patient resource ID
            category: Optional category filter (e.g., "vital-signs", "laboratory")
            
        Returns:
            List of Observation resources
        """
        if self.mock_mode:
            return self._mock_observations(patient_id, category)
        
        try:
            url = f"{self.base_url}/Observation"
            params = {"patient": patient_id}
            if category:
                params["category"] = category
            
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            
            if response.status_code == 200:
                bundle = response.json()
                return bundle.get("entry", [])
            else:
                logger.warning(f"Observations not found for patient {patient_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching observations for {patient_id}: {e}")
            return []
    
    # Mock data methods for development
    def _mock_patient(self, patient_id: str) -> Dict[str, Any]:
        """Return mock Patient resource."""
        return {
            "resourceType": "Patient",
            "id": patient_id,
            "name": [{"given": ["John"], "family": "Doe"}],
            "gender": "male",
            "birthDate": "1980-01-15",
            "telecom": [
                {"system": "phone", "value": "555-0123"},
                {"system": "email", "value": "john.doe@example.com"}
            ],
            "address": [{
                "line": ["123 Main St"],
                "city": "Springfield",
                "state": "IL",
                "postalCode": "62701"
            }]
        }
    
    def _mock_allergies(self, patient_id: str) -> List[Dict[str, Any]]:
        """Return mock AllergyIntolerance resources."""
        return [
            {
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "id": "allergy-1",
                    "patient": {"reference": f"Patient/{patient_id}"},
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "387207008",
                            "display": "Penicillin"
                        }]
                    },
                    "clinicalStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                            "code": "active"
                        }]
                    },
                    "reaction": [{
                        "manifestation": [{
                            "coding": [{
                                "display": "Rash"
                            }]
                        }]
                    }]
                }
            }
        ]
    
    def _mock_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        """Return mock MedicationStatement resources."""
        return [
            {
                "resource": {
                    "resourceType": "MedicationStatement",
                    "id": "med-1",
                    "status": "active",
                    "medicationCodeableConcept": {
                        "coding": [{
                            "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                            "code": "197361",
                            "display": "Lisinopril 10 MG"
                        }]
                    },
                    "subject": {"reference": f"Patient/{patient_id}"},
                    "dosage": [{
                        "text": "10mg once daily"
                    }]
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationStatement",
                    "id": "med-2",
                    "status": "active",
                    "medicationCodeableConcept": {
                        "coding": [{
                            "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                            "code": "83367",
                            "display": "Metformin 500 MG"
                        }]
                    },
                    "subject": {"reference": f"Patient/{patient_id}"},
                    "dosage": [{
                        "text": "500mg twice daily"
                    }]
                }
            }
        ]
    
    def _mock_procedures(self, patient_id: str) -> List[Dict[str, Any]]:
        """Return mock Procedure resources."""
        return [
            {
                "resource": {
                    "resourceType": "Procedure",
                    "id": "proc-1",
                    "status": "completed",
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "80146002",
                            "display": "Appendectomy"
                        }]
                    },
                    "subject": {"reference": f"Patient/{patient_id}"},
                    "performedDateTime": "2019-03-15"
                }
            }
        ]
    
    def _mock_observations(self, patient_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return mock Observation resources."""
        return [
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-1",
                    "status": "final",
                    "category": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs"
                        }]
                    }],
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "85354-9",
                            "display": "Blood pressure"
                        }]
                    },
                    "subject": {"reference": f"Patient/{patient_id}"},
                    "effectiveDateTime": datetime.now().isoformat(),
                    "component": [
                        {
                            "code": {"coding": [{"code": "8480-6", "display": "Systolic"}]},
                            "valueQuantity": {"value": 120, "unit": "mmHg"}
                        },
                        {
                            "code": {"coding": [{"code": "8462-4", "display": "Diastolic"}]},
                            "valueQuantity": {"value": 80, "unit": "mmHg"}
                        }
                    ]
                }
            }
        ]
