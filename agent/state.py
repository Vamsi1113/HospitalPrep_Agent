"""
Agent State Definition for LangGraph-based Appointment Prep Agent.

This module defines the state structure that flows through the agent graph.
Each node in the graph reads from and writes to this state.

THREE-PHASE WORKFLOW:
- Phase I: Triage & Intake (symptom capture, follow-up questions)
- Phase II: Admin Prep (logistics, insurance, documents)
- Phase III: Clinical Briefing (EHR summary, clinician notes)
"""

from typing import TypedDict, Optional, List, Dict, Any


class IntakeData(TypedDict):
    """Structured intake data from Phase I."""
    chief_complaint: str
    chief_complaint_normalized: Optional[str]
    symptoms: List[Dict[str, Any]]  # [{name, onset, duration, severity, triggers}]
    current_medications: List[str]
    allergies: List[str]
    age_group: Optional[str]
    pregnancy_flag: bool
    prior_conditions: List[str]
    needs_clarification: bool
    follow_up_questions: List[str]


class TriageData(TypedDict):
    """Triage classification from Phase I."""
    urgency_level: str  # "routine", "urgent", "emergency"
    red_flags: List[str]
    prep_complexity: str  # "simple", "moderate", "complex"
    requires_human_review: bool
    prep_flow_type: str  # "standard", "procedure", "specialty"


class AdminPrepData(TypedDict):
    """Admin/logistics preparation from Phase II."""
    insurance_verification_needed: bool
    copay_reminder: Optional[str]
    required_documents: List[str]
    arrival_instructions: str
    transport_instructions: Optional[str]
    fasting_instructions: Optional[str]
    diet_instructions: Optional[str]
    paperwork_reminders: List[str]
    reschedule_warnings: List[str]
    patient_readiness_checklist: List[str]


class ClinicalBriefingData(TypedDict):
    """Clinical briefing for staff/doctor from Phase III."""
    relevant_history: str
    medication_conflicts: List[str]
    allergy_alerts: List[str]
    missing_labs: List[str]
    missing_records: List[str]
    care_gaps: List[str]
    follow_up_items: List[str]
    prep_status: str
    key_risks: List[str]


class PrepPlanSections(TypedDict):
    """Structured preparation plan sections for patient."""
    appointment_summary: str
    symptom_clarification: Optional[str]
    fasting_plan: Optional[str]
    diet_guidance: Optional[str]
    medication_instructions: str
    items_to_bring: List[str]
    arrival_instructions: str
    transport_instructions: Optional[str]
    red_flag_warnings: List[str]
    procedure_specific_notes: Optional[str]
    closing_note: str


class AgentState(TypedDict):
    """
    State object that flows through the LangGraph agent.
    
    This state is passed between nodes and accumulates information
    as the agent progresses through its THREE-PHASE workflow.
    
    PHASE I: TRIAGE & INTAKE
        - raw_intake: User's initial input
        - intake_data: Structured intake with normalized symptoms
        - triage_data: Urgency classification and red flags
    
    PHASE II: ADMIN PREP
        - admin_prep_data: Logistics and administrative instructions
        - retrieved_protocols: Clinic protocols from RAG
    
    PHASE III: CLINICAL BRIEFING
        - ehr_context: Patient history and records
        - clinical_briefing: Doctor-facing summary
    
    OUTPUTS:
        - patient_message: Patient-facing prep instructions
        - clinician_summary: Clinician-facing briefing
        - prep_sections: Structured patient prep sections
    
    METADATA:
        - errors: Error messages
        - reasoning_trace: Step-by-step agent reasoning
        - metadata: Timestamps and execution info
        - llm_used: Whether LLM was used
        - saved_record_id: Database ID
    """
    # Phase I: Triage & Intake
    raw_intake: Dict[str, Any]
    intake_data: Optional[IntakeData]
    triage_data: Optional[TriageData]
    
    # Phase II: Admin Prep
    admin_prep_data: Optional[AdminPrepData]
    retrieved_protocols: Optional[List[Dict[str, Any]]]
    
    # Phase III: Clinical Briefing
    ehr_context: Optional[Dict[str, Any]]
    clinical_briefing: Optional[ClinicalBriefingData]
    
    # Legacy fields (for backward compatibility)
    input_data: Dict[str, Any]
    validated_data: Optional[Dict[str, Any]]
    rules_output: Optional[Any]
    
    # Output generation
    prep_sections: Optional[PrepPlanSections]
    patient_message: Optional[str]
    clinician_summary: Optional[str]
    draft_message: Optional[str]
    final_message: Optional[str]
    preview: Optional[str]
    rules_explanation: Optional[List[Dict[str, str]]]
    
    # Error handling
    errors: List[str]
    
    # Explainability
    reasoning_trace: List[Dict[str, Any]]
    
    # Metadata and persistence
    metadata: Dict[str, Any]
    llm_used: bool
    saved_record_id: Optional[int]


def create_initial_state(raw_intake: Dict[str, Any]) -> AgentState:
    """
    Create initial agent state from user input.
    
    Args:
        raw_intake: Raw intake data from user (symptoms, complaint, demographics)
    
    Returns:
        AgentState with initialized fields
    """
    return AgentState(
        # Phase I: Triage & Intake
        raw_intake=raw_intake,
        intake_data=None,
        triage_data=None,
        
        # Phase II: Admin Prep
        admin_prep_data=None,
        retrieved_protocols=None,
        
        # Phase III: Clinical Briefing
        ehr_context=raw_intake.get("ehr_context"),
        clinical_briefing=None,
        
        # Legacy fields
        input_data=raw_intake,
        validated_data=None,
        rules_output=None,
        
        # Outputs
        prep_sections=None,
        patient_message=None,
        clinician_summary=None,
        draft_message=None,
        final_message=None,
        preview=None,
        rules_explanation=None,
        
        # Metadata
        errors=[],
        reasoning_trace=[],
        metadata={
            "start_time": None,
            "end_time": None,
            "steps": [],
            "phase": "intake"
        },
        llm_used=False,
        saved_record_id=None
    )

