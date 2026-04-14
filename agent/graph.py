"""
LangGraph Agent for THREE-PHASE Appointment Prep System.

This module defines the agent graph that orchestrates the three-phase workflow:
- Phase I: Triage & Intake
- Phase II: Admin Prep
- Phase III: Clinical Briefing
"""

from datetime import datetime
from typing import Dict, Any
import logging

from langgraph.graph import StateGraph, END
from agent.state import AgentState, create_initial_state
from agent.tools import (
    intake_node_tool,
    triage_node_tool,
    protocol_retrieval_tool,
    admin_prep_tool,
    clinical_briefing_tool,
    patient_message_tool,
    clinician_summary_tool,
    save_output_tool,
    conversation_intake_node,
    voice_input_node,
    missing_info_detector_node,
    clarification_agent_node,
    scheduling_orchestrator_node,
    hospital_suggestion_node
)

logger = logging.getLogger(__name__)


def build_graph(
    rules_engine,
    retrieval_service,
    llm_client,
    storage
) -> StateGraph:
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Define nodes for autonomous workflow
    workflow.add_node("voice_input", voice_input_node)
    workflow.add_node("conversation_intake", lambda state: conversation_intake_node(state, llm_client))
    workflow.add_node("missing_info_detector", missing_info_detector_node)
    workflow.add_node("clarification_agent", clarification_agent_node)
    workflow.add_node("process_intake", lambda state: intake_node_tool(state, llm_client))
    
    workflow.add_node("triage", lambda state: triage_node_tool(state))
    workflow.add_node("protocol_retrieval", lambda state: protocol_retrieval_tool(state, retrieval_service))
    workflow.add_node("admin_prep", lambda state: admin_prep_tool(state, rules_engine))
    workflow.add_node("hospital_suggestion", hospital_suggestion_node)
    workflow.add_node("scheduling_orchestrator", scheduling_orchestrator_node)
    
    workflow.add_node("clinical_briefing", lambda state: clinical_briefing_tool(state, llm_client))
    workflow.add_node("patient_message", lambda state: patient_message_tool(state, llm_client))
    workflow.add_node("clinician_summary", lambda state: clinician_summary_tool(state))
    workflow.add_node("save", lambda state: save_output_tool(state, storage))
    
    # Entry Point
    workflow.set_entry_point("voice_input")
    
    # Intake flow
    workflow.add_edge("voice_input", "conversation_intake")
    workflow.add_edge("conversation_intake", "missing_info_detector")
    
    def confidence_router(state: AgentState):
        c_score = state.get("conversation_data", {}).get("confidence_score", 1.0)
        if c_score < 0.8:
            return "incomplete"
        return "complete"

    workflow.add_conditional_edges(
        "missing_info_detector",
        confidence_router,
        {
            "incomplete": "clarification_agent",
            "complete": "process_intake"
        }
    )
    
    # If incomplete, we end the current turn expecting the system to resume
    # at intake when the user replies (effectively "back to intake").
    workflow.add_edge("clarification_agent", END)
    
    # Processed intake -> triage
    workflow.add_edge("process_intake", "triage")
    
    # If complete, proceed to triage -> protocol -> admin prep -> hospital suggestion -> scheduling
    workflow.add_edge("triage", "protocol_retrieval")
    workflow.add_edge("protocol_retrieval", "admin_prep")
    workflow.add_edge("admin_prep", "hospital_suggestion")
    workflow.add_edge("hospital_suggestion", "scheduling_orchestrator")
    
    # Output Generation
    workflow.add_edge("scheduling_orchestrator", "clinical_briefing")
    workflow.add_edge("clinical_briefing", "patient_message")
    workflow.add_edge("patient_message", "clinician_summary")
    
    # Save and End
    workflow.add_edge("clinician_summary", "save")
    workflow.add_edge("save", END)
    
    # Compile the graph
    return workflow.compile()


def run_agent(
    raw_intake: Dict[str, Any],
    rules_engine,
    retrieval_service,
    llm_client,
    storage
) -> Dict[str, Any]:
    """
    Execute the THREE-PHASE LangGraph agent with input data.
    
    This is the main entry point for the agent system. It:
    1. Creates initial state from raw intake
    2. Builds the three-phase graph
    3. Executes the graph
    4. Returns both patient and clinician outputs
    
    Args:
        raw_intake: Raw intake data (symptoms, demographics, EHR context)
        rules_engine: RulesEngine instance
        retrieval_service: ProtocolRetrieval instance
        llm_client: LLMClient instance
        storage: StorageService instance
    
    Returns:
        Dictionary with patient_message, clinician_summary, and metadata
    """
    logger.info("Starting THREE-PHASE LangGraph agent execution")
    
    # Create initial state
    initial_state = create_initial_state(raw_intake)
    initial_state["metadata"]["start_time"] = datetime.now().isoformat()
    
    try:
        # Build the graph
        graph = build_graph(rules_engine, retrieval_service, llm_client, storage)
        
        # Execute the graph
        final_state = graph.invoke(initial_state)
        
        # Mark end time
        final_state["metadata"]["end_time"] = datetime.now().isoformat()
        
        # Check for errors
        if final_state["errors"]:
            logger.warning(f"Agent completed with errors: {final_state['errors']}")
            return {
                "error": True,
                "messages": final_state["errors"],
                "agent_trace": final_state["metadata"]["steps"]
            }
        
        # Success - return THREE-PHASE outputs
        logger.info("Agent execution completed successfully")
        return {
            "error": False,
            # Patient-facing output
            "patient_message": final_state.get("patient_message"),
            "prep_sections": final_state.get("prep_sections"),  # Backward compatibility
            # Clinician-facing output
            "clinician_summary": final_state.get("clinician_summary"),
            # Metadata
            "intake_data": final_state.get("intake_data"),
            "triage_data": final_state.get("triage_data"),
            "admin_prep_data": final_state.get("admin_prep_data"),
            "clinical_briefing": final_state.get("clinical_briefing"),
            "message_id": final_state.get("saved_record_id"),
            "llm_used": final_state.get("llm_used", False),
            "agent_trace": final_state["metadata"]["steps"],
            # Clarification specific response
            "clarification_message": final_state.get("draft_message", ""),
            "suggested_options": final_state.get("conversation_data", {}).get("suggested_options", {}),
            # Backward compatibility
            "preview": final_state.get("patient_message", "")[:200] if final_state.get("patient_message") else "",
            "full_message": final_state.get("patient_message"),
            "rules_explanation": []
        }
    
    except Exception as e:
        logger.error(f"Agent execution error: {type(e).__name__}: {str(e)}")
        return {
            "error": True,
            "messages": [f"Agent execution failed: {str(e)}"],
            "agent_trace": []
        }


def visualize_graph(rules_engine, retrieval_service, llm_client, storage):
    """
    Generate a visual representation of the THREE-PHASE agent graph.
    
    This is useful for debugging and understanding the agent flow.
    
    Args:
        rules_engine: RulesEngine instance
        retrieval_service: ProtocolRetrieval instance
        llm_client: LLMClient instance
        storage: StorageService instance
    
    Returns:
        Graph visualization (if graphviz is available)
    """
    graph = build_graph(rules_engine, retrieval_service, llm_client, storage)
    
    try:
        # Try to generate visualization
        return graph.get_graph().draw_mermaid()
    except Exception as e:
        logger.warning(f"Could not generate graph visualization: {e}")
        return None
