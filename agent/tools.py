"""
Agent Tools - Service wrappers for LangGraph nodes.

This module wraps services as tools for the THREE-PHASE agent workflow:
- Phase I: Triage & Intake
- Phase II: Admin Prep  
- Phase III: Clinical Briefing
"""

from typing import Dict, Any
from datetime import datetime
import logging
import json

from agent.state import AgentState
from agent.prompts import (
    SYMPTOM_NORMALIZATION_PROMPT,
    FOLLOW_UP_QUESTIONS_PROMPT,
    TRIAGE_CLASSIFICATION_PROMPT,
    CLINICAL_BRIEFING_PROMPT,
    PATIENT_MESSAGE_REWRITE_PROMPT
)

logger = logging.getLogger(__name__)


# ============================================================================
# PHASE I: TRIAGE & INTAKE TOOLS
# ============================================================================

def intake_node_tool(state: AgentState, llm_client, **kwargs) -> AgentState:
    """
    Phase I Tool: Process intake, normalize symptoms, identify follow-ups.
    
    This tool:
    1. Extracts chief complaint and symptoms from raw intake
    2. Normalizes casual symptom language to clinical terms (using LLM if available)
    3. Identifies missing information
    4. Generates follow-up questions if needed
    
    Args:
        state: Current agent state
        llm_client: LLM client for symptom normalization
    
    Returns:
        Updated state with intake_data populated
    """
    logger.info("Agent Tool: intake_node_tool (Phase I)")
    
    state["metadata"]["steps"].append({
        "step": "intake_processing",
        "phase": "I",
        "timestamp": datetime.now().isoformat(),
        "description": "Processing patient intake and symptoms"
    })
    
    try:
        raw = state["raw_intake"]
        
        # Extract chief complaint
        chief_complaint = raw.get("chief_complaint", "")
        symptoms_desc = raw.get("symptoms_description", "")
        
        # Normalize symptoms using LLM if available
        normalized_complaint = None
        if llm_client and llm_client.is_available() and chief_complaint:
            prompt = SYMPTOM_NORMALIZATION_PROMPT.format(
                symptom_description=chief_complaint
            )
            normalized_complaint = llm_client.generate_with_prompt(
                "You are a medical intake assistant normalizing symptom descriptions.",
                prompt
            )
        
        # Build structured intake data
        intake_data = {
            "chief_complaint": chief_complaint,
            "chief_complaint_normalized": normalized_complaint,
            "symptoms": _parse_symptoms(symptoms_desc),
            "current_medications": raw.get("current_medications", []),
            "allergies": raw.get("allergies", []),
            "age_group": raw.get("age_group"),
            "pregnancy_flag": raw.get("pregnancy_flag", False),
            "prior_conditions": raw.get("prior_conditions", []),
            "needs_clarification": False,
            "follow_up_questions": []
        }
        
        # Check if we need follow-up questions
        if not symptoms_desc or len(symptoms_desc) < 20:
            intake_data["needs_clarification"] = True
            # Generate follow-up questions (simplified for now)
            intake_data["follow_up_questions"] = _generate_follow_up_questions(
                chief_complaint, symptoms_desc
            )
        
        state["intake_data"] = intake_data
        state["metadata"]["steps"].append({
            "step": "intake_complete",
            "phase": "I",
            "timestamp": datetime.now().isoformat(),
            "normalized": normalized_complaint is not None,
            "needs_clarification": intake_data["needs_clarification"]
        })
        
    except Exception as e:
        logger.error(f"Intake tool error: {e}")
        state["errors"].append(f"Intake processing error: {str(e)}")
        # Create minimal intake_data to prevent downstream errors
        if "intake_data" not in state:
            state["intake_data"] = {
                "chief_complaint": raw.get("chief_complaint", ""),
                "chief_complaint_normalized": None,
                "symptoms": [],
                "current_medications": raw.get("current_medications", []),
                "allergies": raw.get("allergies", []),
                "age_group": raw.get("age_group"),
                "pregnancy_flag": raw.get("pregnancy_flag", False),
                "prior_conditions": raw.get("prior_conditions", []),
                "needs_clarification": True,
                "follow_up_questions": []
            }
    
    return state


def triage_node_tool(state: AgentState, **kwargs) -> AgentState:
    """
    Phase I Tool: Classify urgency and identify red flags.
    
    This tool:
    1. Classifies urgency level (routine, urgent, emergency)
    2. Identifies red flags requiring immediate attention
    3. Determines prep complexity
    4. Flags cases requiring human review
    
    Args:
        state: Current agent state
    
    Returns:
        Updated state with triage_data populated
    """
    logger.info("Agent Tool: triage_node_tool (Phase I)")
    
    state["metadata"]["steps"].append({
        "step": "triage_classification",
        "phase": "I",
        "timestamp": datetime.now().isoformat(),
        "description": "Classifying urgency and identifying red flags"
    })
    
    try:
        intake = state.get("intake_data")
        if not intake:
            raise ValueError("No intake data available for triage")
        
        # Deterministic triage rules
        red_flags = _identify_red_flags(
            intake.get("chief_complaint", ""),
            intake.get("symptoms", []),
            intake.get("age_group"),
            intake.get("prior_conditions", [])
        )
        
        urgency = _classify_urgency(intake.get("chief_complaint", ""), red_flags)
        
        triage_data = {
            "urgency_level": urgency,
            "red_flags": red_flags,
            "prep_complexity": _determine_prep_complexity(state.get("raw_intake", {})),
            "requires_human_review": len(red_flags) > 0 or urgency == "emergency",
            "prep_flow_type": _determine_prep_flow(state.get("raw_intake", {}))
        }
        
        state["triage_data"] = triage_data
        state["metadata"]["steps"].append({
            "step": "triage_complete",
            "phase": "I",
            "timestamp": datetime.now().isoformat(),
            "urgency": urgency,
            "red_flags_count": len(red_flags),
            "requires_review": triage_data["requires_human_review"]
        })
        
    except Exception as e:
        logger.error(f"Triage tool error: {e}")
        state["errors"].append(f"Triage error: {str(e)}")
    
    return state


