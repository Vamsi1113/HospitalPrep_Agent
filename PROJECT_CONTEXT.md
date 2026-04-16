# Hospital Pre-Appointment Management System - Complete Project Context

**Last Updated**: April 15, 2026  
**Status**: Agentic Upgrade Phase - Task 5 (Gmail Integration) In Progress

---

## Project Overview

A Flask-based AI agent system that generates personalized appointment preparation instructions for hospital patients. The system uses a three-phase LangGraph workflow combining deterministic rules with LLM-powered content generation.

### Core Purpose
- Generate personalized pre-appointment preparation guides for patients
- Provide clinician-facing pre-visit summaries
- Support voice input, real-time hospital lookup, and travel time calculation
- Enable complete patient journey from intake to booking
- Ensure medical safety through deterministic rules + LLM enhancement

---

## System Architecture

### Technology Stack
- **Backend**: Python 3.x, Flask
- **Agent Framework**: LangGraph (state machine workflow)
- **LLM**: OpenRouter API (Claude/GPT models)
- **Database**: SQLite (local file storage)
- **Frontend**: HTML/CSS/JavaScript (vanilla)
- **Testing**: pytest, hypothesis (property-based testing)
- **External APIs**: Google Places, OpenRouteService, SendGrid, Twilio, Google Calendar

### Three-Phase Agent Workflow

**Phase I: Triage & Intake**
- Process patient intake (voice or text)
- Normalize symptoms using LLM
- Enrich with EHR/FHIR data (if available)
- Classify urgency and identify red flags
- Suggest hospitals and doctors based on location

**Phase II: Admin Prep**
- Retrieve clinic protocols from RAG
- Generate administrative instructions
- Create document checklists
- Provide arrival/transport/fasting instructions

**Phase III: Clinical Briefing**
- Generate clinician-facing summary
- Identify medication conflicts
- Flag missing labs/records
- Create personalized patient prep message

---

## Current Development Phase: Agentic Upgrade

### Objective
Replace mock/synthetic data with real APIs to create a production-ready demo system.

### 8-Task Roadmap

#### ✅ TASK 1: Voice Intake - Web Speech API Integration (COMPLETE)
**Status**: Done  
**Implementation**:
- Replaced custom audio recording with browser-native `window.SpeechRecognition` API
- Real-time speech → text transcription with interim results
- LLM-based extraction of structured intake fields via `/api/extract-intake` endpoint
- Auto-populates form fields (name, age, symptoms, medications, allergies)
- Graceful error handling for mic permission, no speech, network errors

**Files Modified**:
- `static/js/agent_workspace.js` - Web Speech API integration
- `app.py` - `/api/extract-intake` endpoint
- `agent/tools.py` - `extract_intake_from_transcript()` function

