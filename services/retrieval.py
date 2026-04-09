"""
Protocol Retrieval Service for RAG (Retrieval-Augmented Generation).

This module provides retrieval of clinic-specific protocols, prep instructions,
and policy documents from a local knowledge base.
"""

from typing import List, Dict, Optional, Any
import os
import json
import logging

logger = logging.getLogger(__name__)


class ProtocolRetrieval:
    """
    Retrieves clinic protocols and prep instructions.
    
    This service provides RAG capabilities for grounding agent outputs
    in actual clinic policies and procedures. It uses a simple file-based
    retrieval system that can be upgraded to vector search later.
    """
    
    def __init__(self, protocols_dir: str = "data/protocols"):
        """
        Initialize protocol retrieval service.
        
        Args:
            protocols_dir: Directory containing protocol documents
        """
        self.protocols_dir = protocols_dir
        self.protocols_cache = {}
        self._load_protocols()
    
    def _load_protocols(self):
        """Load all protocol documents into memory."""
        if not os.path.exists(self.protocols_dir):
            logger.warning(f"Protocols directory not found: {self.protocols_dir}")
            return
        
        try:
            for filename in os.listdir(self.protocols_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.protocols_dir, filename)
                    with open(filepath, 'r') as f:
                        protocol_data = json.load(f)
                        protocol_id = filename.replace('.json', '')
                        self.protocols_cache[protocol_id] = protocol_data
            
            logger.info(f"Loaded {len(self.protocols_cache)} protocol documents")
        except Exception as e:
            logger.error(f"Error loading protocols: {e}")
    
    def retrieve_protocols(
        self,
        appointment_type: str,
        procedure: str,
        specialty: Optional[str] = None,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant protocols for an appointment.
        
        Args:
            appointment_type: Type of appointment
            procedure: Specific procedure
            specialty: Medical specialty (optional)
            max_results: Maximum number of protocols to return
        
        Returns:
            List of relevant protocol documents
        """
        if not self.protocols_cache:
            logger.warning("No protocols loaded, using fallback")
            return self._get_fallback_protocols(appointment_type, procedure)
        
        # Simple keyword matching (can be upgraded to vector search)
        relevant_protocols = []
        
        search_terms = [
            appointment_type.lower(),
            procedure.lower()
        ]
        if specialty:
            search_terms.append(specialty.lower())
        
        for protocol_id, protocol_data in self.protocols_cache.items():
            # Check if any search term matches protocol keywords
            protocol_keywords = protocol_data.get('keywords', [])
            protocol_type = protocol_data.get('type', '').lower()
            protocol_procedure = protocol_data.get('procedure', '').lower()
            
            score = 0
            for term in search_terms:
                if term in protocol_type:
                    score += 3
                if term in protocol_procedure:
                    score += 3
                if any(term in keyword.lower() for keyword in protocol_keywords):
                    score += 1
            
            if score > 0:
                relevant_protocols.append({
                    'id': protocol_id,
                    'score': score,
                    'data': protocol_data
                })
        
        # Sort by relevance score
        relevant_protocols.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top results
        return [p['data'] for p in relevant_protocols[:max_results]]
    
    def _get_fallback_protocols(
        self,
        appointment_type: str,
        procedure: str
    ) -> List[Dict[str, Any]]:
        """
        Fallback protocols when no documents are loaded.
        
        Returns basic, safe protocols based on appointment type.
        """
        fallback = {
            'id': 'fallback',
            'type': appointment_type,
            'procedure': procedure,
            'instructions': {
                'general': [
                    "Bring photo ID and insurance card",
                    "Arrive 15 minutes before your appointment",
                    "Bring a list of current medications",
                    "Bring a list of allergies"
                ],
                'fasting': None,
                'transport': None,
                'paperwork': [
                    "Complete any forms sent to you in advance",
                    "Bring referral if required by your insurance"
                ]
            },
            'source': 'fallback_rules'
        }
        
        # Add procedure-specific fallback rules
        proc_lower = procedure.lower()
        
        if 'surgery' in proc_lower:
            fallback['instructions']['fasting'] = "Do not eat or drink for 8 hours before surgery"
            fallback['instructions']['transport'] = "Arrange for someone to drive you home"
        
        elif 'colonoscopy' in proc_lower or 'endoscopy' in proc_lower:
            fallback['instructions']['fasting'] = "Follow bowel prep instructions provided"
            fallback['instructions']['transport'] = "Arrange for someone to drive you home"
        
        elif 'mri' in proc_lower or 'ct' in proc_lower:
            if 'contrast' in proc_lower:
                fallback['instructions']['fasting'] = "Do not eat for 4 hours before scan"
        
        return [fallback]
    
    def get_fasting_protocol(self, procedure: str) -> Optional[Dict[str, Any]]:
        """
        Get fasting protocol for a specific procedure.
        
        Args:
            procedure: Procedure name
        
        Returns:
            Fasting protocol or None
        """
        protocols = self.retrieve_protocols('procedure', procedure)
        
        for protocol in protocols:
            if 'fasting' in protocol.get('instructions', {}):
                return protocol.get('instructions', {}).get('fasting')
        
        return None
    
    def get_transport_protocol(self, procedure: str) -> Optional[Dict[str, Any]]:
        """
        Get transport/escort protocol for a specific procedure.
        
        Args:
            procedure: Procedure name
        
        Returns:
            Transport protocol or None
        """
        protocols = self.retrieve_protocols('procedure', procedure)
        
        for protocol in protocols:
            if 'transport' in protocol.get('instructions', {}):
                return protocol.get('instructions', {}).get('transport')
        
        return None
    
    def is_available(self) -> bool:
        """Check if retrieval service is available."""
        return len(self.protocols_cache) > 0