# ============================================================================
# PHASE II: ADMIN PREP TOOLS
# ============================================================================

def protocol_retrieval_tool(state: AgentState, retrieval_service, **kwargs) -> AgentState:
    """
    Phase II Tool: Retrieve clinic protocols from RAG.
    
    This tool:
    1. Retrieves relevant protocols based on appointment type and procedure
    2. Falls back to deterministic rules if retrieval unavailable
    3. Stores retrieved protocols in state
    
    Args:
        state: Current agent state
        retrieval_service: Protocol retrieval service
    
    Returns:
        Updated state with retrieved_protocols populated
    """
    logger.info("Agent Tool: protocol_retrieval_tool (Phase II)")
    
    state["metadata"]["steps"].append({
        "step": "protocol_retrieval",
        "phase": "II",
        "timestamp": datetime.now().isoformat(),
        "description": "Retrieving clinic protocols"
    })
    
    try:
        raw = state["raw_intake"]
        appointment_type = raw.get("appointment_type", "")
        procedure = raw.get("procedure", "")
        
        if retrieval_service and retrieval_service.is_available():
            protocols = retrieval_service.retrieve_protocols(
                appointment_type=appointment_type,
                procedure=procedure,
                max_results=3
            )
            state["retrieved_protocols"] = protocols
            
            state["metadata"]["steps"].append({
                "step": "protocol_retrieval_success",
                "phase": "II",
                "timestamp": datetime.now().isoformat(),
                "protocols_found": len(protocols)
            })
        else:
            # Fallback to basic rules
            logger.warning("Protocol retrieval unavailable, using fallback")
            state["retrieved_protocols"] = []
            state["metadata"]["steps"].append({
                "step": "protocol_retrieval_fallback",
                "phase": "II",
                "timestamp": datetime.now().isoformat(),
                "description": "Using fallback rules"
            })
        
    except Exception as e:
        logger.error(f"Protocol retrieval error: {e}")
        state["errors"].append(f"Protocol retrieval error: {str(e)}")
        state["retrieved_protocols"] = []
    
    return state



def admin_prep_tool(state: AgentState, rules_engine, **kwargs) -> AgentState:
    """
    Phase II Tool: Generate administrative preparation instructions.
    
    This tool:
    1. Generates insurance/copay reminders
    2. Lists required documents
    3. Provides arrival instructions
    4. Includes transport/fasting instructions if needed
    5. Creates patient readiness checklist
    
    Args:
        state: Current agent state
        rules_engine: Rules engine for deterministic logic
    
    Returns:
        Updated state with admin_prep_data populated
    """
    logger.info("Agent Tool: admin_prep_tool (Phase II)")
    
    state["metadata"]["steps"].append({
        "step": "admin_prep_generation",
        "phase": "II",
        "timestamp": datetime.now().isoformat(),
        "description": "Generating administrative preparation instructions"
    })
    
    try:
        raw = state["raw_intake"]
        protocols = state.get("retrieved_protocols", [])
        
        # Apply rules to get prep requirements
        rules = rules_engine.apply_rules(
            raw.get("appointment_type", ""),
            raw.get("procedure", "")
        )
        
        # Build admin prep data
        admin_prep = {
            "insurance_verification_needed": True,
            "copay_reminder": "Please be prepared to pay your copay at check-in",
            "required_documents": _build_document_list(rules, protocols),
            "arrival_instructions": _build_arrival_instructions(rules, raw),
            "transport_instructions": _build_transport_instructions(rules) if rules.requires_responsible_adult else None,
            "fasting_instructions": _build_fasting_instructions(rules, raw) if rules.fasting_required else None,
            "diet_instructions": _build_diet_instructions(rules, protocols),
            "paperwork_reminders": _build_paperwork_reminders(protocols),
            "reschedule_warnings": _build_reschedule_warnings(state["triage_data"]),
            "patient_readiness_checklist": _build_readiness_checklist(rules, protocols)
        }
        
        state["admin_prep_data"] = admin_prep
        state["rules_output"] = rules  # Keep for backward compatibility
        
        state["metadata"]["steps"].append({
            "step": "admin_prep_complete",
            "phase": "II",
            "timestamp": datetime.now().isoformat(),
            "fasting_required": rules.fasting_required,
            "transport_required": rules.requires_responsible_adult
        })
        
    except Exception as e:
        logger.error(f"Admin prep tool error: {e}")
        state["errors"].append(f"Admin prep error: {str(e)}")
    
    return state


# ============================================================================
# PHASE III: CLINICAL BRIEFING TOOLS
# ============================================================================