#### ✅ TASK 2: Geolocation - Browser Geolocation API (COMPLETE)
**Status**: Done  
**Implementation**:
- Captures user location automatically when "Analyze" button clicked
- Uses browser `navigator.geolocation.getCurrentPosition()` with 5-second timeout
- Graceful fallback if permission denied (shows inline notice, doesn't block workflow)
- Location attached to `/api/analyze` request as `lat` and `lng` fields

**Files Modified**:
- `static/js/agent_workspace.js` - Geolocation capture

#### ✅ TASK 3: Real Hospital Lookup - Google Places API (COMPLETE)
**Status**: Done  
**Implementation**:
- Extended `HospitalLookupService` with `search_real_hospitals()` method
- Uses Google Places Nearby Search API with location, radius, type=hospital, keyword=specialty
- Calls Place Details API for phone, website, opening hours
- Maps results to existing hospital schema expected by frontend
- Generates mock doctors for each real hospital (2 doctors per hospital with realistic slots)
- Falls back to mock data silently if `GOOGLE_PLACES_API_KEY` not set
- Determines specialty keyword from procedure/symptoms (cardiology, gastroenterology, radiology, surgery)

**Files Modified**:
- `services/hospital_lookup_service.py` - Google Places integration
- `app.py` - Updated `/api/analyze` endpoint
- `.env.example` - Added `GOOGLE_PLACES_API_KEY`

#### ✅ TASK 4: Travel Time - OpenRouteService API (COMPLETE)
**Status**: Done  
**Implementation**:
- Created new `services/travel_service.py` with `TravelService` class
- `get_travel_time()` method calls ORS driving-car directions API
- Returns `{duration_minutes, distance_km}` or nulls if API unavailable
- Updated `/api/analyze` to calculate travel time for each hospital in parallel using `ThreadPoolExecutor`
- Travel time attached to each doctor object in response
- Frontend displays travel time as "🚗 ~X min" pill in doctor cards
- Gracefully handles missing API key - no errors, just doesn't show travel time

**Files Modified**:
- `services/travel_service.py` - New file
- `app.py` - Parallel travel time calculation
- `static/js/agent_workspace.js` - Travel time display
- `.env.example` - Added `ORS_API_KEY`

#### 🔄 TASK 5: Real Email - Gmail API Integration (IN PROGRESS)
**Status**: Partially started  
**Next Steps**:
- Add Gmail API initialization in `EmailService.__init__()` - check for `GMAIL_SENDER_ADDRESS` and `GMAIL_OAUTH_CREDENTIALS_JSON` env vars
- Add `_send_gmail()` method using `google-auth` and `googleapiclient.discovery` with scope `https://www.googleapis.com/auth/gmail.send`
- Update `send_email()` to try Gmail first if configured, then SendGrid, then mock
- Add `GMAIL_SENDER_ADDRESS` and `GMAIL_OAUTH_CREDENTIALS_JSON` to `.env.example`
- Keep existing mock fallback if neither Gmail nor SendGrid configured

**Files to Modify**:
- `services/email_service.py` - Gmail integration
- `.env.example` - Gmail env vars

#### ⏳ TASK 6: Real SMS - Fast2SMS Integration (NOT STARTED)
**Status**: Not started  
**Plan**:
- Read `services/sms_service.py` to understand current Twilio implementation
- Add Fast2SMS as new provider option - check for `FAST2SMS_API_KEY` env var
- Add `_send_fast2sms()` method: POST to `https://www.fast2sms.com/dev/bulkV2`
- Update `send_sms()` to try Fast2SMS first if configured, then Twilio, then mock
- SMS content: "Appointment confirmed at {hospital_name} on {date_time}. Bring: {key_prep_items}. Contact: {hospital_phone}."
- Add `FAST2SMS_API_KEY` to `.env.example`

**Files to Modify**:
- `services/sms_service.py` - Fast2SMS integration
- `.env.example` - Fast2SMS env var

#### ⏳ TASK 7: Urgency Display - Frontend UI Enhancement (NOT STARTED)
**Status**: Not started  
**Plan**:
- Update `renderStep2()` in `static/js/agent_workspace.js` to read `triage.urgency` from response
- Add prominent banner above hospital suggestions with color coding:
  - CRITICAL (red): "Seek emergency care immediately. Call 108 or go to ER now."
  - HIGH (orange): "See a specialist within 24–48 hours."
  - MODERATE (yellow): "Schedule an appointment within the next few days."
  - LOW (green): "This can be scheduled at your convenience."
- Add urgency badge to each hospital/doctor card matching the color
- No backend changes needed - display only

**Files to Modify**:
- `static/js/agent_workspace.js` - Urgency display
- `static/css/agent_workspace.css` - Color styling

#### ⏳ TASK 8: Booking Flow - Email-Based Appointment Request (NOT STARTED)
**Status**: Not started  
**Plan**:
- Update `/api/book-appointment` endpoint in `app.py` after SQLite save:
  1. Send confirmation email to patient via `email_service.send_booking_confirmation()` with appointment details + prep instructions + urgency + hospital contact
  2. Send notification email to hospital using `hospital.website` domain or `HOSPITAL_NOTIFY_EMAIL` env var with patient name, procedure, urgency, requested date/time, patient contact
  3. Send SMS to patient via `sms_service.send_booking_confirmation()` with short confirmation
  4. If Google Calendar credentials configured, create calendar event (path already exists)
- Return to frontend: `{success: true, confirmation_id, hospital_name, datetime, prep_summary}`
- Add `HOSPITAL_NOTIFY_EMAIL` to `.env.example`

**Files to Modify**:
- `app.py` - `/api/book-appointment` endpoint
- `.env.example` - Hospital notification email

---

## API & Data Sources (Complete Analysis)

### ✅ REAL APIs Currently Active:
1. **Web Speech API** - Real-time voice transcription (browser-native)
2. **Geolocation API** - User location capture (browser-native)
3. **Google Places API** - Real hospital search with ratings, contact info, location
4. **OpenRouteService API** - Travel time and distance calculation
5. **OpenRouter LLM API** - Symptom analysis, intake extraction, message generation
6. **SQLite Database** - Appointment storage

### ⚠️ MOCK/SYNTHETIC Data:
1. **Doctor Availability** - Generated dynamically (2 doctors per hospital with realistic slots)
2. **EHR/FHIR Data** - Mock patient records (can connect to real FHIR servers)
3. **Hospital Data** - Falls back to 3 synthetic hospitals if Google API unavailable

### ✅ CONFIGURED But Not Used in Main Booking Flow:
1. **SendGrid Email** - Ready but not called during `/api/book-appointment`
2. **Twilio SMS** - Ready but not called during `/api/book-appointment`
3. **Google Calendar** - Ready but not called during `/api/book-appointment`

### 🔧 REQUIRED API KEYS:
- `OPENROUTER_API_KEY` - ✅ Required (LLM)
- `GOOGLE_PLACES_API_KEY` - Optional (falls back to mock hospitals)
- `ORS_API_KEY` - Optional (travel time)
- `SENDGRID_API_KEY` - Optional (email)
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` - Optional (SMS)
- `GOOGLE_CALENDAR_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON` - Optional (calendar)

---

## Key Endpoints

### Frontend Routes
- `GET /` - Agent workspace (single-page interface)

### API Endpoints
- `POST /generate` - Generate prep message (legacy, full agent workflow)
- `POST /api/analyze` - Analyze intake + triage + hospital suggestions (Step 2)
- `POST /api/book-appointment` - Book appointment + generate prep (Step 4)
- `POST /api/extract-intake` - Extract structured fields from voice transcript
- `POST /api/transcribe` - Transcribe audio file (legacy, not used with Web Speech API)
- `POST /api/hospital-lookup` - Search hospitals by procedure (legacy)
- `POST /api/chat` - Patient Q&A chat
- `POST /api/slots` - Get available appointment slots (separate calendar flow)
- `POST /api/book` - Book slot + send confirmations (separate calendar flow)
- `POST /api/cancel` - Cancel appointment (separate calendar flow)
- `POST /api/post-procedure` - Generate recovery plan
- `GET /history` - Retrieve message history
- `GET /load-sample/<id>` - Load sample appointment
- `GET /load-sample-case/<id>` - Load sample case

---

## File Structure

### Core Application
- `app.py` - Flask application with all API endpoints
- `requirements.txt` - Python dependencies

### Agent System
- `agent/graph.py` - LangGraph workflow definition
- `agent/state.py` - Agent state schema
- `agent/tools.py` - Agent tools (intake, triage, prep, briefing)
- `agent/prompts.py` - LLM prompts for each phase

### Services
- `services/llm_client.py` - OpenRouter LLM integration
- `services/rules_engine.py` - Deterministic prep rules
- `services/message_builder.py` - Message formatting
- `services/storage.py` - SQLite database operations
- `services/retrieval.py` - Protocol RAG retrieval
- `services/prep_plan_builder.py` - Prep plan construction
- `services/validation.py` - Input validation
- `services/models.py` - Data models
- `services/hospital_lookup_service.py` - Google Places integration
- `services/travel_service.py` - OpenRouteService integration
- `services/email_service.py` - SendGrid integration
- `services/sms_service.py` - Twilio integration
- `services/calendar_service.py` - Google Calendar integration
- `services/voice_service.py` - Voice transcription (legacy)
- `services/ehr_service.py` - EHR/FHIR integration
- `services/fhir_client.py` - FHIR API client
- `services/fhir_normalizer.py` - FHIR data normalization
- `services/context_manager.py` - Session context management
- `services/missing_field_detector.py` - Intake completeness check

### Frontend
- `templates/agent_workspace.html` - Main UI
- `static/js/agent_workspace.js` - Frontend logic
- `static/css/agent_workspace.css` - Styling

### Data
- `data/protocols/` - JSON protocol files (endoscopy, imaging, surgery)
- `data/appointments.db` - SQLite database
- `data/sample_appointments.json` - Sample data
- `data/sample_cases.json` - Sample cases
- `data/design_tokens.json` - UI design tokens
- `data/page_content.json` - Page content

### Tests
- `tests/test_*.py` - Unit and integration tests
- Property-based tests using Hypothesis

---

## Development Guidelines

### Code Modification Rules
1. **DO NOT** create test files, summary files, or markdown documentation unless explicitly requested
2. **DO NOT** rewrite services from scratch - extend existing classes only
3. **DO NOT** touch RulesEngine logic or LLM client - they work correctly
4. **DO NOT** add print statements beyond existing logging
5. **All new env vars must be optional** - fall back to mock silently if not set
6. **Implement steps sequentially** - complete each before moving to next
7. **Only modify**: specific service file, app.py if endpoint changes, frontend file, .env.example for new keys
8. **Preserve existing SQLite save** in booking flow
9. **No testing needed** unless verifying broken imports

### Environment Configuration
- All API keys are optional
- System falls back to mock/synthetic data gracefully
- No errors shown to user if API unavailable
- See `.env.example` for all configuration options

---

## Recent Changes

### April 15, 2026
- Completed comprehensive API and data sources analysis
- Documented all real APIs, mock data, and synthetic components
- Identified that doctor availability is currently synthetic (no real scheduling API)
- Confirmed email/SMS/calendar services are configured but not used in main booking flow
- Ready to proceed with Task 5 (Gmail integration)

### Previous Updates
- Completed Tasks 1-4 of Agentic Upgrade Phase
- Integrated Web Speech API for voice input
- Added browser geolocation capture
- Integrated Google Places API for real hospital search
- Added OpenRouteService for travel time calculation
- All changes maintain backward compatibility

---

## Next Steps

1. **Complete Task 5**: Add Gmail API integration to email service
2. **Complete Task 6**: Add Fast2SMS integration to SMS service
3. **Complete Task 7**: Add urgency display to frontend UI
4. **Complete Task 8**: Update booking endpoint to send emails/SMS and create calendar events
5. **Testing**: Verify all integrations work with real API keys
6. **Documentation**: Update user guide with API setup instructions

---

## Contact & Support

For questions about this project, refer to:
- `API_AND_DATA_SOURCES_ANALYSIS.md` - Complete API analysis
- `.env.example` - Environment variable configuration
- `README.md` - Setup and installation instructions
- Spec files in `.kiro/specs/` - Feature specifications

---

**Document Version**: 2.0  
**Last Comprehensive Update**: April 15, 2026
