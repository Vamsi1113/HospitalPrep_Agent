"""
Hospital Lookup Service

Provides hospital search and ranking using Overpass API and Nominatim.
Supports mock mode for testing without external API calls.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from math import radians, sin, cos, sqrt, atan2

logger = logging.getLogger(__name__)


class HospitalLookupService:
    """Service for finding and ranking hospitals based on procedure and location."""
    
    def __init__(self, mock_mode: bool = True):
        """
        Initialize Hospital Lookup Service.
        
        Args:
            mock_mode: If True, return mock data without calling external APIs
        """
        self.mock_mode = mock_mode
        logger.info(f"HospitalLookupService initialized (mock_mode={mock_mode})")
    
    def search_hospitals(
        self,
        procedure: str,
        location: Optional[Tuple[float, float]] = None,
        radius_km: float = 25.0
    ) -> List[Dict[str, Any]]:
        """
        Search for hospitals suitable for the given procedure.
        
        Args:
            procedure: Procedure type (e.g., "Cardiac evaluation", "MRI")
            location: (latitude, longitude) tuple, defaults to mock location
            radius_km: Search radius in kilometers
        
        Returns:
            List of hospital dicts with name, location, rating, distance, etc.
        """
        if self.mock_mode:
            return self._mock_search_hospitals(procedure, location)
        
        # TODO: Implement real Overpass API and Nominatim integration
        logger.warning("Real API not implemented yet, using mock data")
        return self._mock_search_hospitals(procedure, location)
    
    def rank_hospitals(self, hospitals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank hospitals by weighted score (70% rating, 30% distance).
        
        Args:
            hospitals: List of hospital dicts with rating and distance_km
        
        Returns:
            Sorted list of hospitals with score field added
        """
        for hospital in hospitals:
            # Normalize rating (0-5 scale)
            rating_score = hospital.get("rating", 0.0) / 5.0
            
            # Normalize distance (inverse, max 50km)
            distance_km = hospital.get("distance_km", 0.0)
            distance_score = 1.0 - min(distance_km / 50.0, 1.0)
            
            # Weighted score: 70% rating, 30% distance
            hospital["score"] = 0.7 * rating_score + 0.3 * distance_score
        
        # Sort by score descending
        return sorted(hospitals, key=lambda h: h.get("score", 0.0), reverse=True)
    
    def filter_by_capability(
        self,
        hospitals: List[Dict[str, Any]],
        procedure: str
    ) -> List[Dict[str, Any]]:
        """
        Filter hospitals by procedure capability.
        
        Args:
            hospitals: List of hospital dicts
            procedure: Procedure type
        
        Returns:
            Filtered list of hospitals with required capability
        """
        # Map procedures to required capabilities
        procedure_lower = procedure.lower()
        required_capability = None
        
        if any(term in procedure_lower for term in ["cardiac", "heart", "chest"]):
            required_capability = "cardiology"
        elif any(term in procedure_lower for term in ["surgery", "surgical"]):
            required_capability = "surgery"
        elif any(term in procedure_lower for term in ["mri", "ct", "x-ray", "imaging", "scan"]):
            required_capability = "imaging"
        elif any(term in procedure_lower for term in ["endoscopy", "colonoscopy"]):
            required_capability = "endoscopy"
        
        if not required_capability:
            return hospitals  # No filtering needed
        
        filtered = [
            h for h in hospitals
            if required_capability in h.get("capabilities", [])
        ]
        
        return filtered if filtered else hospitals  # Return all if none match
    
    def _mock_search_hospitals(
        self,
        procedure: str,
        location: Optional[Tuple[float, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Return mock hospital data for testing.
        
        Args:
            procedure: Procedure type
            location: User location (ignored in mock)
        
        Returns:
            List of mock hospitals with doctors and slots
        """
        logger.info(f"[MOCK] Searching hospitals for procedure: {procedure}")
        
        # Default location (New York City)
        if location is None:
            location = (40.7128, -74.0060)
        
        # Mock hospitals with realistic data
        mock_hospitals = [
            {
                "name": "St. Jude Premier Health",
                "location": "Downtown",
                "rating": 4.9,
                "distance_km": 2.3,
                "address": "123 Main St, New York, NY 10001",
                "phone": "555-1000",
                "capabilities": ["cardiology", "surgery", "imaging", "endoscopy"],
                "latitude": 40.7489,
                "longitude": -73.9680,
                "doctors": [
                    {
                        "id": "dr_001",
                        "name": "Dr. Sarah Johnson",
                        "specialty": "Cardiologist",
                        "rating": 4.9,
                        "experience": "15 years",
                        "hospital": "St. Jude Premier Health",
                        "hospital_location": "Downtown",
                        "hospital_rating": 4.9,
                        "image_initial": "SJ",
                        "slots": [
                            {
                                "slot_id": "dr_001_slot_0",
                                "datetime_display": "Jan 16, 2024 at 09:00 AM",
                                "datetime_iso": "2024-01-16T09:00:00",
                                "duration": "45 min",
                                "location": "Main Clinic",
                                "available": True
                            },
                            {
                                "slot_id": "dr_001_slot_1",
                                "datetime_display": "Jan 16, 2024 at 02:00 PM",
                                "datetime_iso": "2024-01-16T14:00:00",
                                "duration": "45 min",
                                "location": "Main Clinic",
                                "available": True
                            },
                            {
                                "slot_id": "dr_001_slot_2",
                                "datetime_display": "Jan 17, 2024 at 10:30 AM",
                                "datetime_iso": "2024-01-17T10:30:00",
                                "duration": "45 min",
                                "location": "Main Clinic",
                                "available": True
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Metropolitan Medical Center",
                "location": "Midtown",
                "rating": 4.7,
                "distance_km": 5.1,
                "address": "456 Park Ave, New York, NY 10022",
                "phone": "555-2000",
                "capabilities": ["cardiology", "imaging", "surgery"],
                "latitude": 40.7614,
                "longitude": -73.9776,
                "doctors": [
                    {
                        "id": "dr_002",
                        "name": "Dr. Michael Chen",
                        "specialty": "Cardiologist",
                        "rating": 4.8,
                        "experience": "12 years",
                        "hospital": "Metropolitan Medical Center",
                        "hospital_location": "Midtown",
                        "hospital_rating": 4.7,
                        "image_initial": "MC",
                        "slots": [
                            {
                                "slot_id": "dr_002_slot_0",
                                "datetime_display": "Jan 16, 2024 at 11:00 AM",
                                "datetime_iso": "2024-01-16T11:00:00",
                                "duration": "30 min",
                                "location": "Cardiology Wing",
                                "available": True
                            },
                            {
                                "slot_id": "dr_002_slot_1",
                                "datetime_display": "Jan 17, 2024 at 09:00 AM",
                                "datetime_iso": "2024-01-17T09:00:00",
                                "duration": "30 min",
                                "location": "Cardiology Wing",
                                "available": True
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Riverside Community Hospital",
                "location": "Upper West Side",
                "rating": 4.5,
                "distance_km": 8.7,
                "address": "789 Riverside Dr, New York, NY 10032",
                "phone": "555-3000",
                "capabilities": ["imaging", "surgery", "endoscopy"],
                "latitude": 40.8448,
                "longitude": -73.9421,
                "doctors": [
                    {
                        "id": "dr_003",
                        "name": "Dr. Emily Rodriguez",
                        "specialty": "Internal Medicine",
                        "rating": 4.6,
                        "experience": "10 years",
                        "hospital": "Riverside Community Hospital",
                        "hospital_location": "Upper West Side",
                        "hospital_rating": 4.5,
                        "image_initial": "ER",
                        "slots": [
                            {
                                "slot_id": "dr_003_slot_0",
                                "datetime_display": "Jan 16, 2024 at 03:00 PM",
                                "datetime_iso": "2024-01-16T15:00:00",
                                "duration": "30 min",
                                "location": "General Medicine",
                                "available": True
                            }
                        ]
                    }
                ]
            }
        ]
        
        # Calculate distances from user location
        for hospital in mock_hospitals:
            hospital_coords = (hospital["latitude"], hospital["longitude"])
            hospital["distance_km"] = self.haversine_distance(location, hospital_coords)
        
        # Filter by capability
        filtered_hospitals = self.filter_by_capability(mock_hospitals, procedure)
        
        # Rank hospitals
        ranked_hospitals = self.rank_hospitals(filtered_hospitals)
        
        return ranked_hospitals
    
    @staticmethod
    def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """
        Calculate distance between two coordinates in kilometers using Haversine formula.
        
        Args:
            coord1: (latitude, longitude) tuple
            coord2: (latitude, longitude) tuple
        
        Returns:
            Distance in kilometers
        """
        lat1, lon1 = radians(coord1[0]), radians(coord1[1])
        lat2, lon2 = radians(coord2[0]), radians(coord2[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        radius_earth_km = 6371.0
        return radius_earth_km * c