def clinical_briefing_tool(state: AgentState, llm_client, **kwargs) -> AgentState:
    """
    Phase III Tool: Generate clinician-facing pre-visit summary.
    
    This tool:
    1. Summarizes relevant patient history from EHR
    2. Highlights medication conflicts
    3. Identifies missing labs/records
    4. Notes care gaps and follow-up items
    5. Assesses prep status
    
    Args:
        state: Current agent state
        llm_client: LLM client for summary generation
    
    Returns:
        Updated state with clinical_briefing populated
    """
    logger.info("Agent Tool: clinical_briefing_tool (Phase III)")
    
    state["metadata"]["steps"].append({
        "step": "clinical_briefing_generation",
        "phase": "III",
        "timestamp": datetime.now().isoformat(),
        "description": "Generating clinician-facing summary"
    })
    
    try:
        intake = state.get("intake_data")
        if not intake:
            logger.error("No intake_data in state for clinical briefing")
            raise ValueError("No intake data available for clinical briefing")
        
        ehr = state.get("ehr_context", {})
        
        # Analyze EHR context with detailed error tracking
        try:
            relevant_history = _summarize_history(ehr, intake)
        except Exception as e:
            logger.error(f"Error in _summarize_history: {e}")
            relevant_history = "Error summarizing history"
        
        try:
            medication_conflicts = _identify_med_conflicts(
                intake.get("current_medications", []),
                ehr.get("medications_on_file", [])
            )
        except Exception as e:
            logger.error(f"Error in _identify_med_conflicts: {e}")
            medication_conflicts = []
        
        try:
            missing_labs = _identify_missing_labs(ehr, state.get("raw_intake", {}))
        except Exception as e:
            logger.error(f"Error in _identify_missing_labs: {e}")
            missing_labs = []
        
        try:
            missing_records = _identify_missing_records(ehr)
        except Exception as e:
            logger.error(f"Error in _identify_missing_records: {e}")
            missing_records = []
        
        try:
            care_gaps = _identify_care_gaps(ehr, intake)
        except Exception as e:
            logger.error(f"Error in _identify_care_gaps: {e}")
            care_gaps = []
        
        try:
            follow_up_items = _identify_follow_ups(ehr)
        except Exception as e:
            logger.error(f"Error in _identify_follow_ups: {e}")
            follow_up_items = []
        
        try:
            prep_status = _assess_prep_status(state)
        except Exception as e:
            logger.error(f"Error in _assess_prep_status: {e}")
            prep_status = "Unknown"
        
        try:
            triage_data = state.get("triage_data", {})
            key_risks = triage_data.get("red_flags", []) if triage_data else []
        except Exception as e:
            logger.error(f"Error getting key_risks: {e}")
            key_risks = []
        
        briefing = {
            "relevant_history": relevant_history,
            "medication_conflicts": medication_conflicts,
            "allergy_alerts": intake.get("allergies", []),
            "missing_labs": missing_labs,
            "missing_records": missing_records,
            "care_gaps": care_gaps,
            "follow_up_items": follow_up_items,
            "prep_status": prep_status,
            "key_risks": key_risks
        }
        
        state["clinical_briefing"] = briefing
        
        state["metadata"]["steps"].append({
            "step": "clinical_briefing_complete",
            "phase": "III",
            "timestamp": datetime.now().isoformat(),
            "med_conflicts": len(briefing["medication_conflicts"]),
            "missing_labs": len(briefing["missing_labs"]),
            "key_risks": len(briefing["key_risks"])
        })
        
    except Exception as e:
        logger.error(f"Clinical briefing tool error: {e}")
        state["errors"].append(f"Clinical briefing error: {str(e)}")
    
    return state


def patient_message_tool(state: AgentState, llm_client, **kwargs) -> AgentState:
    """
    Tool: Generate patient-facing preparation message.
    
    This tool:
    1. Combines intake, admin prep, and safety info
    2. Formats in friendly, clear language
    3. Optionally enhances with LLM
    4. Includes all necessary prep sections
    
    Args:
        state: Current agent state
        llm_client: LLM client for message enhancement
    
    Returns:
        Updated state with patient_message populated
    """
    logger.info("Agent Tool: patient_message_tool")
    
    state["metadata"]["steps"].append({
        "step": "patient_message_generation",
        "timestamp": datetime.now().isoformat(),
        "description": "Generating patient-facing prep message"
    })
    
    try:
        # Build structured message
        draft = _build_patient_message_draft(state)
        
        # Optionally enhance with LLM
        if llm_client and llm_client.is_available():
            enhanced = llm_client.rewrite_message(draft, tone="friendly")
            final = enhanced if enhanced else draft
            state["llm_used"] = enhanced is not None
        else:
            final = draft
            state["llm_used"] = False
        
        state["patient_message"] = final
        state["final_message"] = final  # Backward compatibility
        
        state["metadata"]["steps"].append({
            "step": "patient_message_complete",
            "timestamp": datetime.now().isoformat(),
            "llm_used": state["llm_used"],
            "message_length": len(final)
        })
        
    except Exception as e:
        logger.error(f"Patient message tool error: {e}")
        state["errors"].append(f"Patient message error: {str(e)}")
    
    return state


