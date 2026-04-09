"""
LangGraph Agent for Appointment Prep System.

This module defines the agent graph that orchestrates the appointment
preparation workflow using LangGraph's StateGraph.
"""

from datetime import datetime
from typing import Dict, Any
import logging

from langgraph.graph import StateGraph, END
from agent.state import AgentState, create_initial_state
from agent.tools import (
    validate_input_tool,
    apply_rules_tool,
    build_prep_plan_tool,
    build_message_tool,
    enhance_message_tool,
    save_output_tool
)

logger = logging.getLogger(__name__)


def build_graph(rules_engine, prep_plan_builder, message_builder, llm_client, storage) -> StateGraph:
    """
    Build the LangGraph agent workflow.
    
    The graph defines a structured flow:
    START → validate_input → apply_rules → build_prep_plan → build_message → enhance_message → save_output → END
    
    With conditional logic:
    - If validation fails, skip to END
    - If LLM unavailable, enhance_message uses template fallback
    
    Args:
        rules_engine: RulesEngine instance
        prep_plan_builder: PrepPlanBuilder instance
        message_builder: MessageBuilder instance
        llm_client: LLMClient instance
        storage: StorageService instance
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Define nodes (each node is a tool)
    workflow.add_node("validate_input", lambda state: validate_input_tool(state))
    workflow.add_node("apply_rules", lambda state: apply_rules_tool(state, rules_engine))
    workflow.add_node("build_prep_plan", lambda state: build_prep_plan_tool(state, prep_plan_builder))
    workflow.add_node("build_message", lambda state: build_message_tool(state, message_builder))
    workflow.add_node("enhance_message", lambda state: enhance_message_tool(state, llm_client))
    workflow.add_node("save_output", lambda state: save_output_tool(state, storage))
    
    # Define edges (workflow flow)
    workflow.set_entry_point("validate_input")
    
    # Conditional edge after validation
    def should_continue_after_validation(state: AgentState) -> str:
        """Check if validation succeeded."""
        if state["errors"]:
            # Validation failed, end workflow
            return END
        return "apply_rules"
    
    workflow.add_conditional_edges(
        "validate_input",
        should_continue_after_validation,
        {
            "apply_rules": "apply_rules",
            END: END
        }
    )
    
    # Linear flow after validation succeeds
    workflow.add_edge("apply_rules", "build_prep_plan")
    workflow.add_edge("build_prep_plan", "build_message")
    workflow.add_edge("build_message", "enhance_message")
    workflow.add_edge("enhance_message", "save_output")
    workflow.add_edge("save_output", END)
    
    # Compile the graph
    return workflow.compile()


def run_agent(
    input_data: Dict[str, Any],
    rules_engine,
    prep_plan_builder,
    message_builder,
    llm_client,
    storage
) -> Dict[str, Any]:
    """
    Execute the LangGraph agent with input data.
    
    This is the main entry point for the agent system. It:
    1. Creates initial state
    2. Builds the graph
    3. Executes the graph
    4. Returns the final result
    
    Args:
        input_data: Raw appointment data from user
        rules_engine: RulesEngine instance
        prep_plan_builder: PrepPlanBuilder instance
        message_builder: MessageBuilder instance
        llm_client: LLMClient instance
        storage: StorageService instance
    
    Returns:
        Dictionary with result data for Flask response
    """
    logger.info("Starting LangGraph agent execution")
    
    # Create initial state
    initial_state = create_initial_state(input_data)
    initial_state["metadata"]["start_time"] = datetime.now().isoformat()
    
    try:
        # Build the graph
        graph = build_graph(rules_engine, prep_plan_builder, message_builder, llm_client, storage)
        
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
        
        # Success - return result
        logger.info("Agent execution completed successfully")
        return {
            "error": False,
            "prep_sections": final_state.get("prep_sections"),
            "preview": final_state.get("preview"),
            "full_message": final_state.get("final_message"),
            "rules_explanation": final_state.get("rules_explanation"),
            "message_id": final_state.get("saved_record_id"),
            "llm_used": final_state.get("llm_used", False),
            "agent_trace": final_state["metadata"]["steps"]
        }
    
    except Exception as e:
        logger.error(f"Agent execution error: {type(e).__name__}: {str(e)}")
        return {
            "error": True,
            "messages": [f"Agent execution failed: {str(e)}"],
            "agent_trace": []
        }


def visualize_graph(rules_engine, prep_plan_builder, message_builder, llm_client, storage):
    """
    Generate a visual representation of the agent graph.
    
    This is useful for debugging and understanding the agent flow.
    
    Args:
        rules_engine: RulesEngine instance
        prep_plan_builder: PrepPlanBuilder instance
        message_builder: MessageBuilder instance
        llm_client: LLMClient instance
        storage: StorageService instance
    
    Returns:
        Graph visualization (if graphviz is available)
    """
    graph = build_graph(rules_engine, prep_plan_builder, message_builder, llm_client, storage)
    
    try:
        # Try to generate visualization
        return graph.get_graph().draw_mermaid()
    except Exception as e:
        logger.warning(f"Could not generate graph visualization: {e}")
        return None
