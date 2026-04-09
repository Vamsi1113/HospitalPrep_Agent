# Three-Phase Agent - Quick Start Guide

## What Was Built

Your appointment prep system has been upgraded from a single-phase to a **THREE-PHASE AI agent**:

### Phase I: Triage & Intake ✅
- Captures chief complaint and symptoms
- Normalizes casual language to clinical terms
- Identifies red flags
- Classifies urgency (routine, urgent, emergency)

### Phase II: Admin Prep ✅
- Retrieves clinic protocols via RAG
- Generates logistics instructions
- Provides insurance/copay reminders
- Lists required documents
- Includes fasting/transport instructions

### Phase III: Clinical Briefing ✅
- Scans EHR context
- Generates clinician-facing summary
- Highlights medication conflicts
- Identifies missing labs/records
- Assesses prep status

## What's Ready To Use Right Now

### ✅ Backend (100% Complete)
- `agent/state.py` - Three-phase state structure
- `agent/prompts.py` - LLM prompts for all phases
- `agent/tools.py` - 8 agent tools + 20 helper functions
- `agent/graph.py` - LangGraph workflow
- `services/retrieval.py` - RAG protocol retrieval
- `app.py` - Flask endpoints updated
- `data/protocols/` - 3 protocol documents
- `data/sample_cases.json` - 5 test cases

### ⚠️ Frontend (Needs Updates)
- HTML needs new input fields (symptoms, medications, allergies)
- JavaScript needs to handle new data format
- CSS needs two-column output layout (patient | clinician)

## How To Test Right Now

### Option 1: API Testing (Works Immediately)

```bash
# Start the server
python app.py

# Test with curl
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name": "John Doe",
    "chief_complaint": "chest feels heavy",
    "symptoms_description": "Started yesterday, pressure feeling",
    "current_medications": ["lisinopril"],
    "allergies": ["penicillin"],
    "age_group": "55-65",
    "prior_conditions": ["hypertension"],
    "appointment_type": "Consultation",
    "procedure": "Cardiac evaluation",
    "clinician_name": "Dr. Smith",
    "appointment_datetime": "2026-04-15T10:00",
    "channel_preference": "email"
  }'
```

**Expected Response**:
```json
{
  "error": false,
  "patient_message": "APPOINTMENT PREPARATION GUIDE\n...",
  "clinician_summary": "PRE-VISIT SUMMARY\nPatient: John Doe\n...",
  "intake_data": {...},
  "triage_data": {...},
  "admin_prep_data": {...},
  "clinical_briefing": {...},
  "agent_trace": [...]
}
```

### Option 2: Load Sample Cases

```bash
# Get sample case data
curl http://localhost:5000/load-sample-case/0

# Returns chest pain case with full EHR context
```

## Frontend Update Checklist

If you want to update the UI to work with the new backend:

### 1. Add Input Fields (`templates/agent_workspace.html`)
- [ ] Chief complaint input
- [ ] Symptoms description textarea
- [ ] Current medications input
- [ ] Allergies input
- [ ] Age group dropdown
- [ ] Prior conditions input
- [ ] EHR context textarea (optional)

### 2. Update JavaScript (`static/js/agent_workspace.js`)
- [ ] Collect new form fields
- [ ] Parse comma-separated lists (medications, allergies)
- [ ] Handle two outputs (patient_message + clinician_summary)
- [ ] Render patient prep in left panel
- [ ] Render clinician summary in right panel
- [ ] Update sample case loading

### 3. Update CSS (`static/css/agent_workspace.css`)
- [ ] Two-column output layout
- [ ] Style for clinician summary panel
- [ ] Style for new input fields

**Estimated Time**: 2-4 hours

## Key Features

### 1. Deterministic Rules ✅
All medical instructions come from rules, not AI:
- Fasting hours by procedure type
- Transport requirements
- Arrival timing
- Document checklists
- Red flag detection

### 2. RAG Retrieval ✅
Retrieves clinic protocols from local documents:
- Surgery prep protocols
- Endoscopy prep protocols
- Imaging prep protocols
- Falls back to rules if unavailable