def clinician_summary_tool(state: AgentState, **kwargs) -> AgentState:
    """
    Tool: Format clinician-facing summary.
    
    This tool:
    1. Formats clinical briefing for display
    2. Adds triage information
    3. Includes prep status
    4. Highlights urgent items
    
    Args:
        state: Current agent state
    
    Returns:
        Updated state with clinician_summary populated
    """
    logger.info("Agent Tool: clinician_summary_tool")
    
    try:
        briefing = state.get("clinical_briefing")
        triage = state.get("triage_data")
        intake = state.get("intake_data")
        
        if not briefing or not intake:
            state["clinician_summary"] = "Clinical briefing or intake data not available"
            return state
        
        # Format summary
        summary_parts = []
        
        # Header
        summary_parts.append(f"PRE-VISIT SUMMARY")
        summary_parts.append(f"Patient: {state.get('raw_intake', {}).get('patient_name', 'Unknown')}")
        summary_parts.append(f"Chief Complaint: {intake.get('chief_complaint', 'Not provided')}")
        if intake.get("chief_complaint_normalized"):
            summary_parts.append(f"Clinical: {intake['chief_complaint_normalized']}")
        summary_parts.append("")
        
        # Triage
        if triage:
            summary_parts.append(f"TRIAGE: {triage.get('urgency_level', 'Unknown').upper()}")
            if triage.get('red_flags'):
                summary_parts.append(f"⚠️ RED FLAGS: {', '.join(triage['red_flags'])}")
            summary_parts.append("")
        
        # History
        if briefing.get('relevant_history'):
            summary_parts.append(f"RELEVANT HISTORY:")
            summary_parts.append(briefing['relevant_history'])
            summary_parts.append("")
        
        # Medications
        if intake.get('current_medications'):
            summary_parts.append(f"CURRENT MEDICATIONS:")
            for med in intake['current_medications']:
                summary_parts.append(f"  • {med}")
            if briefing.get('medication_conflicts'):
                summary_parts.append(f"  ⚠️ CONFLICTS: {', '.join(briefing['medication_conflicts'])}")
            summary_parts.append("")
        
        # Allergies
        if briefing.get('allergy_alerts'):
            summary_parts.append(f"ALLERGIES: {', '.join(briefing['allergy_alerts'])}")
            summary_parts.append("")
        
        # Missing data
        if briefing.get('missing_labs') or briefing.get('missing_records'):
            summary_parts.append(f"MISSING DATA:")
            for lab in briefing.get('missing_labs', []):
                summary_parts.append(f"  • Lab: {lab}")
            for record in briefing.get('missing_records', []):
                summary_parts.append(f"  • Record: {record}")
            summary_parts.append("")
        
        # Prep status
        summary_parts.append(f"PREP STATUS: {briefing.get('prep_status', 'Unknown')}")
        
        state["clinician_summary"] = "\n".join(summary_parts)
        
    except Exception as e:
        logger.error(f"Clinician summary tool error: {e}")
        state["clinician_summary"] = f"Error generating summary: {str(e)}"
    
    return state



def save_output_tool(state: AgentState, storage, **kwargs) -> AgentState:
    """
    Tool: Save all three phases to database.
    
    Args:
        state: Current agent state
        storage: Storage service
    
    Returns:
        Updated state with saved_record_id
    """
    logger.info("Agent Tool: save_output_tool")
    
    state["metadata"]["steps"].append({
        "step": "save_output",
        "timestamp": datetime.now().isoformat(),
        "description": "Saving to database"
    })
    
    try:
        # Prepare data for storage
        save_data = {
            "raw_intake": state["raw_intake"],
            "intake_data": state.get("intake_data"),
            "triage_data": state.get("triage_data"),
            "admin_prep_data": state.get("admin_prep_data"),
            "clinical_briefing": state.get("clinical_briefing"),
            "patient_message": state.get("patient_message"),
            "clinician_summary": state.get("clinician_summary"),
            "reasoning_trace": state["metadata"]["steps"]
        }
        
        # Save to database (simplified - storage service needs update)
        message_id = storage.save_message(
            appointment_data=state["raw_intake"],
            generated_text=state.get("patient_message", ""),
            rules_used=state.get("rules_output").__dict__ if state.get("rules_output") else {}
        )
        
        state["saved_record_id"] = message_id
        
        state["metadata"]["steps"].append({
            "step": "save_complete",
            "timestamp": datetime.now().isoformat(),
            "record_id": message_id
        })
        
    except Exception as e:
        logger.error(f"Save tool error: {e}")
        state["errors"].append(f"Save error: {str(e)}")
    
    return state


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _parse_symptoms(symptoms_desc: str) -> list:
    """Parse symptom description into structured list."""
    if not symptoms_desc:
        return []
    
    # Simple parsing - can be enhanced
    return [{
        "description": symptoms_desc,
        "onset": "unknown",
        "duration": "unknown",
        "severity": "unknown"
    }]


def _generate_follow_up_questions(chief_complaint: str, symptoms_desc: str) -> list:
    """Generate follow-up questions based on complaint."""
    questions = []
    
    if not symptoms_desc or len(symptoms_desc) < 20:
        questions.append("When did this symptom start?")
        questions.append("How severe is it on a scale of 1-10?")
        questions.append("Does anything make it better or worse?")
    
    return questions


def _identify_red_flags(complaint: str, symptoms: list, age_group: str, prior_conditions: list) -> list:
    """Identify red flags requiring immediate attention."""
    red_flags = []
    complaint_lower = complaint.lower() if complaint else ""
    
    # Chest pain red flags
    if "chest" in complaint_lower and ("pain" in complaint_lower or "pressure" in complaint_lower):
        red_flags.append("Chest pain/pressure - requires urgent evaluation")
    
    # Breathing difficulty
    if "breath" in complaint_lower or "breathing" in complaint_lower:
        red_flags.append("Difficulty breathing")
    
    # Severe pain
    if "severe" in complaint_lower and "pain" in complaint_lower:
        red_flags.append("Severe pain")
    
    # Elderly with falls/dizziness
    if age_group and "70" in age_group and "dizz" in complaint_lower:
        red_flags.append("Elderly patient with dizziness - fall risk")
    
    return red_flags


