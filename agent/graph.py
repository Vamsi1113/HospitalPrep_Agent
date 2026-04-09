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
    save_output_tool
)

logger = logging.getLogger(__name__)


def build_graph(
    rules_engine,
    retrieval_service,
    llm_client,
    storage
) -> StateGraph:
    """
    Build the THREE-PHASE LangGraph agent workflow.
    
    Graph flow:
    START → intake → triage → protocol_retrieval → admin_prep → 
    clinical_briefing → patient_message → clinician_summary → save → END
    
    Conditional logic:
    - If red flags detected, mark for human review
    - If retrieval unavailable, use fallback rules
    - If symptoms unclear, could loop back (future enhancement)
    
    Args:
        rules_engine: RulesEngine instance
        retrieval_service: ProtocolRetrieval instance
        llm_client: LLMClient instance
        storage: StorageService instance
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Define nodes for THREE-PHASE workflow
    workflow.add_node("intake", lambda state: intake_node_tool(state, llm_client))
    workflow.add_node("triage", lambda state: triage_node_tool(state))
    workflow.add_node("protocol_retrieval", lambda state: protocol_retrieval_tool(state, retrieval_service))
    workflow.add_node("admin_prep", lambda state: admin_prep_tool(state, rules_engine))
    workflow.add_node("clinical_briefing", lambda state: clinical_briefing_tool(state, llm_client))
    workflow.add_node("patient_message", lambda state: patient_message_tool(state, llm_client))
    workflow.add_node("clinician_summary", lambda state: clinician_summary_tool(state))
    workflow.add_node("save", lambda state: save_output_tool(state, storage))
    
    # Define edges (workflow flow)
    workflow.set_entry_point("intake")
    
    # Phase I: Intake → Triage
    workflow.add_edge("intake", "triage")
    
    # Phase II: Triage → Protocol Retrieval → Admin Prep
    workflow.add_edge("triage", "protocol_retrieval")
    workflow.add_edge("protocol_retrieval", "admin_prep")
    
    # Phase III: Admin Prep → Clinical Briefing
    workflow.add_edge("admin_prep", "clinical_briefing")
    
    # Output Generation: Clinical Briefing → Patient Message → Clinician Summary
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
