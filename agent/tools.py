"""
Agent Tools - Service wrappers for LangGraph nodes.

This module wraps existing services as tools that can be used by the LangGraph agent.
Each tool takes the agent state, performs an operation, and returns updated state.
"""

from typing import Dict, Any
from datetime import datetime
import logging

from agent.state import AgentState
from services.validation import validate_appointment_data
from services.rules_engine import RulesEngine
from services.message_builder import MessageBuilder
from services.llm_client import LLMClient
from services.storage import StorageService
from services.prep_plan_builder import PrepPlanBuilder

logger = logging.getLogger(__name__)


def validate_input_tool(state: AgentState, **kwargs) -> AgentState:
    """
    Tool: Validate user input data.
    
    This tool wraps the validation service and updates the state with
    validated data or error messages.
    
    Args:
        state: Current agent state
        **kwargs: Additional arguments (unused)
    
    Returns:
        Updated agent state with validated_data or errors
    """
    logger.info("Agent Tool: validate_input_tool")
    
    # Add step to reasoning trace
    state["metadata"]["steps"].append({
        "step": "validate_input",
        "timestamp": datetime.now().isoformat(),
        "description": "Validating appointment data"
    })
    
    try:
        # Call validation service (returns tuple: is_valid, errors)
        is_valid, errors = validate_appointment_data(state["input_data"])
        
        if not is_valid:
            # Validation failed
            state["errors"].extend(errors)
            state["metadata"]["steps"].append({
                "step": "validate_input_failed",
                "timestamp": datetime.now().isoformat(),
                "errors": errors
            })
        else:
            # Validation succeeded
            state["validated_data"] = state["input_data"]
            state["metadata"]["steps"].append({
                "step": "validate_input_success",
                "timestamp": datetime.now().isoformat(),
                "description": "All fields validated successfully"
            })
    
    except Exception as e:
        logger.error(f"Validation tool error: {type(e).__name__}")
        state["errors"].append(f"Validation error: {str(e)}")
        state["metadata"]["steps"].append({
            "step": "validate_input_error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        })
    
    return state


def apply_rules_tool(state: AgentState, rules_engine: RulesEngine, **kwargs) -> AgentState:
    """
    Tool: Apply deterministic preparation rules.
    
    This tool wraps the rules engine and determines all medical instructions
    based on appointment type and procedure.
    
    Args:
        state: Current agent state
        rules_engine: RulesEngine instance
        **kwargs: Additional arguments (unused)
    
    Returns:
        Updated agent state with rules_output
    """
    logger.info("Agent Tool: apply_rules_tool")
    
    # Add step to reasoning trace
    state["metadata"]["steps"].append({
        "step": "apply_rules",
        "timestamp": datetime.now().isoformat(),
        "description": "Applying deterministic preparation rules"
    })
    
    try:
        # Call rules engine with appointment_type and procedure
        rules = rules_engine.apply_rules(
            state["validated_data"]["appointment_type"],
            state["validated_data"]["procedure"]
        )
        state["rules_output"] = rules
        
        # Log rule details
        state["metadata"]["steps"].append({
            "step": "apply_rules_success",
            "timestamp": datetime.now().isoformat(),
            "category": rules.category,
            "fasting_required": rules.fasting_required,
            "fasting_hours": rules.fasting_hours if rules.fasting_required else 0,
            "arrival_minutes": rules.arrival_minutes_early,
            "items_count": len(rules.items_to_bring),
            "responsible_adult": rules.requires_responsible_adult
        })
    
    except Exception as e:
        logger.error(f"Rules tool error: {type(e).__name__}")
        state["errors"].append(f"Rules engine error: {str(e)}")
        state["metadata"]["steps"].append({
            "step": "apply_rules_error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        })
    
    return state


def build_message_tool(state: AgentState, message_builder: MessageBuilder, **kwargs) -> AgentState:
    """
    Tool: Build template-based message.
    
    This tool generates the structured message using templates.
    This is the draft message before any LLM enhancement.
    
    Args:
        state: Current agent state
        message_builder: MessageBuilder instance
        **kwargs: Additional arguments (unused)
    
    Returns:
        Updated agent state with draft_message, preview, and rules_explanation
    """
    logger.info("Agent Tool: build_message_tool")
    
    # Add step to reasoning trace
    state["metadata"]["steps"].append({
        "step": "build_message",
        "timestamp": datetime.now().isoformat(),
        "description": "Generating template-based message"
    })
    
    try:
        # Build template message (no LLM)
        draft = message_builder.build_template_message(
            state["validated_data"],
            state["rules_output"]
        )
        state["draft_message"] = draft
        
        # Build preview
        preview = message_builder.build_preview(
            state["validated_data"],
            state["rules_output"]
        )
        state["preview"] = preview
        
        # Build rules explanation
        rules_explanation = message_builder.format_rules_explanation(
            state["rules_output"]
        )
        state["rules_explanation"] = rules_explanation
        
        state["metadata"]["steps"].append({
            "step": "build_message_success",
            "timestamp": datetime.now().isoformat(),
            "message_length": len(draft),
            "preview_length": len(preview),
            "rules_count": len(rules_explanation)
        })
    
    except Exception as e:
        logger.error(f"Message builder tool error: {type(e).__name__}")
        state["errors"].append(f"Message generation error: {str(e)}")
        state["metadata"]["steps"].append({
            "step": "build_message_error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        })
    
    return state


def enhance_message_tool(state: AgentState, llm_client: LLMClient, **kwargs) -> AgentState:
    """
    Tool: Enhance message with LLM (optional).
    
    This tool attempts to rewrite the draft message in a friendly tone
    using the LLM. If LLM fails or is unavailable, the draft message
    is used as the final message.
    
    SAFETY: The LLM is ONLY used for tone/wording. All medical instructions
    come from the rules engine.
    
    Args:
        state: Current agent state
        llm_client: LLMClient instance
        **kwargs: Additional arguments (unused)
    
    Returns:
        Updated agent state with final_message and llm_used flag
    """
    logger.info("Agent Tool: enhance_message_tool")
    
    # Add step to reasoning trace
    state["metadata"]["steps"].append({
        "step": "enhance_message",
        "timestamp": datetime.now().isoformat(),
        "description": "Attempting LLM enhancement",
        "llm_available": llm_client.is_available()
    })
    
    try:
        if llm_client.is_available():
            # Attempt LLM enhancement
            enhanced = llm_client.rewrite_message(state["draft_message"], tone="friendly")
            
            if enhanced:
                # LLM succeeded
                state["final_message"] = enhanced
                state["llm_used"] = True
                state["metadata"]["steps"].append({
                    "step": "enhance_message_success",
                    "timestamp": datetime.now().isoformat(),
                    "description": "LLM enhancement successful",
                    "enhanced_length": len(enhanced)
                })
            else:
                # LLM failed, use template fallback
                state["final_message"] = state["draft_message"]
                state["llm_used"] = False
                state["metadata"]["steps"].append({
                    "step": "enhance_message_fallback",
                    "timestamp": datetime.now().isoformat(),
                    "description": "LLM failed, using template fallback"
                })
        else:
            # LLM not available, use template
            state["final_message"] = state["draft_message"]
            state["llm_used"] = False
            state["metadata"]["steps"].append({
                "step": "enhance_message_skipped",
                "timestamp": datetime.now().isoformat(),
                "description": "LLM not available, using template"
            })
    
    except Exception as e:
        logger.error(f"LLM enhancement tool error: {type(e).__name__}")
        # On error, fall back to template
        state["final_message"] = state["draft_message"]
        state["llm_used"] = False
        state["metadata"]["steps"].append({
            "step": "enhance_message_error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "description": "Error during enhancement, using template"
        })
    
    return state


def build_prep_plan_tool(state: AgentState, prep_plan_builder: PrepPlanBuilder, **kwargs) -> AgentState:
    """
    Tool: Build structured preparation plan sections.
    
    This tool generates comprehensive, structured preparation instructions
    organized into sections (fasting, diet, medications, etc.).
    
    Args:
        state: Current agent state
        prep_plan_builder: PrepPlanBuilder instance
        **kwargs: Additional arguments (unused)
    
    Returns:
        Updated agent state with prep_sections
    """
    logger.info("Agent Tool: build_prep_plan_tool")
    
    # Add step to reasoning trace
    state["metadata"]["steps"].append({
        "step": "build_prep_plan",
        "timestamp": datetime.now().isoformat(),
        "description": "Building structured preparation plan"
    })
    
    try:
        # Build structured sections
        prep_sections = prep_plan_builder.build_prep_sections(
            state["validated_data"],
            state["rules_output"]
        )
        state["prep_sections"] = prep_sections
        
        state["metadata"]["steps"].append({
            "step": "build_prep_plan_success",
            "timestamp": datetime.now().isoformat(),
            "sections_count": len([v for v in prep_sections.values() if v is not None])
        })
    
    except Exception as e:
        logger.error(f"Prep plan builder tool error: {type(e).__name__}")
        state["errors"].append(f"Prep plan generation error: {str(e)}")
        state["metadata"]["steps"].append({
            "step": "build_prep_plan_error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        })
    
    return state


def save_output_tool(state: AgentState, storage: StorageService, **kwargs) -> AgentState:
    """
    Tool: Save generated message to database.
    
    This tool persists the final message and metadata to SQLite.
    
    Args:
        state: Current agent state
        storage: StorageService instance
        **kwargs: Additional arguments (unused)
    
    Returns:
        Updated agent state with message_id
    """
    logger.info("Agent Tool: save_output_tool")
    
    # Add step to reasoning trace
    state["metadata"]["steps"].append({
        "step": "save_output",
        "timestamp": datetime.now().isoformat(),
        "description": "Saving message to database"
    })
    
    try:
        # Save to database
        message_id = storage.save_message(
            appointment_data=state["validated_data"],
            generated_text=state["final_message"],
            rules_used=state["rules_output"].__dict__
        )
        
        state["saved_record_id"] = message_id
        state["metadata"]["steps"].append({
            "step": "save_output_success",
            "timestamp": datetime.now().isoformat(),
            "message_id": message_id
        })
    
    except Exception as e:
        logger.error(f"Storage tool error: {type(e).__name__}")
        state["errors"].append(f"Storage error: {str(e)}")
        state["metadata"]["steps"].append({
            "step": "save_output_error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        })
    
    return state