def _classify_urgency(complaint: str, red_flags: list) -> str:
    """Classify urgency level."""
    if len(red_flags) > 0:
        return "urgent"
    
    complaint_lower = complaint.lower() if complaint else ""
    
    # Emergency keywords
    if any(word in complaint_lower for word in ["chest pain", "can't breathe", "severe bleeding"]):
        return "emergency"
    
    return "routine"


def _determine_prep_complexity(raw_intake: dict) -> str:
    """Determine preparation complexity."""
    procedure = raw_intake.get("procedure", "").lower()
    
    if "surgery" in procedure:
        return "complex"
    elif "colonoscopy" in procedure or "endoscopy" in procedure:
        return "complex"
    elif "mri" in procedure or "ct" in procedure:
        return "moderate"
    else:
        return "simple"


def _determine_prep_flow(raw_intake: dict) -> str:
    """Determine prep flow type."""
    apt_type = raw_intake.get("appointment_type", "").lower()
    procedure = raw_intake.get("procedure", "").lower()
    
    if "surgery" in apt_type or "surgery" in procedure:
        return "procedure"
    elif "imaging" in apt_type:
        return "standard"
    else:
        return "standard"


def _build_document_list(rules, protocols: list) -> list:
    """Build list of required documents."""
    docs = list(rules.items_to_bring)
    
    # Add from protocols
    for protocol in protocols:
        protocol_docs = protocol.get("instructions", {}).get("general", [])
        for doc in protocol_docs:
            if doc not in docs:
                docs.append(doc)
    
    return docs


def _build_arrival_instructions(rules, raw_intake: dict) -> str:
    """Build arrival instructions."""
    from datetime import datetime, timedelta
    
    apt_datetime_str = raw_intake.get("appointment_datetime", "")
    try:
        apt_datetime = datetime.fromisoformat(apt_datetime_str.replace('Z', '+00:00'))
        arrival_time = apt_datetime - timedelta(minutes=rules.arrival_minutes_early)
        return f"Arrive at {arrival_time.strftime('%I:%M %p')} ({rules.arrival_minutes_early} minutes before your appointment)"
    except:
        return f"Arrive {rules.arrival_minutes_early} minutes before your appointment"


def _build_transport_instructions(rules) -> str:
    """Build transport instructions."""
    if rules.requires_responsible_adult:
        return "You MUST arrange for a responsible adult to drive you home. You cannot drive yourself due to sedation/anesthesia."
    return None


def _build_fasting_instructions(rules, raw_intake: dict) -> str:
    """Build fasting instructions."""
    if not rules.fasting_required:
        return None
    
    from datetime import datetime, timedelta
    
    apt_datetime_str = raw_intake.get("appointment_datetime", "")
    try:
        apt_datetime = datetime.fromisoformat(apt_datetime_str.replace('Z', '+00:00'))
        fasting_start = apt_datetime - timedelta(hours=rules.fasting_hours)
        return f"Do not eat or drink anything after {fasting_start.strftime('%I:%M %p on %B %d')} ({rules.fasting_hours} hours before appointment)"
    except:
        return f"Do not eat or drink for {rules.fasting_hours} hours before your appointment"


def _build_diet_instructions(rules, protocols: list) -> str:
    """Build diet instructions."""
    for protocol in protocols:
        diet = protocol.get("instructions", {}).get("fasting", {}).get("diet_restrictions")
        if diet:
            return str(diet)
    return None


def _build_paperwork_reminders(protocols: list) -> list:
    """Build paperwork reminders."""
    reminders = []
    for protocol in protocols:
        paperwork = protocol.get("instructions", {}).get("paperwork", [])
        reminders.extend(paperwork)
    return reminders


def _build_reschedule_warnings(triage_data: dict) -> list:
    """Build reschedule warnings."""
    warnings = []
    if triage_data and triage_data.get("red_flags"):
        warnings.append("Contact clinic immediately if symptoms worsen before appointment")
    return warnings


def _build_readiness_checklist(rules, protocols: list) -> list:
    """Build patient readiness checklist."""
    checklist = [
        "Confirm appointment date and time",
        "Arrange transportation if needed",
        "Complete any required paperwork",
        "Prepare list of current medications",
        "Gather required documents"
    ]
    
    if rules.fasting_required:
        checklist.append("Follow fasting instructions")
    
    return checklist


def _summarize_history(ehr: dict, intake: dict) -> str:
    """Summarize relevant patient history."""
    if not ehr:
        return "No EHR data available"
    
    if not intake:
        return "No intake data available"
    
    parts = []
    
    if ehr.get("last_visit"):
        parts.append(f"Last visit: {ehr['last_visit']}")
    
    if ehr.get("recent_labs"):
        parts.append(f"Recent labs: {', '.join([f'{k}: {v}' for k, v in ehr['recent_labs'].items()])}")
    
    if intake.get("prior_conditions"):
        parts.append(f"Prior conditions: {', '.join(intake['prior_conditions'])}")
    
    return "; ".join(parts) if parts else "No significant history"


def _identify_med_conflicts(current_meds: list, ehr_meds: list) -> list:
    """Identify medication conflicts."""
    conflicts = []
    
    # Simple check for discrepancies
    current_set = set([m.lower() for m in current_meds])
    ehr_set = set([m.lower().split()[0] for m in ehr_meds])  # Get drug name only
    
    # Meds in EHR but not reported by patient
    for ehr_med in ehr_set:
        if not any(ehr_med in curr for curr in current_set):
            conflicts.append(f"EHR shows {ehr_med} but not reported by patient")
    
    return conflicts


