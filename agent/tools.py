"""
Agent Tools - Service wrappers for LangGraph nodes.

This module wraps services as tools for the THREE-PHASE agent workflow:
- Phase I: Triage & Intake
- Phase II: Admin Prep  
- Phase III: Clinical Briefing
"""

from typing import Dict, Any
from datetime import datetime, timedelta
import logging
import json

from agent.state import AgentState
from agent.prompts import (
    SYMPTOM_NORMALIZATION_PROMPT,
    FOLLOW_UP_QUESTIONS_PROMPT,
    TRIAGE_CLASSIFICATION_PROMPT,
    build_prep_prompt,
    build_clinical_prompt,
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
    3. Enriches intake with EHR/FHIR data if fhir_patient_id is provided
    4. Identifies missing information
    5. Generates follow-up questions if needed
    
    Args:
        state: Current agent state
        llm_client: LLM client for symptom normalization
    
    Returns:
        Updated state with intake_data and ehr_context populated
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
        
        # Check for FHIR patient ID and enrich with EHR data if available
        fhir_patient_id = raw.get("fhir_patient_id")
        if fhir_patient_id:
            try:
                from services.ehr_service import EHRService
                ehr_service = EHRService()
                
                logger.info(f"Enriching intake with EHR data for patient: {fhir_patient_id}")
                enriched_data = ehr_service.enrich_intake(raw, fhir_patient_id)
                
                # Update raw_intake with enriched data
                state["raw_intake"].update(enriched_data.get("intake_data", {}))
                
                # Store EHR context
                state["ehr_context"] = enriched_data.get("ehr_context", {})
                
                state["metadata"]["steps"].append({
                    "step": "ehr_enrichment",
                    "phase": "I",
                    "timestamp": datetime.now().isoformat(),
                    "description": "EHR data enrichment successful",
                    "fhir_patient_id": fhir_patient_id
                })
                
                logger.info("EHR enrichment successful")
                
            except Exception as ehr_error:
                logger.warning(f"EHR enrichment failed: {ehr_error}")
                state["metadata"]["steps"].append({
                    "step": "ehr_enrichment_failed",
                    "phase": "I",
                    "timestamp": datetime.now().isoformat(),
                    "description": f"EHR enrichment failed: {str(ehr_error)}",
                    "fhir_patient_id": fhir_patient_id
                })
                # Continue with manual data - don't fail the entire intake
        
        # Extract chief complaint (may have been enriched by EHR)
        raw = state["raw_intake"]  # Re-read after potential enrichment
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
            "needs_clarification": intake_data["needs_clarification"],
            "ehr_enriched": fhir_patient_id is not None
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

        # Safe attribute access in case rules is None or unexpected type
        requires_adult   = getattr(rules, "requires_responsible_adult", False)
        fasting_required = getattr(rules, "fasting_required", False)

        # Build admin prep data
        admin_prep = {
            "insurance_verification_needed": True,
            "copay_reminder": "Please be prepared to pay your copay at check-in",
            "required_documents": _build_document_list(rules, protocols),
            "arrival_instructions": _build_arrival_instructions(rules, raw),
            "transport_instructions": _build_transport_instructions(rules) if requires_adult else None,
            "fasting_instructions": _build_fasting_instructions(rules, raw) if fasting_required else None,
            "diet_instructions": _build_diet_instructions(rules, protocols),
            "paperwork_reminders": _build_paperwork_reminders(protocols),
            "reschedule_warnings": _build_reschedule_warnings(state.get("triage_data") or {}),
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
    Tool: Generate a personalized patient preparation message.

    Uses the new context-aware prompt builder so the LLM generates
    a procedure-specific guide directly — no static template rewriting.
    """
    logger.info("Agent Tool: patient_message_tool")

    state["metadata"]["steps"].append({
        "step": "patient_message_generation",
        "phase": "III",
        "timestamp": datetime.now().isoformat(),
        "description": "Generating personalized preparation guide"
    })

    try:
        # Build rich context dict from the accumulated state
        raw = state.get("raw_intake", {})
        intake = state.get("intake_data", {})

        ctx = {
            "patient_name":    raw.get("patient_name", "Patient"),
            "age_group":       raw.get("age_group", ""),
            "chief_complaint": intake.get("chief_complaint") or raw.get("chief_complaint", ""),
            "symptoms":        raw.get("symptoms_description", ""),
            "current_medications": raw.get("current_medications", []),
            "allergies":       raw.get("allergies", []),
            "prior_conditions":raw.get("prior_conditions", []),
            "appointment_type":raw.get("appointment_type", ""),
            "procedure":       raw.get("procedure", ""),
            "clinician_name":  raw.get("clinician_name", "your doctor"),
            "appointment_datetime": raw.get("appointment_datetime", ""),
            "hospital_data":   state.get("hospital_data", {}),
        }

        if llm_client and llm_client.is_available():
            system_prompt, user_prompt = build_prep_prompt(ctx)
            final = llm_client.generate_with_prompt(system_prompt, user_prompt)
            state["llm_used"] = final is not None
            if not final:
                # LLM failed — fall back to deterministic draft
                final = _build_patient_message_draft(state)
        else:
            final = _build_patient_message_draft(state)
            state["llm_used"] = False

        state["patient_message"] = final
        state["final_message"]   = final  # backward compat

        state["metadata"]["steps"].append({
            "step": "patient_message_complete",
            "phase": "III",
            "timestamp": datetime.now().isoformat(),
            "llm_used": state["llm_used"],
            "message_length": len(final) if final else 0
        })

    except Exception as e:
        logger.error(f"Patient message tool error: {e}")
        state["errors"].append(f"Patient message error: {str(e)}")
        # Last-resort fallback
        if not state.get("patient_message"):
            state["patient_message"] = _build_patient_message_draft(state)

    return state


def clinician_summary_tool(state: AgentState, llm_client=None, **kwargs) -> AgentState:
    """
    Tool: Generate structured clinician-facing pre-visit summary.
    Uses context-aware LLM prompt when available; falls back to
    deterministic formatting otherwise.
    """
    logger.info("Agent Tool: clinician_summary_tool")

    try:
        raw    = state.get("raw_intake", {})
        intake = state.get("intake_data", {})
        triage = state.get("triage_data", {})

        # Try LLM-generated clinical note
        if llm_client and llm_client.is_available():
            ctx = {
                "patient_name":    raw.get("patient_name", "Patient"),
                "age_group":       raw.get("age_group", ""),
                "chief_complaint": intake.get("chief_complaint") or raw.get("chief_complaint", ""),
                "symptoms":        raw.get("symptoms_description", ""),
                "current_medications": raw.get("current_medications", []),
                "allergies":       raw.get("allergies", []),
                "prior_conditions":raw.get("prior_conditions", []),
                "appointment_type":raw.get("appointment_type", ""),
                "procedure":       raw.get("procedure", ""),
                "hospital_data":   state.get("hospital_data", {}),
            }
            system_prompt, user_prompt = build_clinical_prompt(ctx)
            generated = llm_client.generate_with_prompt(system_prompt, user_prompt)
            if generated:
                state["clinician_summary"] = generated
                return state

        # Deterministic fallback
        briefing = state.get("clinical_briefing", {})
        if not briefing and not intake:
            state["clinician_summary"] = "Clinical briefing data not available."
            return state

        parts = []
        parts.append(f"PRE-VISIT SUMMARY")
        parts.append(f"Patient: {raw.get('patient_name', 'Unknown')}")
        parts.append(f"Chief Complaint: {intake.get('chief_complaint', 'Not provided')}")
        if intake.get("chief_complaint_normalized"):
            parts.append(f"Clinical Term: {intake['chief_complaint_normalized']}")
        parts.append("")

        if triage:
            parts.append(f"TRIAGE: {triage.get('urgency_level', 'Unknown').upper()}")
            if triage.get("red_flags"):
                parts.append(f"Red Flags: {', '.join(triage['red_flags'])}")
            parts.append("")

        if intake.get("current_medications"):
            parts.append("CURRENT MEDICATIONS:")
            for med in intake["current_medications"]:
                parts.append(f"  - {med}")
            parts.append("")

        if briefing and briefing.get("allergy_alerts"):
            parts.append(f"ALLERGIES: {', '.join(briefing['allergy_alerts'])}")
            parts.append("")

        prep_status = briefing.get("prep_status", "Pending") if briefing else "Pending"
        parts.append(f"PREP STATUS: {prep_status}")

        state["clinician_summary"] = "\n".join(parts)

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
    """Build comprehensive patient message from all phases."""
    parts = []
    
    # Header
    raw = state["raw_intake"]
    intake = state.get("intake_data", {})
    admin = state.get("admin_prep_data", {})
    triage = state.get("triage_data", {})
    hospital_data = state.get("hospital_data", {})
    
    patient_name = raw.get('patient_name', 'Patient')
    procedure = raw.get('procedure', 'Consultation')
    appointment_type = raw.get('appointment_type', 'Consultation')
    clinician_name = raw.get('clinician_name', 'your doctor')
    appointment_datetime = raw.get('appointment_datetime', 'your scheduled time')
    
    parts.append(f"APPOINTMENT PREPARATION GUIDE")
    parts.append(f"")
    parts.append(f"Dear {patient_name},")
    parts.append(f"")
    parts.append(f"This guide will help you prepare for your upcoming {appointment_type} appointment with {clinician_name} on {appointment_datetime}.")
    parts.append(f"")
    
    # Appointment Overview
    parts.append(f"APPOINTMENT OVERVIEW:")
    parts.append(f"")
    parts.append(f"Procedure: {procedure}")
    parts.append(f"Type: {appointment_type}")
    parts.append(f"Doctor: {clinician_name}")
    parts.append(f"Date & Time: {appointment_datetime}")
    
    # Hospital information if available
    if hospital_data and hospital_data.get("doctors"):
        selected_doctor = hospital_data["doctors"][0] if hospital_data["doctors"] else {}
        if selected_doctor:
            parts.append(f"Hospital: {selected_doctor.get('hospital', 'Hospital')}")
            parts.append(f"Location: {selected_doctor.get('hospital_location', 'Location')}")
    
    parts.append(f"")
    
    # Reason for visit
    if intake and intake.get("chief_complaint"):
        parts.append(f"REASON FOR VISIT:")
        parts.append(f"")
        parts.append(f"You are being seen for: {intake['chief_complaint']}")
        if raw.get("symptoms_description"):
            parts.append(f"Symptoms: {raw['symptoms_description']}")
        if intake.get("chief_complaint_normalized"):
            parts.append(f"Clinical assessment: {intake['chief_complaint_normalized']}")
        parts.append(f"")
    
    # Medical history context
    if raw.get("current_medications") or raw.get("allergies") or raw.get("prior_conditions"):
        parts.append(f"YOUR MEDICAL INFORMATION:")
        parts.append(f"")
        if raw.get("current_medications"):
            meds = raw["current_medications"]
            parts.append(f"Current Medications: {', '.join(meds) if isinstance(meds, list) else meds}")
        if raw.get("allergies"):
            allergies = raw["allergies"]
            parts.append(f"Allergies: {', '.join(allergies) if isinstance(allergies, list) else allergies}")
        if raw.get("prior_conditions"):
            conditions = raw["prior_conditions"]
            parts.append(f"Medical History: {', '.join(conditions) if isinstance(conditions, list) else conditions}")
        parts.append(f"")
    
    # Urgency level if not routine
    if triage and triage.get("urgency_level") and triage["urgency_level"] != "routine":
        urgency = triage["urgency_level"].upper()
        parts.append(f"⚠️ URGENCY LEVEL: {urgency}")
        parts.append(f"")
        if triage.get("red_flags"):
            parts.append(f"Important clinical indicators have been identified:")
            for flag in triage["red_flags"]:
                parts.append(f"  • {flag}")
            parts.append(f"")
    
    # What to bring
    parts.append(f"WHAT TO BRING TO YOUR APPOINTMENT:")
    parts.append(f"")
    if admin and admin.get("required_documents"):
        for doc in admin["required_documents"]:
            parts.append(f"  • {doc}")
    else:
        parts.append(f"  • Photo ID (driver's license or passport)")
        parts.append(f"  • Insurance card and any referral forms")
        parts.append(f"  • List of current medications with dosages")
        parts.append(f"  • Any recent test results or medical records")
        parts.append(f"  • Payment method for copay")
    parts.append(f"")
    
    # Arrival instructions
    parts.append(f"ARRIVAL INSTRUCTIONS:")
    parts.append(f"")
    if admin and admin.get("arrival_instructions"):
        parts.append(admin["arrival_instructions"])
    else:
        parts.append(f"Please arrive 15 minutes before your scheduled appointment time to complete check-in.")
        parts.append(f"This allows time for registration, insurance verification, and any necessary paperwork.")
    parts.append(f"")
    
    # Fasting instructions if applicable
    if admin and admin.get("fasting_instructions"):
        parts.append(f"FASTING REQUIREMENTS:")
        parts.append(f"")
        parts.append(admin["fasting_instructions"])
        parts.append(f"")
    
    # Transportation if needed
    if admin and admin.get("transport_instructions"):
        parts.append(f"TRANSPORTATION:")
        parts.append(f"")
        parts.append(admin["transport_instructions"])
        parts.append(f"")
    
    # Diet instructions if applicable
    if admin and admin.get("diet_instructions"):
        parts.append(f"DIETARY GUIDELINES:")
        parts.append(f"")
        parts.append(admin["diet_instructions"])
        parts.append(f"")
    
    # Medication instructions
    parts.append(f"MEDICATION INSTRUCTIONS:")
    parts.append(f"")
    if raw.get("current_medications"):
        parts.append(f"Continue taking your regular medications unless specifically instructed otherwise by your doctor.")
        parts.append(f"Bring a complete list of all medications, including over-the-counter drugs and supplements.")
    else:
        parts.append(f"If you take any medications, bring a complete list including dosages.")
    parts.append(f"")
    
    # Preparation checklist
    if admin and admin.get("patient_readiness_checklist"):
        parts.append(f"PREPARATION CHECKLIST:")
        parts.append(f"")
        for item in admin["patient_readiness_checklist"]:
            parts.append(f"  ☐ {item}")
        parts.append(f"")
    
    # What to expect
    parts.append(f"WHAT TO EXPECT:")
    parts.append(f"")
    if "consultation" in procedure.lower() or "consultation" in appointment_type.lower():
        parts.append(f"During your consultation, the doctor will:")
        parts.append(f"  • Review your medical history and current symptoms")
        parts.append(f"  • Perform a physical examination")
        parts.append(f"  • Discuss diagnosis and treatment options")
        parts.append(f"  • Answer any questions you may have")
        parts.append(f"  • Provide next steps and follow-up recommendations")
    elif "imaging" in procedure.lower() or "mri" in procedure.lower() or "ct" in procedure.lower():
        parts.append(f"During your imaging appointment:")
        parts.append(f"  • You will be positioned for the scan")
        parts.append(f"  • The procedure is painless and non-invasive")
        parts.append(f"  • You may need to remain still during the scan")
        parts.append(f"  • Results will be reviewed by a radiologist")
        parts.append(f"  • Your doctor will discuss findings with you")
    elif "surgery" in procedure.lower():
        parts.append(f"For your surgical procedure:")
        parts.append(f"  • Pre-operative assessment will be completed")
        parts.append(f"  • Anesthesia options will be discussed")
        parts.append(f"  • Post-operative care instructions will be provided")
        parts.append(f"  • Recovery timeline will be explained")
    else:
        parts.append(f"Your healthcare team will guide you through each step of your appointment.")
        parts.append(f"Please feel free to ask questions at any time.")
    parts.append(f"")
    
    # Important warnings
    if triage and triage.get("red_flags"):
        parts.append(f"⚠️ IMPORTANT - SEEK IMMEDIATE CARE IF YOU EXPERIENCE:")
        parts.append(f"")
        for flag in triage["red_flags"]:
            parts.append(f"  • {flag}")
        parts.append(f"")
        parts.append(f"If symptoms worsen before your appointment, call the clinic immediately or go to the emergency room.")
        parts.append(f"")
    
    # Questions to ask
    parts.append(f"QUESTIONS TO CONSIDER ASKING YOUR DOCTOR:")
    parts.append(f"")
    parts.append(f"  • What is causing my symptoms?")
    parts.append(f"  • What treatment options are available?")
    parts.append(f"  • Are there any lifestyle changes I should make?")
    parts.append(f"  • When should I expect to see improvement?")
    parts.append(f"  • What are the next steps in my care?")
    parts.append(f"  • When should I schedule a follow-up?")
    parts.append(f"")
    
    # Contact information
    parts.append(f"NEED TO RESCHEDULE OR HAVE QUESTIONS?")
    parts.append(f"")
    parts.append(f"Please contact the clinic as soon as possible if you:")
    parts.append(f"  • Need to reschedule your appointment")
    parts.append(f"  • Have questions about preparation instructions")
    parts.append(f"  • Experience worsening symptoms")
    parts.append(f"  • Need clarification on any instructions")
    parts.append(f"")
    
    # Closing
    parts.append(f"We look forward to seeing you at your appointment. Our team is committed to providing you with excellent care.")
    parts.append(f"")
    parts.append(f"Important Note: This is a preparation guide based on your intake information. It is not a substitute for medical advice. Always follow specific instructions provided by your healthcare team.")
    
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

# ============================================================================
# ============================================================================
# NEW CONVERSATIONAL & SCHEDULING NODES
# ============================================================================

def conversation_intake_node(state: AgentState, llm_client=None, **kwargs) -> AgentState:
    """
    Accepts free text / partial input and extracts structured fields dynamically.
    Updates AgentState dynamically.
    """
    logger.info("Agent Tool: conversation_intake_node")
    state["metadata"]["steps"].append({
        "step": "conversation_intake",
        "timestamp": datetime.now().isoformat(),
        "description": "Extracting structured intent from free text"
    })
    
    raw = state.get("raw_intake", {})
    query = raw.get("conversational_query", "")
    
    if not query and state.get("conversation_data", {}).get("current_transcript"):
        query = state["conversation_data"]["current_transcript"]

    # Basic entity extraction (could be enhanced with LLM if provided)
    query_lower = query.lower()
    
    # Extract Patient Name: "I am [Name]", "My name is [Name]", "This is [Name]"
    import re
    name_match = re.search(r"(?:i am|my name is|this is)\s+([a-z\s]+)(?:and|\.|$)", query_lower)
    if name_match:
        state["raw_intake"]["patient_name"] = name_match.group(1).strip().title()

    # We populate raw_intake by inferring from text
    # Procedures / Appointment Types
    procedure_map = {
        "colonoscopy": ("Colonoscopy", "Procedure"),
        "mri": ("MRI", "Imaging"),
        "ct scan": ("CT Scan", "Imaging"),
        "checkup": ("Checkup", "Consultation"),
        "consult": ("Consultation", "Consultation"),
        "surgery": ("Surgery", "Surgery"),
        "blood test": ("Blood Test", "Lab Work")
    }
    
    for key, (proc, atype) in procedure_map.items():
        if key in query_lower:
            state["raw_intake"]["procedure"] = proc
            state["raw_intake"]["appointment_type"] = atype
            break
        
    if "next week" in query_lower:
        next_week = datetime.now() + timedelta(days=7)
        state["raw_intake"]["preferred_date"] = next_week.strftime("%Y-%m-%d")
    elif "tomorrow" in query_lower:
        tomorrow = datetime.now() + timedelta(days=1)
        state["raw_intake"]["preferred_date"] = tomorrow.strftime("%Y-%m-%d")
        
    # Map conversational query to legacy fields if missing
    if query:
        if not state["raw_intake"].get("chief_complaint"):
            state["raw_intake"]["chief_complaint"] = query
        if not state["raw_intake"].get("symptoms_description"):
            state["raw_intake"]["symptoms_description"] = query
            
        # If we found a name but it wasn't in raw_intake initially, ensure it's there
        if "patient_name" in state["raw_intake"] and not raw.get("patient_name"):
            raw["patient_name"] = state["raw_intake"]["patient_name"]

    if "conversation_data" not in state or state["conversation_data"] is None:
        state["conversation_data"] = {
            "missing_fields": [],
            "suggested_options": {},
            "confidence_score": 1.0,
            "confidence_scores": {},
            "current_transcript": query,
            "is_voice": raw.get("input_mode") == "voice",
            "input_mode": raw.get("input_mode", "text"),
            "user_confirmations": {}
        }
        
    return state


def missing_info_detector_node(state: AgentState, **kwargs) -> AgentState:
    """
    Checks if there are required fields missing from the extracted structured context.
    Calls missing_field_detector service to detect missing fields and calculate confidence.
    """
    logger.info("Agent Tool: missing_info_detector_node")
    state["metadata"]["steps"].append({
        "step": "missing_info_detector",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        from services.missing_field_detector import detect_missing_fields
        
        raw_intake = state.get("raw_intake", {})
        appointment_type = raw_intake.get("appointment_type", "")
        
        # Detect missing fields using the service
        result = detect_missing_fields(raw_intake, appointment_type)
        
        # Update conversation_data
        if "conversation_data" not in state or state["conversation_data"] is None:
            state["conversation_data"] = {}
            
        state["conversation_data"]["missing_fields"] = result["missing_fields"]
        state["conversation_data"]["confidence_score"] = result["confidence_score"]
        state["conversation_data"]["confidence_scores"] = result["confidence_scores"]
        state["conversation_data"]["suggested_options"] = result["suggested_options"]
        
        logger.info(
            f"Missing fields: {len(result['missing_fields'])}, "
            f"Confidence: {result['confidence_score']:.2f}"
        )
        
    except Exception as e:
        logger.error(f"Missing info detector error: {e}")
        state["errors"].append(f"Missing info detector error: {str(e)}")
        # Set default values to prevent downstream errors
        if "conversation_data" not in state:
            state["conversation_data"] = {}
        state["conversation_data"]["missing_fields"] = []
        state["conversation_data"]["confidence_score"] = 1.0
        
    return state

def clarification_agent_node(state: AgentState, **kwargs) -> AgentState:
    """
    Asks only necessary questions based on missing fields.
    Provides suggested options (buttons/dropdowns).
    """
    logger.info("Agent Tool: clarification_agent_node")
    state["metadata"]["steps"].append({
        "step": "clarification_agent",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        conversation_data = state.get("conversation_data", {})
        missing_fields = conversation_data.get("missing_fields", [])
        suggested_options = conversation_data.get("suggested_options", {})
        
        if not missing_fields:
            # No missing fields, no clarification needed
            state["draft_message"] = ""
            return state
        
        # Generate follow-up questions
        questions = []
        
        for field in missing_fields:
            if field == "chief_complaint":
                questions.append("What is the main reason for your visit?")
            elif field == "appointment_type":
                questions.append("What type of appointment do you need?")
                if "appointment_type" in suggested_options:
                    questions.append(f"Options: {', '.join(suggested_options['appointment_type'])}")
            elif field == "symptoms_description":
                questions.append("Can you describe your symptoms in more detail?")
            elif field == "age_group":
                questions.append("What is your age group?")
                if "age_group" in suggested_options:
                    questions.append(f"Options: {', '.join(suggested_options['age_group'])}")
            elif field == "current_medications":
                questions.append("Are you currently taking any medications?")
            elif field == "allergies":
                questions.append("Do you have any allergies?")
            elif field == "procedure":
                questions.append("What kind of procedure or appointment do you need?")
                if "procedure" in suggested_options:
                    questions.append(f"Options: {', '.join(suggested_options['procedure'])}")
            elif field == "patient_name":
                questions.append("Could you please provide your full name for the booking?")
        
        # Combine questions
        clarification_message = "\n\n".join(questions)
        state["draft_message"] = clarification_message
        
        logger.info(f"Generated {len(questions)} follow-up questions")
        
    except Exception as e:
        logger.error(f"Clarification agent error: {e}")
        state["errors"].append(f"Clarification agent error: {str(e)}")
        state["draft_message"] = "Please provide more information about your appointment needs."
    
    return state

def voice_input_node(state: AgentState, **kwargs) -> AgentState:
    """
    Accepts voice -> converts to structured input. Falls back to text if low confidence.
    """
    logger.info("Agent Tool: voice_input_node")
    state["metadata"]["steps"].append({
        "step": "voice_input",
        "timestamp": datetime.now().isoformat()
    })
    
    raw = state.get("raw_intake", {})
    voice_transcript = raw.get("voice_transcript", "")
    
    if voice_transcript:
        if "conversation_data" not in state or state["conversation_data"] is None:
             state["conversation_data"] = {}
        state["conversation_data"]["is_voice"] = True
        state["conversation_data"]["current_transcript"] = voice_transcript
        
        # Merge transcript into conversational query
        state["raw_intake"]["conversational_query"] = voice_transcript
        
    return state

def scheduling_orchestrator_node(state: AgentState, **kwargs) -> AgentState:
    """
    Replaces synthetic scheduling.
    Slot generation logic (time, doctor, availability).
    Constraint validation (prep time, urgency).
    Smart slot selection. Auto-booking + confirmation.
    Writes booking into state + DB.
    """
    logger.info("Agent Tool: scheduling_orchestrator_node")
    state["metadata"]["steps"].append({
        "step": "scheduling_orchestrator",
        "timestamp": datetime.now().isoformat()
    })
    
    raw = state.get("raw_intake", {})
    procedure = raw.get("procedure", "General")
    selected_doc = raw.get("clinician_name")
    selected_time = raw.get("appointment_datetime")

    now_dt = datetime.now()

    if "scheduling_data" not in state or state["scheduling_data"] is None:
        state["scheduling_data"] = {
            "selected_slot": None,
            "booking_confirmed": False,
            "event_id": None,
            "confirmation_sent": False
        }

    # Auto-booking + confirmation
    if not state["scheduling_data"]["booking_confirmed"]:
        if selected_doc and selected_time:
            # We have the selection from the frontend UI
            state["scheduling_data"]["selected_slot"] = {
                "datetime": selected_time,
                "doctor": selected_doc,
                "location": "Main Clinic"
            }
        else:
            # Fallback mock logic for pure backend execution
            days_to_add = 3 if "colonoscopy" in procedure.lower() else 1
            calculated_date = now_dt + timedelta(days=days_to_add)
            selected = {
                "datetime": f"{calculated_date.strftime('%Y-%m-%d')}T09:00:00Z", 
                "doctor": "Dr. Smith", 
                "location": "Main Clinic"
            }
            state["scheduling_data"]["selected_slot"] = selected
            state["raw_intake"]["appointment_datetime"] = selected["datetime"]
            state["raw_intake"]["clinician_name"] = selected["doctor"]

        state["scheduling_data"]["booking_confirmed"] = True
        state["scheduling_data"]["event_id"] = f"EVN-{int(now_dt.timestamp())}"
        state["scheduling_data"]["confirmation_sent"] = True

    return state


def hospital_suggestion_node(state: AgentState, **kwargs) -> AgentState:
    """
    Search and suggest suitable hospitals based on ratings and proximity to procedure requirements.
    Calls hospital_lookup_service to find and rank hospitals.
    """
    logger.info("Agent Tool: hospital_suggestion_node")
    state["metadata"]["steps"].append({
        "step": "hospital_suggestion",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        from services.hospital_lookup_service import HospitalLookupService
        
        raw_intake = state.get("raw_intake", {})
        procedure = raw_intake.get("procedure", "")
        
        if not procedure:
            logger.warning("No procedure specified, skipping hospital lookup")
            state["hospital_data"] = {"hospitals": [], "suggested_hospitals": []}
            return state
        
        # Initialize hospital lookup service in REAL mode
        hospital_service = HospitalLookupService(mock_mode=False)
        logger.info("[HOSPITAL LOOKUP] Using REAL mode (Geoapify)")
        
        # Search for hospitals
        hospitals = hospital_service.search_hospitals(procedure)
        
        # Extract doctors from hospitals
        all_doctors = []
        for hospital in hospitals:
            doctors = hospital.get("doctors", [])
            all_doctors.extend(doctors)
        
        # Update hospital_data
        state["hospital_data"] = {
            "hospitals": hospitals,
            "suggested_hospitals": hospitals,  # For backward compatibility
            "selected_hospital": None,
            "doctors": all_doctors,
            "selected_doctor": None,
            "selected_slot": None,
            "search_query": procedure
        }
        
        logger.info(f"Found {len(hospitals)} hospitals with {len(all_doctors)} doctors")
        
    except Exception as e:
        logger.error(f"Hospital suggestion error: {e}")
        state["errors"].append(f"Hospital suggestion error: {str(e)}")
        state["hospital_data"] = {"hospitals": [], "suggested_hospitals": []}
    
    return state


# ============================================================================
# AGENTIC UPGRADE: NEW TOOLS FOR VOICE, EHR, HOSPITAL LOOKUP
# ============================================================================

def voice_input_node_tool(state: AgentState, **kwargs) -> AgentState:
    """
    Voice Input Node: Logs voice input detection.
    
    This node checks if input mode is voice and logs the detection.
    The actual transcription is done by /api/transcribe before this node.
    
    Args:
        state: Current agent state
    
    Returns:
        Updated state with voice input logged
    """
    logger.info("Agent Tool: voice_input_node_tool")
    
    conversation_data = state.get("conversation_data", {})
    
    if conversation_data.get("input_mode") == "voice":
        state["reasoning_trace"].append({
            "node": "voice_input",
            "action": "Voice input detected",
            "transcript": conversation_data.get("current_transcript", ""),
            "timestamp": datetime.now().isoformat()
        })
        logger.info("Voice input mode detected")
    else:
        state["reasoning_trace"].append({
            "node": "voice_input",
            "action": "Text input mode",
            "timestamp": datetime.now().isoformat()
        })
    
    return state


def conversation_intake_node_tool(state: AgentState, llm_client=None, **kwargs) -> AgentState:
    """
    Conversation Intake Node: Extracts structured data from conversational query.
    
    This node uses LLM (if available) to extract structured fields from
    free-form conversational text.
    
    Args:
        state: Current agent state
        llm_client: LLM client for extraction
    
    Returns:
        Updated state with extracted structured data
    """
    logger.info("Agent Tool: conversation_intake_node_tool")
    
    state["reasoning_trace"].append({
        "node": "conversation_intake",
        "action": "Extracting structured data from conversational query",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        conversation_data = state.get("conversation_data", {})
        transcript = conversation_data.get("current_transcript", "")
        
        if not transcript:
            # No transcript to process
            return state
        
        # Use LLM to extract structured fields if available
        if llm_client and llm_client.is_available():
            extraction_prompt = f"""Extract the following information from the patient's message:
- Patient name (if mentioned)
- Age and Gender (if mentioned)
- Chief complaint or reason for visit
- Symptoms description
- Duration and Severity
- Associated complaints
- Appointment type (Consultation, Surgery, Imaging, Lab Work, Procedure)
- Procedure name (if mentioned)
- Current medications, Allergies, Prior conditions
- Location/Preferences (if mentioned)
- Preferred timing (if mentioned)

Patient message: {transcript}

Return the extracted information in a structured JSON format ONLY. Do not include markdown."""
            
            extracted = llm_client.generate_with_prompt(
                "You are a medical intake assistant extracting structured information.",
                extraction_prompt
            )
            
            if extracted:
                # Parse extracted data and update raw_intake
                # This is a simplified version - could be enhanced with JSON parsing
                state["reasoning_trace"].append({
                    "node": "conversation_intake",
                    "action": "LLM extraction completed",
                    "extracted": extracted[:200],
                    "timestamp": datetime.now().isoformat()
                })
        
        # Basic keyword extraction as fallback
        transcript_lower = transcript.lower()
        raw_intake = state.get("raw_intake", {})
        
        # Extract procedure keywords
        if "colonoscopy" in transcript_lower:
            raw_intake["procedure"] = "Colonoscopy"
            raw_intake["appointment_type"] = "Procedure"
        elif "mri" in transcript_lower:
            raw_intake["procedure"] = "MRI"
            raw_intake["appointment_type"] = "Imaging"
        elif "ct scan" in transcript_lower or "ct" in transcript_lower:
            raw_intake["procedure"] = "CT Scan"
            raw_intake["appointment_type"] = "Imaging"
        elif "surgery" in transcript_lower:
            raw_intake["appointment_type"] = "Surgery"
        
        # Update chief complaint if not set
        if not raw_intake.get("chief_complaint"):
            raw_intake["chief_complaint"] = transcript
        
        state["raw_intake"] = raw_intake
        
    except Exception as e:
        logger.error(f"Conversation intake error: {e}")
        state["errors"].append(f"Conversation intake error: {str(e)}")
    
    return state


def missing_info_detector_node_tool(state: AgentState, **kwargs) -> AgentState:
    """
    Missing Info Detector Node: Identifies missing required fields.
    
    This node calls the missing_field_detector service to identify
    missing fields and calculate confidence score.
    
    Args:
        state: Current agent state
    
    Returns:
        Updated state with missing fields and confidence score
    """
    logger.info("Agent Tool: missing_info_detector_node_tool")
    
    state["reasoning_trace"].append({
        "node": "missing_info_detector",
        "action": "Detecting missing required fields",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        from services.missing_field_detector import detect_missing_fields
        
        raw_intake = state.get("raw_intake", {})
        appointment_type = raw_intake.get("appointment_type", "")
        
        # Detect missing fields
        result = detect_missing_fields(raw_intake, appointment_type)
        
        # Update conversation_data
        conversation_data = state.get("conversation_data", {})
        conversation_data["missing_fields"] = result["missing_fields"]
        conversation_data["confidence_score"] = result["confidence_score"]
        conversation_data["confidence_scores"] = result["confidence_scores"]
        conversation_data["suggested_options"] = result["suggested_options"]
        
        state["conversation_data"] = conversation_data
        
        state["reasoning_trace"].append({
            "node": "missing_info_detector",
            "action": "Missing field detection complete",
            "missing_count": len(result["missing_fields"]),
            "confidence": result["confidence_score"],
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(
            f"Missing fields: {len(result['missing_fields'])}, "
            f"Confidence: {result['confidence_score']:.2f}"
        )
        
    except Exception as e:
        logger.error(f"Missing info detector error: {e}")
        state["errors"].append(f"Missing info detector error: {str(e)}")
        # Set default values to prevent downstream errors
        if "conversation_data" not in state:
            state["conversation_data"] = {}
        state["conversation_data"]["missing_fields"] = []
        state["conversation_data"]["confidence_score"] = 1.0
    
    return state


def clarification_agent_node_tool(state: AgentState, **kwargs) -> AgentState:
    """
    Clarification Agent Node: Generates follow-up questions for missing fields.
    
    This node generates intelligent follow-up questions based on
    missing fields identified by the missing_info_detector.
    
    Args:
        state: Current agent state
    
    Returns:
        Updated state with follow-up questions in draft_message
    """
    logger.info("Agent Tool: clarification_agent_node_tool")
    
    state["reasoning_trace"].append({
        "node": "clarification_agent",
        "action": "Generating follow-up questions",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        conversation_data = state.get("conversation_data", {})
        missing_fields = conversation_data.get("missing_fields", [])
        suggested_options = conversation_data.get("suggested_options", {})
        
        if not missing_fields:
            # No missing fields, no clarification needed
            state["draft_message"] = ""
            return state
        
        # Generate follow-up questions
        questions = []
        
        # Priority order for missing fields to ask about
        priority_fields = ["patient_name", "chief_complaint", "appointment_type", "procedure", "symptoms_description", "age_group", "allergies", "current_medications"]
        
        questions_asked = 0
        for field in priority_fields:
            if field in missing_fields:
                if field == "chief_complaint":
                    questions.append("What is the main reason for your visit?")
                elif field == "appointment_type":
                    questions.append("What type of appointment do you need?")
                    if "appointment_type" in suggested_options:
                        questions.append(f"Options: {', '.join(suggested_options['appointment_type'])}")
                elif field == "symptoms_description":
                    questions.append("Can you describe your symptoms in more detail?")
                elif field == "age_group":
                    questions.append("What is your age group?")
                    if "age_group" in suggested_options:
                        questions.append(f"Options: {', '.join(suggested_options['age_group'])}")
                elif field == "current_medications":
                    questions.append("Are you currently taking any medications?")
                elif field == "allergies":
                    questions.append("Do you have any allergies?")
                elif field == "procedure":
                    questions.append("What kind of procedure or appointment do you need?")
                    if "procedure" in suggested_options:
                        questions.append(f"Options: {', '.join(suggested_options['procedure'])}")
                elif field == "patient_name":
                    questions.append("Could you please provide your full name for the booking?")
                
                questions_asked += 1
                # Only ask about 2 missing items at a time to avoid overwhelming the patient
                if questions_asked >= 2:
                    break
        
        # Combine questions
        clarification_message = "\n\n".join(questions)
        state["draft_message"] = clarification_message
        
        state["reasoning_trace"].append({
            "node": "clarification_agent",
            "action": "Follow-up questions generated",
            "question_count": len(questions),
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Generated {len(questions)} follow-up questions")
        
    except Exception as e:
        logger.error(f"Clarification agent error: {e}")
        state["errors"].append(f"Clarification agent error: {str(e)}")
        state["draft_message"] = "Please provide more information about your appointment needs."
    
    return state


def hospital_suggestion_node_tool(state: AgentState, **kwargs) -> AgentState:
    """
    Hospital Suggestion Node: Suggests nearby hospitals based on procedure.
    
    This node calls the hospital_lookup_service to find and rank
    hospitals suitable for the patient's procedure.
    
    Args:
        state: Current agent state
    
    Returns:
        Updated state with hospital_data populated
    """
    logger.info("Agent Tool: hospital_suggestion_node_tool")
    
    state["reasoning_trace"].append({
        "node": "hospital_suggestion",
        "action": "Searching for suitable hospitals",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        from services.hospital_lookup_service import HospitalLookupService
        
        raw_intake = state.get("raw_intake", {})
        procedure = raw_intake.get("procedure", "")
        
        if not procedure:
            logger.warning("No procedure specified, skipping hospital lookup")
            state["hospital_data"] = {"hospitals": []}
            return state
        
        # Initialize hospital lookup service in REAL mode
        hospital_service = HospitalLookupService(mock_mode=False)
        logger.info("[HOSPITAL LOOKUP] Using REAL mode (Geoapify)")
        
        # Search for hospitals
        hospitals = hospital_service.search_hospitals(procedure)
        
        # Extract doctors from hospitals
        all_doctors = []
        for hospital in hospitals:
            doctors = hospital.get("doctors", [])
            all_doctors.extend(doctors)
        
        # Update hospital_data
        state["hospital_data"] = {
            "hospitals": hospitals,
            "selected_hospital": None,
            "doctors": all_doctors,
            "selected_doctor": None,
            "selected_slot": None
        }
        
        state["reasoning_trace"].append({
            "node": "hospital_suggestion",
            "action": "Hospital search complete",
            "hospital_count": len(hospitals),
            "doctor_count": len(all_doctors),
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Found {len(hospitals)} hospitals with {len(all_doctors)} doctors")
        
    except Exception as e:
        logger.error(f"Hospital suggestion error: {e}")
        state["errors"].append(f"Hospital suggestion error: {str(e)}")
        state["hospital_data"] = {"hospitals": []}
    
    return state


def scheduling_orchestrator_node_tool(state: AgentState, **kwargs) -> AgentState:
    """
    Scheduling Orchestrator Node: Manages appointment scheduling.
    
    This node is a pass-through for now. Actual scheduling is handled
    by the /api/book-appointment route after user selects doctor and slot.
    
    Args:
        state: Current agent state
    
    Returns:
        Updated state
    """
    logger.info("Agent Tool: scheduling_orchestrator_node_tool")
    
    state["reasoning_trace"].append({
        "node": "scheduling_orchestrator",
        "action": "Scheduling orchestration (pass-through)",
        "timestamp": datetime.now().isoformat()
    })
    
    # This node is a placeholder for now
    # Actual scheduling happens in the booking API route
    
    return state



# ============================================================================
# VOICE INTAKE EXTRACTION
# ============================================================================

def extract_intake_from_transcript(transcript: str, llm_client) -> dict:
    """
    Extract structured intake fields from voice transcript using LLM.
    
    Args:
        transcript: Raw voice transcript text
        llm_client: LLM client for extraction
    
    Returns:
        Dict with extracted fields (name, age, symptoms, etc.)
    """
    logger.info("Extracting intake from transcript")
    
    if not transcript or not transcript.strip():
        return {"error": "Empty transcript"}
    
    if not llm_client or not llm_client.is_available():
        # Fallback: return transcript as chief_complaint
        return {
            "chief_complaint": transcript,
            "symptoms_description": transcript
        }
    
    system_prompt = (
        "You are a medical intake assistant. Extract detailed patient information from the transcript. "
        "Return ONLY valid JSON with these keys: name, age, gender, chief_complaint, "
        "symptoms_description, duration, severity, associated_complaints, procedure_type, "
        "current_medications, allergies, prior_conditions, location, preferred_timing. "
        "Use null for missing fields. Ensure entity mapping is clinically accurate (e.g. mapping casual terms to procedure_type). "
        "No explanation, no markdown, only JSON."
    )
    
    user_prompt = f"Transcript: {transcript}"
    
    try:
        response = llm_client.generate_with_prompt(system_prompt, user_prompt)
        
        if not response:
            # LLM failed, return basic extraction
            return {
                "chief_complaint": transcript,
                "symptoms_description": transcript
            }
        
        # Try to parse JSON from response
        import json
        import re
        
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response
        
        extracted = json.loads(json_str)
        
        # Ensure all expected keys exist
        result = {
            "name": extracted.get("name"),
            "age": extracted.get("age"),
            "gender": extracted.get("gender"),
            "chief_complaint": extracted.get("chief_complaint") or transcript,
            "symptoms_description": extracted.get("symptoms_description") or transcript,
            "duration": extracted.get("duration"),
            "severity": extracted.get("severity"),
            "associated_complaints": extracted.get("associated_complaints") or [],
            "procedure_type": extracted.get("procedure_type"),
            "current_medications": extracted.get("current_medications") or [],
            "allergies": extracted.get("allergies") or [],
            "prior_conditions": extracted.get("prior_conditions") or [],
            "location": extracted.get("location"),
            "preferred_timing": extracted.get("preferred_timing")
        }
        
        logger.info(f"Successfully extracted intake fields from transcript")
        return result
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON from LLM response: {e}")
        return {
            "chief_complaint": transcript,
            "symptoms_description": transcript
        }
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return {
            "chief_complaint": transcript,
            "symptoms_description": transcript
        }
