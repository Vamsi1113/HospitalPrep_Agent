"""
Agent State Definition for LangGraph-based Appointment Prep Agent.

This module defines the state structure that flows through the agent graph.
Each node in the graph reads from and writes to this state.
"""

from typing import TypedDict, Optional, List, Dict, Any


class PrepPlanSections(TypedDict):
    """Structured preparation plan sections."""
    appointment_summary: str
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
    as the agent progresses through its workflow.
    
    Attributes:
        input_data: Raw input from the user (appointment details)
        validated_data: Validated and normalized appointment data
        rules_output: PrepRules object from rules engine
        prep_sections: Structured preparation plan sections
        draft_message: Template-based message before LLM enhancement
        final_message: Final message (LLM-enhanced or template fallback)
        preview: Short preview text for UI display
        rules_explanation: List of rule explanations for transparency
        errors: List of error messages if validation or processing fails
        reasoning_trace: Step-by-step reasoning for explainability
        metadata: Additional metadata including timestamps
        llm_used: Boolean indicating if LLM was used for enhancement
        saved_record_id: Database ID of saved message (if saved)
    """
    # Input stage
    input_data: Dict[str, Any]
    
    # Validation stage
    validated_data: Optional[Dict[str, Any]]
    
    # Rules stage
    rules_output: Optional[Any]  # PrepRules object
    
    # Preparation plan stage
    prep_sections: Optional[PrepPlanSections]
    
    # Message generation stage
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


def create_initial_state(input_data: Dict[str, Any]) -> AgentState:
    """
    Create initial agent state from user input.
    
    Args:
        input_data: Raw appointment data from user
    
    Returns:
        AgentState with initialized fields
    """
    return AgentState(
        input_data=input_data,
        validated_data=None,
        rules_output=None,
        prep_sections=None,
        draft_message=None,
        final_message=None,
        preview=None,
        rules_explanation=None,
        errors=[],
        reasoning_trace=[],
        metadata={
            "start_time": None,
            "end_time": None,
            "steps": []
        },
        llm_used=False,
        saved_record_id=None
    )