def _identify_missing_labs(ehr: dict, raw_intake: dict) -> list:
    """Identify missing lab work."""
    missing = []
    procedure = raw_intake.get("procedure", "").lower()
    
    # Check for procedure-specific lab requirements
    if "surgery" in procedure:
        if not ehr.get("recent_labs", {}).get("complete_blood_count"):
            missing.append("CBC")
        if not ehr.get("recent_labs", {}).get("basic_metabolic_panel"):
            missing.append("BMP")
    
    if "contrast" in procedure:
        if not ehr.get("recent_labs", {}).get("kidney_function"):
            missing.append("Kidney function (creatinine)")
    
    return missing


def _identify_missing_records(ehr: dict) -> list:
    """Identify missing records."""
    missing = []
    
    if not ehr.get("medications_on_file"):
        missing.append("Current medication list")
    
    if not ehr.get("allergies_on_file"):
        missing.append("Allergy information")
    
    return missing


def _identify_care_gaps(ehr: dict, intake: dict) -> list:
    """Identify care gaps."""
    if not intake:
        return []
    
    gaps = []
    
    # Check for overdue screenings based on age
    age_group = intake.get("age_group", "")
    if "50" in age_group or "60" in age_group or "70" in age_group:
        if not ehr.get("recent_colonoscopy"):
            gaps.append("Colorectal cancer screening may be due")
    
    return gaps


def _identify_follow_ups(ehr: dict) -> list:
    """Identify follow-up items."""
    follow_ups = []
    
    if ehr.get("pending_referrals"):
        follow_ups.append("Pending specialist referrals")
    
    if ehr.get("abnormal_labs"):
        follow_ups.append("Abnormal lab results need follow-up")
    
    return follow_ups


def _assess_prep_status(state: AgentState) -> str:
    """Assess overall prep status."""
    admin_prep = state.get("admin_prep_data")
    
    if not admin_prep:
        return "Incomplete"
    
    if admin_prep.get("reschedule_warnings"):
        return "Needs review - potential reschedule"
    
    if state.get("triage_data", {}).get("requires_human_review"):
        return "Requires human review"
    
    return "Ready for appointment"


def _build_patient_message_draft(state: AgentState) -> str:
    """Build draft patient message from all phases."""
    parts = []
    
    # Header
    raw = state["raw_intake"]
    parts.append(f"APPOINTMENT PREPARATION GUIDE")
    parts.append(f"Patient: {raw.get('patient_name', 'Unknown')}")
    parts.append(f"Appointment: {raw.get('appointment_type')} - {raw.get('procedure')}")
    parts.append("")
    
    # Symptom clarification
    intake = state.get("intake_data")
    if intake and intake.get("chief_complaint"):
        parts.append(f"REASON FOR VISIT:")
        parts.append(intake["chief_complaint"])
        if intake.get("chief_complaint_normalized"):
            parts.append(f"(Clinical term: {intake['chief_complaint_normalized']})")
        parts.append("")
    
    # Admin prep
    admin = state.get("admin_prep_data")
    if admin:
        parts.append("WHAT TO BRING:")
        for doc in admin["required_documents"]:
            parts.append(f"  • {doc}")
        parts.append("")
        
        if admin.get("arrival_instructions"):
            parts.append("ARRIVAL:")
            parts.append(admin["arrival_instructions"])
            parts.append("")
        
        if admin.get("fasting_instructions"):
            parts.append("FASTING:")
            parts.append(admin["fasting_instructions"])
            parts.append("")
        
        if admin.get("transport_instructions"):
            parts.append("TRANSPORTATION:")
            parts.append(admin["transport_instructions"])
            parts.append("")
    
    # Red flags
    triage = state.get("triage_data")
    if triage and triage.get("red_flags"):
        parts.append("⚠️ IMPORTANT - CALL CLINIC IF:")
        for flag in triage["red_flags"]:
            parts.append(f"  • {flag}")
        parts.append("")
    
    # Closing
    parts.append("If you have questions, please contact the clinic.")
    parts.append("This is a preparation guide, not medical advice.")
    
    return "\n".join(parts)



# ============================================================================
# NEW TOOLS FOR FULL PATIENT JOURNEY
# ============================================================================

def calendar_check_availability_tool(state: AgentState, calendar_service, **kwargs) -> AgentState:
    """
    Tool: Check available appointment slots.
    
    Args:
        state: Current agent state
        calendar_service: CalendarService instance
    
    Returns:
        Updated state with scheduling_data containing available slots
    """
    logger.info("Agent Tool: calendar_check_availability_tool")
    
    try:
        raw = state["raw_intake"]
        appointment_type = raw.get("appointment_type", "Consultation")
        preferred_date = raw.get("preferred_date", "")
        duration = raw.get("duration_minutes", 30)
        
        slots = calendar_service.get_available_slots(
            appointment_type=appointment_type,
            preferred_date=preferred_date,
            duration_minutes=duration
        )
        
        state["scheduling_data"] = {
            "available_slots": slots,
            "selected_slot": None,
            "booking_confirmed": False,
            "event_id": None,
            "confirmation_sent": False
        }
        
        logger.info(f"Found {len(slots)} available slots")
        
    except Exception as e:
        logger.error(f"Calendar check availability error: {e}")
        state["errors"].append(f"Calendar availability error: {str(e)}")
    
    return state


