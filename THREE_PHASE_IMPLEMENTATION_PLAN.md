# Three-Phase Agent Implementation Plan

## Status: IN PROGRESS

This document tracks the implementation of the three-phase appointment prep agent upgrade.

## Completed Steps

✅ 1. Updated `agent/state.py` with new state structure
   - Added IntakeData, TriageData, AdminPrepData, ClinicalBriefingData types
   - Updated AgentState to support three phases
   - Modified create_initial_state function

✅ 2. Created `agent/prompts.py`
   - Symptom normalization prompts
   - Follow-up question generation prompts
   - Triage classification prompts
   - Admin prep prompts
   - Clinical briefing prompts
   - Patient message rewrite prompts

✅ 3. Created `services/retrieval.py`
   - Protocol retrieval service for RAG
   - File-based retrieval system
   - Fallback protocols when no documents loaded

✅ 4. Created protocol documents in `data/protocols/`
   - surgery_prep.json
   - endoscopy_prep.json
   - imaging_prep.json

✅ 5. Created `data/sample_cases.json`
   - 5 sample cases with symptoms, EHR context, demographics

## Remaining Steps

### Phase 1: Core Agent Tools (agent/tools.py)

Need to create/update these tools:

1. ✅ `intake_node_tool` - Process raw intake, normalize symptoms, generate follow-up questions
2. ✅ `triage_node_tool` - Classify urgency, identify red flags
3. ✅ `protocol_retrieval_tool` - Retrieve relevant protocols from RAG
4. ✅ `admin_prep_tool` - Generate admin/logistics instructions
5. ✅ `clinical_briefing_tool` - Generate clinician-facing summary
6. ✅ `patient_message_tool` - Generate patient-facing prep message
7. ✅ `explainability_tool` - Build reasoning trace
8. ✅ Update `save_output_tool` - Save all three phases

### Phase 2: Agent Graph (agent/graph.py)

Update graph to include:

1. ✅ New node sequence: intake → triage → protocol_retrieval → admin_prep → clinical_briefing → patient_message → explainability → save
2. ✅ Conditional logic for follow-up questions
3. ✅ Conditional logic for red flags
4. ✅ Fallback handling for missing retrieval

### Phase 3: Services Updates

1. ✅ Update `services/rules_engine.py` - Add triage rules, admin prep rules
2. ✅ Update `services/storage.py` - Store three-phase data
3. ✅ Keep `services/llm_client.py` - Already supports needed functionality

### Phase 4: Flask Application (app.py)

1. ✅ Update `/generate` endpoint to handle new input format
2. ✅ Initialize retrieval service
3. ✅ Pass retrieval service to agent
4. ✅ Handle new response format (patient_message + clinician_summary)

### Phase 5: Frontend Updates

1. ✅ Update `templates/agent_workspace.html`
   - Add symptom/complaint input fields
   - Add EHR context input (optional)
   - Add two output panels: patient prep + clinician summary
   - Update reasoning trace display

2. ✅ Update `static/js/agent_workspace.js`
   - Handle new input format
   - Render patient prep sections
   - Render clinician summary
   - Handle follow-up questions (future enhancement)

3. ✅ Update `static/css/agent_workspace.css`
   - Style for two-column output
   - Style for clinician summary panel

### Phase 6: Testing & Validation

1. Test with sample cases
2. Verify three-phase flow
3. Test RAG retrieval
4. Test fallback behavior
5. Verify local-first operation

## Implementation Notes

- Keep backward compatibility where possible
- LLM is optional - system must work without it
- RAG is optional - system must work with fallback rules
- All medical instructions must be deterministic
- Clear separation between patient-facing and clinician-facing outputs

## Next Actions

Continue with Phase 1: Implement new agent tools in `agent/tools.py`