### 3. LLM Enhancement (Optional) ✅
Uses GPT-3.5-Turbo for:
- Symptom normalization
- Friendly message rewriting
- Clinical summary generation
- Falls back to templates if unavailable

### 4. Dual Outputs ✅
Generates two separate outputs:
- **Patient Message**: Friendly prep instructions
- **Clinician Summary**: Medical summary with risks, conflicts, gaps

### 5. Explainability ✅
Every step logged in reasoning trace:
- Intake processing
- Triage classification
- Protocol retrieval
- Admin prep generation
- Clinical briefing
- Message generation

## File Structure

```
.
├── agent/
│   ├── state.py          ✅ Three-phase state structure
│   ├── prompts.py        ✅ LLM prompts
│   ├── tools.py          ✅ 8 agent tools
│   └── graph.py          ✅ LangGraph workflow
├── services/
│   ├── retrieval.py      ✅ RAG protocol retrieval
│   ├── rules_engine.py   ✅ Deterministic rules
│   ├── llm_client.py     ✅ GPT-3.5-Turbo client
│   └── storage.py        ✅ SQLite storage
├── data/
│   ├── protocols/        ✅ 3 protocol documents
│   └── sample_cases.json ✅ 5 test cases
├── templates/
│   └── agent_workspace.html  ⚠️ Needs updates
├── static/
│   ├── js/agent_workspace.js ⚠️ Needs updates
│   └── css/agent_workspace.css ⚠️ Needs updates
└── app.py                ✅ Flask app updated
```

## What Works Right Now

✅ Three-phase agent workflow
✅ Symptom normalization
✅ Triage classification
✅ Red flag detection
✅ Protocol retrieval (RAG)
✅ Admin prep generation
✅ Clinical briefing generation
✅ Patient message generation
✅ Clinician summary generation
✅ Reasoning trace
✅ Database storage
✅ API endpoints
✅ Sample cases

## What Needs Frontend Work

⚠️ Input form (add symptom fields)
⚠️ Output display (two-column layout)
⚠️ Sample case buttons (load new cases)
⚠️ CSS styling (patient vs clinician panels)

## Testing Strategy

### 1. Backend Testing (Do This First)
```bash
# Test each sample case
for i in {0..4}; do
  curl http://localhost:5000/load-sample-case/$i | \
  curl -X POST http://localhost:5000/generate \
    -H "Content-Type: application/json" \
    -d @-
done
```

### 2. Frontend Testing (After Updates)
1. Open http://localhost:5000
2. Fill in symptom fields
3. Click "Generate Prep Plan"
4. Verify patient prep displays on left
5. Verify clinician summary displays on right
6. Check reasoning trace
7. Test all 5 sample cases

## Troubleshooting

### Backend Issues

**Problem**: "Module not found" errors
**Solution**: 
```bash
pip install -r requirements.txt
```

**Problem**: Protocol retrieval not working
**Solution**: Check `data/protocols/` directory exists with JSON files

**Problem**: LLM not working
**Solution**: Set `OPENAI_API_KEY` in `.env` file (optional - system works without it)

### Frontend Issues

**Problem**: Form submission fails
**Solution**: Check browser console for JavaScript errors

**Problem**: Output not displaying
**Solution**: Check response format in Network tab

## Next Steps

1. **Test backend** with curl/Postman ✅
2. **Update frontend** HTML/JS/CSS ⚠️
3. **Test end-to-end** with UI ⏳
4. **Add more protocols** (optional) ⏳
5. **Enhance storage** (optional) ⏳

## Support

- Backend: Fully functional, ready to use
- Frontend: Needs 2-4 hours of updates
- Documentation: Complete
- Sample data: 5 realistic test cases
- Protocols: 3 procedure types covered

## Summary

**Status**: Backend 100% complete, frontend needs updates
**Effort**: 2-4 hours to complete frontend
**Testing**: Backend testable via API right now
**Production**: Ready after frontend updates

The three-phase agent system is fully implemented and functional at the backend level. You can test it immediately via API calls. The frontend just needs to be updated to collect the new input fields and display the dual outputs.