def calendar_book_appointment_tool(state: AgentState, calendar_service, 
                                  sms_service, email_service, **kwargs) -> AgentState:
    """
    Tool: Book appointment and send confirmations.
    
    Args:
        state: Current agent state
        calendar_service: CalendarService instance
        sms_service: SMSService instance
        email_service: EmailService instance
    
    Returns:
        Updated state with booking confirmation
    """
    logger.info("Agent Tool: calendar_book_appointment_tool")
    
    try:
        scheduling = state.get("scheduling_data")
        if not scheduling or not scheduling.get("selected_slot"):
            raise ValueError("No slot selected for booking")
        
        raw = state["raw_intake"]
        slot = scheduling["selected_slot"]
        
        # Create calendar event
        event_id = calendar_service.create_appointment_event(
            title=f"{raw.get('appointment_type')} - {raw.get('patient_name')}",
            start_time=slot["start"],
            end_time=slot["end"],
            description=f"Procedure: {raw.get('procedure', 'N/A')}",
            attendee_email=raw.get("email", ""),
            location=slot.get("location", "Main Clinic")
        )
        
        # Update scheduling data
        scheduling["booking_confirmed"] = True
        scheduling["event_id"] = event_id
        
        # Send SMS confirmation
        if raw.get("phone"):
            sms_service.send_booking_confirmation(
                to_phone=raw["phone"],
                appointment_datetime=slot["start_formatted"],
                doctor=slot.get("doctor", "Doctor TBD"),
                location=slot.get("location", "Main Clinic")
            )
        
        # Send email confirmation
        if raw.get("email"):
            email_service.send_booking_confirmation(
                to_email=raw["email"],
                patient_name=raw.get("patient_name", "Patient"),
                appointment_datetime=slot["start_formatted"],
                doctor=slot.get("doctor", "Doctor TBD"),
                location=slot.get("location", "Main Clinic"),
                prep_summary="Detailed prep instructions will be sent 24 hours before your appointment."
            )
        
        scheduling["confirmation_sent"] = True
        state["scheduling_data"] = scheduling
        
        logger.info(f"Appointment booked: {event_id}")
        
    except Exception as e:
        logger.error(f"Calendar booking error: {e}")
        state["errors"].append(f"Booking error: {str(e)}")
    
    return state


def send_sms_reminder_tool(state: AgentState, sms_service, **kwargs) -> AgentState:
    """
    Tool: Send SMS reminder with prep instructions.
    
    Args:
        state: Current agent state
        sms_service: SMSService instance
    
    Returns:
        Updated state
    """
    logger.info("Agent Tool: send_sms_reminder_tool")
    
    try:
        raw = state["raw_intake"]
        phone = raw.get("phone")
        
        if not phone:
            logger.warning("No phone number provided, skipping SMS")
            return state
        
        # Get prep instructions
        prep_message = state.get("patient_message", "")
        if not prep_message:
            logger.warning("No prep message available, skipping SMS")
            return state
        
        # Truncate for SMS (max 1600 chars)
        prep_brief = prep_message[:1500] + "..." if len(prep_message) > 1500 else prep_message
        
        # Send SMS
        result = sms_service.send_appointment_reminder(
            to_phone=phone,
            appointment_datetime=raw.get("appointment_datetime", "TBD"),
            location="Main Clinic, Floor 2",
            prep_instructions=prep_brief
        )
        
        logger.info(f"SMS reminder sent: {result.get('message_id')}")
        
    except Exception as e:
        logger.error(f"SMS reminder error: {e}")
        state["errors"].append(f"SMS error: {str(e)}")
    
    return state


def send_email_tool(state: AgentState, email_service, **kwargs) -> AgentState:
    """
    Tool: Send email with full prep instructions.
    
    Args:
        state: Current agent state
        email_service: EmailService instance
    
    Returns:
        Updated state
    """
    logger.info("Agent Tool: send_email_tool")
    
    try:
        raw = state["raw_intake"]
        email = raw.get("email")
        
        if not email:
            logger.warning("No email provided, skipping email")
            return state
        
        # Get prep instructions
        prep_message = state.get("patient_message", "")
        if not prep_message:
            logger.warning("No prep message available, skipping email")
            return state
        
        # Send email
        result = email_service.send_prep_instructions(
            to_email=email,
            patient_name=raw.get("patient_name", "Patient"),
            appointment_datetime=raw.get("appointment_datetime", "TBD"),
            prep_message=prep_message
        )
        
        logger.info(f"Email sent: {result.get('message_id')}")
        
    except Exception as e:
        logger.error(f"Email send error: {e}")
        state["errors"].append(f"Email error: {str(e)}")
    
    return state


