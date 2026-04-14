import re

with open('agent/tools.py', 'r', encoding='utf-8') as f:
    tools_content = f.read()

new_tools = """
# ============================================================================
# NEW CONVERSATIONAL & SCHEDULING NODES
# ============================================================================

def conversation_intake_node(state: AgentState, llm_client, **kwargs) -> AgentState:
    \"\"\"
    Phase I / Phase 0 Tool: Handles free-text, partial answers, and field extraction.
    Replaces static form requirement by determining what is missing.
    \"\"\"
    logger.info("Agent Tool: conversation_intake_node")
    
    state["metadata"]["steps"].append({
        "step": "conversation_intake",
        "timestamp": datetime.now().isoformat(),
        "description": "Extracting conversational input and missing fields"
    })
    try:
        raw = state.get("raw_intake", {})
        query = raw.get("conversational_query", "")
        
        # Simplified field extraction logic
        missing_fields = []
        if not raw.get("patient_name"): missing_fields.append("patient_name")
        if not raw.get("appointment_type"): missing_fields.append("appointment_type")
        if not raw.get("procedure"): missing_fields.append("procedure")
        if not raw.get("appointment_datetime"): missing_fields.append("appointment_datetime")
        if not raw.get("chief_complaint") and not query: missing_fields.append("chief_complaint")
        
        # If there's missing information, we log it and keep confidence score low
        confidence = 1.0 if not missing_fields else 0.5
        
        if "conversation_data" not in state or state["conversation_data"] is None:
            state["conversation_data"] = {
                "missing_fields": missing_fields,
                "suggested_options": {},
                "confidence_score": confidence,
                "current_transcript": query,
                "is_voice": False
            }
        else:
            state["conversation_data"]["missing_fields"] = missing_fields
            state["conversation_data"]["confidence_score"] = confidence
            state["conversation_data"]["current_transcript"] = query

    except Exception as e:
        logger.error(f"conversation_intake_node error: {e}")
        state["errors"].append(f"conversation_intake_node error: {str(e)}")
        
    return state

def voice_intake_node(state: AgentState, llm_client, **kwargs) -> AgentState:
    \"\"\"
    Phase I / Phase 0 Tool: Handles speech input and transcripts.
    \"\"\"
    logger.info("Agent Tool: voice_intake_node")
    state["metadata"]["steps"].append({
        "step": "voice_intake",
        "timestamp": datetime.now().isoformat()
    })
    
    raw = state.get("raw_intake", {})
    voice_transcript = raw.get("voice_transcript", "")
    
    # Simple transcription passing logic for now
    if voice_transcript:
        if "conversation_data" not in state or state["conversation_data"] is None:
            state["conversation_data"] = {}
        state["conversation_data"]["is_voice"] = True
        if not state["conversation_data"].get("current_transcript"):
            state["conversation_data"]["current_transcript"] = voice_transcript
            
    return state

def slot_completion_node(state: AgentState, **kwargs) -> AgentState:
    \"\"\"
    Phase 0 Tool: Suggests options and fills missing fields.
    \"\"\"
    logger.info("Agent Tool: slot_completion_node")
    state["metadata"]["steps"].append({
        "step": "slot_completion",
        "timestamp": datetime.now().isoformat()
    })
    
    conv_data = state.get("conversation_data", {})
    if conv_data:
        missing = conv_data.get("missing_fields", [])
        if "appointment_type" in missing:
            conv_data["suggested_options"]["appointment_type"] = ["General Checkup", "Specialist Visit", "Imaging", "Surgery"]
        if "procedure" in missing:
            conv_data["suggested_options"]["procedure"] = ["MRI", "CT Scan", "Colonoscopy", "Endoscopy", "Blood Test"]
    
    return state

def scheduling_orchestrator_node(state: AgentState, **kwargs) -> AgentState:
    \"\"\"
    Phase 0 Tool: Searches slots, books, confirms.
    Replaces synthetic mock booking with a placeholder for a real slot finder/booking.
    \"\"\"
    logger.info("Agent Tool: scheduling_orchestrator_node")
    state["metadata"]["steps"].append({
        "step": "scheduling_orchestrator",
        "timestamp": datetime.now().isoformat()
    })
    
    raw = state.get("raw_intake", {})
    if "scheduling_data" not in state or state["scheduling_data"] is None:
        # Mocking an available slot if missing
        state["scheduling_data"] = {
            "available_slots": [
                {"id": "slot_1", "datetime": "2026-05-01T10:00:00Z"},
                {"id": "slot_2", "datetime": "2026-05-02T14:30:00Z"}
            ],
            "selected_slot": None,
            "booking_confirmed": False,
            "event_id": None,
            "confirmation_sent": False
        }
    
    # Auto-select the first slot and confirm if all info is present and slot not booked yet
    conv_data = state.get("conversation_data", {})
    if not conv_data.get("missing_fields") and not state["scheduling_data"]["booking_confirmed"]:
        state["scheduling_data"]["selected_slot"] = state["scheduling_data"]["available_slots"][0]
        state["scheduling_data"]["booking_confirmed"] = True
        state["scheduling_data"]["event_id"] = "EVN-9999"
        raw["appointment_datetime"] = state["scheduling_data"]["selected_slot"]["datetime"]
        
    return state
"""

if "def conversation_intake_node" not in tools_content:
    with open('agent/tools.py', 'a', encoding='utf-8') as f:
        f.write(new_tools)
    print("agent/tools.py updated successfully!")
else:
    print("agent/tools.py already had conversational tools.")
