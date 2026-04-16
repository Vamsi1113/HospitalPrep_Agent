"""
Hospital Lookup Service

Provides hospital search and ranking using Geoapify Places API (primary)
with fallback to mock data. Supports real-time hospital data from OpenStreetMap
with ratings, contact info, and location.

Geoapify is built on OpenStreetMap and provides:
- 500+ place categories including hospitals
- Location-based search with radius
- Structured JSON data
- Production-ready API
- Free tier: ~3000 requests/day
"""

import logging
import os
import requests
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
        self.geoapify_api_key = os.getenv('GEOAPIFY_API_KEY', '')
        self.use_real_api = bool(self.geoapify_api_key) and not mock_mode
        logger.info(f"HospitalLookupService initialized (mock_mode={mock_mode}, real_api={self.use_real_api})")
    
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
        if self.use_real_api and location:
            return self.search_real_hospitals(location[0], location[1], procedure, int(radius_km * 1000))
        
        return self._mock_search_hospitals(procedure, location)
    
    def search_real_hospitals(
        self,
        lat: float,
        lng: float,
        specialty: Optional[str] = None,
        radius: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Search for real hospitals using Geoapify Places API.
        
        Args:
            lat: Latitude
            lng: Longitude
            specialty: Optional specialty keyword (e.g., "cardiology")
            radius: Search radius in meters (default 10km)
        
        Returns:
            List of hospital dicts with real data from OpenStreetMap
        """
        logger.info(f"[GEOAPIFY API] Searching hospitals near ({lat}, {lng}) radius={radius}m")
        
        try:
            # Geoapify Places API - search for hospitals
            places_url = "https://api.geoapify.com/v2/places"
            
            # Build categories - Geoapify uses specific healthcare categories
            categories = "healthcare.hospital"
            if specialty:
                # Map specialties to additional categories if needed
                specialty_lower = specialty.lower()
                if "cardio" in specialty_lower:
                    categories += ",healthcare.clinic_or_praxis"
            
            # Geoapify expects: circle:longitude,latitude,radius (radius as integer)
            params = {
                "categories": categories,
                "filter": f"circle:{lng},{lat},{int(radius)}",
                "bias": f"proximity:{lng},{lat}",
                "limit": 20,
                "apiKey": self.geoapify_api_key
            }
            
            logger.info(f"[GEOAPIFY API] Request params: filter=circle:{lng},{lat},{int(radius)}")
            
            logger.info(f"[GEOAPIFY API] Calling Geoapify Places API with categories={categories}")
            
            response = requests.get(places_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            features = data.get("features", [])
            
            logger.info(f"[GEOAPIFY API] Received {len(features)} results from Geoapify")
            
            if not features:
                logger.warning("[GEOAPIFY API] No hospitals found, falling back to mock data")
                return self._mock_search_hospitals(specialty or "", (lat, lng))
            
            hospitals = []
            
            for feature in features[:10]:  # Limit to top 10
                props = feature.get("properties", {})
                coords = feature.get("geometry", {}).get("coordinates", [lng, lat])
                
                # Extract hospital data from Geoapify response
                hospital_lat = coords[1] if len(coords) > 1 else lat
                hospital_lng = coords[0] if len(coords) > 0 else lng
                
                hospital = {
                    "id": props.get("place_id", f"geo_{len(hospitals)}"),
                    "name": props.get("name", props.get("address_line1", "Unknown Hospital")),
                    "address": props.get("formatted", props.get("address_line2", "")),
                    "rating": 0.0,  # Geoapify doesn't provide ratings, use default
                    "total_reviews": 0,
                    "phone": props.get("contact", {}).get("phone", ""),
                    "website": props.get("website", props.get("contact", {}).get("website", "")),
                    "latitude": hospital_lat,
                    "longitude": hospital_lng,
                    "open_now": None,  # Can be derived from opening_hours if available
                    "location": props.get("city", props.get("suburb", "")),
                    "distance_km": self.haversine_distance(
                        (lat, lng),
                        (hospital_lat, hospital_lng)
                    ),
                    "capabilities": [specialty] if specialty else [],
                    "datasource": props.get("datasource", {}).get("sourcename", "OpenStreetMap"),
                    "doctors": self._generate_mock_doctors_for_hospital(
                        props.get("name", "Hospital"),
                        specialty or "General"
                    )
                }
                
                # Add rating based on distance (closer = better for OSM data without ratings)
                # This is a heuristic since OSM doesn't have user ratings
                hospital["rating"] = max(3.5, 5.0 - (hospital["distance_km"] / 10.0))
                hospital["rating"] = min(5.0, hospital["rating"])  # Cap at 5.0
                hospital["rating"] = round(hospital["rating"], 1)
                
                hospitals.append(hospital)
            
            # Rank hospitals
            ranked = self.rank_hospitals(hospitals)
            logger.info(f"[GEOAPIFY API] Successfully ranked {len(ranked)} real hospitals")
            
            return ranked
            
        except requests.RequestException as e:
            logger.error(f"[GEOAPIFY API] Request error: {e}, falling back to mock data")
            return self._mock_search_hospitals(specialty or "", (lat, lng))
        except Exception as e:
            logger.error(f"[GEOAPIFY API] Unexpected error: {e}, falling back to mock data")
            return self._mock_search_hospitals(specialty or "", (lat, lng))
    
    def _generate_mock_doctors_for_hospital(
        self,
        hospital_name: str,
        specialty: str
    ) -> List[Dict[str, Any]]:
        """Generate mock doctors for a real hospital."""
        from datetime import datetime, timedelta
        
        # Generate 1-2 mock doctors per hospital
        doctors = []
        base_date = datetime.now() + timedelta(days=1)
        
        doctor_names = [
            ("Dr. Rajesh Kumar", "RK"),
            ("Dr. Priya Sharma", "PS"),
            ("Dr. Amit Patel", "AP")
        ]
        
        for i, (name, initial) in enumerate(doctor_names[:2]):
            slots = []
            for day in range(2):
                for hour in [9, 14]:
                    slot_time = base_date + timedelta(days=day, hours=hour)
                    slots.append({
                        "slot_id": f"slot_{i}_{day}_{hour}",
                        "datetime_display": slot_time.strftime("%b %d, %Y at %I:%M %p"),
                        "datetime_iso": slot_time.isoformat(),
                        "duration": "30 min",
                        "location": hospital_name,
                        "available": True
                    })
            
            doctors.append({
                "id": f"dr_{i}_{hospital_name[:10]}",
                "name": name,
                "specialty": specialty.capitalize() if specialty else "General Physician",
                "rating": round(4.5 + (i * 0.2), 1),
                "experience": f"{10 + i * 2} years",
                "hospital": hospital_name,
                "hospital_location": hospital_name,
                "hospital_rating": 4.5,
                "image_initial": initial,
                "slots": slots
            })
        
        return doctors
    
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