def patient_chat_tool(state: AgentState, llm_client, retrieval_service, **kwargs) -> AgentState:
    """
    Tool: Handle patient Q&A chat.
    
    This tool:
    1. Takes patient question from state
    2. Retrieves relevant context (protocols, prep instructions)
    3. Generates context-aware response
    4. Updates chat history
    
    Args:
        state: Current agent state (must have patient_question in raw_intake)
        llm_client: LLM client for response generation
        retrieval_service: Protocol retrieval service
    
    Returns:
        Updated state with chat_history
    """
    logger.info("Agent Tool: patient_chat_tool")
    
    try:
        raw = state["raw_intake"]
        question = raw.get("patient_question", "")
        
        if not question:
            raise ValueError("No patient question provided")
        
        # Initialize chat history if needed
        if not state.get("chat_history"):
            state["chat_history"] = []
        
        # Add patient question to history
        state["chat_history"].append({
            "role": "patient",
            "content": question,
            "timestamp": datetime.now().isoformat(),
            "context_used": None
        })
        
        # Retrieve relevant context
        context_docs = []
        if retrieval_service and retrieval_service.is_available():
            protocols = retrieval_service.retrieve_protocols(
                appointment_type=raw.get("appointment_type", ""),
                procedure=raw.get("procedure", ""),
                max_results=2
            )
            context_docs = [p.get("content", "") for p in protocols]
        
        # Add prep instructions to context
        if state.get("patient_message"):
            context_docs.append(state["patient_message"])
        
        # Generate response
        response = None
        if llm_client and llm_client.is_available():
            context_str = "\n\n".join(context_docs) if context_docs else "No specific context available."
            prompt = f"""You are a helpful medical appointment assistant. Answer the patient's question based on the context provided.

Context:
{context_str}

Patient Question: {question}

Provide a clear, helpful answer. If the question is outside the scope of appointment preparation, politely redirect to contacting the clinic."""
            
            response = llm_client.generate_with_prompt(
                "You are a medical appointment assistant.",
                prompt
            )
        
        # Fallback if LLM unavailable or failed
        if not response:
            # Provide intelligent fallback based on question keywords
            question_lower = question.lower()
            if any(word in question_lower for word in ['eat', 'food', 'drink', 'fasting']):
                response = "For specific dietary instructions before your appointment, please refer to your preparation instructions or contact the clinic at least 24 hours before your appointment."
            elif any(word in question_lower for word in ['medication', 'medicine', 'pill', 'drug']):
                response = "For questions about your medications, please consult with your doctor or pharmacist. Some medications may need to be adjusted before your procedure."
            elif any(word in question_lower for word in ['time', 'when', 'arrive', 'schedule']):
                response = "Please arrive 15-30 minutes before your scheduled appointment time. Check your appointment confirmation for specific timing instructions."
            elif any(word in question_lower for word in ['bring', 'need', 'required', 'documents']):
                response = "Please bring your ID, insurance card, and any relevant medical records. Check your preparation instructions for procedure-specific requirements."
            else:
                response = "I'm here to help with appointment preparation questions. For specific medical advice or detailed questions, please contact your clinic directly."
        
        # Add agent response to history
        state["chat_history"].append({
            "role": "agent",
            "content": response,
            "timestamp": datetime.now().isoformat(),
            "context_used": context_docs[:2] if context_docs else None
        })
        
        logger.info("Chat response generated")
        
    except Exception as e:
        logger.error(f"Patient chat error: {e}")
        state["errors"].append(f"Chat error: {str(e)}")
    
    return state


def post_procedure_tool(state: AgentState, rules_engine, email_service, **kwargs) -> AgentState:
    """
    Tool: Generate post-procedure recovery plan.
    
    This tool:
    1. Gets procedure-specific recovery rules
    2. Generates recovery instructions
    3. Sends recovery email
    4. Updates state with post-procedure data
    
    Args:
        state: Current agent state
        rules_engine: RulesEngine instance
        email_service: EmailService instance
    
    Returns:
        Updated state with post_procedure_data
    """
    logger.info("Agent Tool: post_procedure_tool")
    
    try:
        raw = state["raw_intake"]
        procedure = raw.get("procedure", "").lower()
        
        # Get post-procedure rules
        recovery_rules = rules_engine.get_post_procedure_rules(procedure)
        
        # Build recovery instructions
        instructions = _build_recovery_instructions(recovery_rules)
        
        # Create post-procedure data
        post_data = {
            "procedure": procedure,
            "recovery_instructions": instructions,
            "activity_restrictions": recovery_rules.get("activity_restrictions", []),
            "medication_schedule": recovery_rules.get("medication_schedule", []),
            "warning_signs": recovery_rules.get("warning_signs", []),
            "follow_up_needed": recovery_rules.get("follow_up_needed", False),
            "follow_up_timeframe": recovery_rules.get("follow_up_timeframe")
        }
        
        state["post_procedure_data"] = post_data
        
        # Send recovery email
        if raw.get("email"):
            email_service.send_post_procedure_instructions(
                to_email=raw["email"],
                patient_name=raw.get("patient_name", "Patient"),
                procedure=procedure,
                instructions=instructions
            )
        
        logger.info("Post-procedure plan generated")
        
    except Exception as e:
        logger.error(f"Post-procedure tool error: {e}")
        state["errors"].append(f"Post-procedure error: {str(e)}")
    
    return state


# ============================================================================
# HELPER FUNCTIONS FOR NEW TOOLS
# ============================================================================

def _build_recovery_instructions(recovery_rules: dict) -> str:
    """Build formatted recovery instructions."""
    parts = []
    
    parts.append("POST-PROCEDURE RECOVERY INSTRUCTIONS\n")
    
    if recovery_rules.get("rest_period"):
        parts.append(f"REST PERIOD: {recovery_rules['rest_period']}")
    
    if recovery_rules.get("activity_restrictions"):
        parts.append("\nACTIVITY RESTRICTIONS:")
        for restriction in recovery_rules["activity_restrictions"]:
            parts.append(f"  • {restriction}")
    
    if recovery_rules.get("medication_schedule"):
        parts.append("\nMEDICATION SCHEDULE:")
        for med in recovery_rules["medication_schedule"]:
            parts.append(f"  • {med.get('name')}: {med.get('schedule')}")
    
    if recovery_rules.get("diet_guidance"):
        parts.append(f"\nDIET: {recovery_rules['diet_guidance']}")
    
    if recovery_rules.get("warning_signs"):
        parts.append("\n⚠️ CALL DOCTOR IF YOU EXPERIENCE:")
        for sign in recovery_rules["warning_signs"]:
            parts.append(f"  • {sign}")
    
    if recovery_rules.get("follow_up_needed"):
        parts.append(f"\nFOLLOW-UP: Schedule appointment within {recovery_rules.get('follow_up_timeframe', '1-2 weeks')}")
    
    return "\n".join(parts)
