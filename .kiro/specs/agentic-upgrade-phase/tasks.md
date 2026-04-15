# Implementation Plan: Agentic Upgrade Phase

## Overview

This implementation plan breaks down the agentic upgrade into discrete, actionable coding tasks. The upgrade adds voice input, EHR/FHIR integration, missing field detection, hospital lookup, enhanced scheduling, and conditional LangGraph flow while preserving deterministic RulesEngine as the source of truth.

The implementation follows a bottom-up approach: services → agent layer → API layer → frontend layer → integration.

## Tasks

- [x] 1. Create Voice Input Service
  - Create `services/voice_service.py` with transcription functionality using speech_recognition library
  - Implement `transcribe_audio(audio_file)` method that accepts WAV files and returns transcribed text
  - Add error handling for speech recognition failures
  - Support mock mode for testing without audio files
  - _Requirements: 1.5, 1.6, 1.7_

- [x] 2. Create Hospital Lookup Service
  - Create `services/hospital_lookup_service.py` with Overpass API and Nominatim integration
  - Implement `search_hospitals(procedure, location, radius_km)` method
  - Implement `rank_hospitals(hospitals)` method using weighted score (70% rating, 30% distance)
  - Implement `filter_by_capability(hospitals, procedure)` method
  - Add Haversine distance calculation for hospital ranking
  - Support mock mode returning realistic hospital data with doctors and slots
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10_

- [x] 3. Create Missing Field Detector
  - Create `services/missing_field_detector.py` with field detection logic
  - Implement `detect_missing_fields(intake_data, appointment_type)` function
  - Implement `calculate_confidence(intake_data, appointment_type)` function with weighted scoring
  - Define field weights: chief_complaint (0.3), appointment_type (0.3), symptoms_description (0.2), age_group (0.1), medications (0.05), allergies (0.05)
  - Return missing_fields list, confidence_score (0.0-1.0), and suggested_options dict
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.10_

- [x] 4. Update Agent State with New Fields
  - Update `agent/state.py` to add ConversationData TypedDict with missing_fields, confidence_score, current_transcript, is_voice, input_mode, suggested_options, user_confirmations
  - Update `agent/state.py` to add HospitalData TypedDict with hospitals, selected_hospital, doctors, selected_doctor, selected_slot
  - Update AgentState to include conversation_data and hospital_data fields
  - Update `create_initial_state()` to initialize conversation_data with input_mode from raw_intake
  - Update `create_initial_state()` to initialize hospital_data as empty dict
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10_

- [x] 5. Add New Tools to Agent
  - Update `agent/tools.py` to add `voice_input_node(state)` that logs voice input detection
  - Update `agent/tools.py` to add `conversation_intake_node(state, llm_client)` that extracts structured data from conversational query
  - Update `agent/tools.py` to add `missing_info_detector_node(state)` that calls missing_field_detector service
  - Update `agent/tools.py` to add `clarification_agent_node(state)` that generates follow-up questions for missing fields
  - Update `agent/tools.py` to add `hospital_suggestion_node(state)` that calls hospital_lookup_service
  - Update `agent/tools.py` to add `scheduling_orchestrator_node(state)` as pass-through for now
  - Import missing_field_detector and hospital_lookup_service in tools.py
  - _Requirements: 6.2, 6.3, 6.4, 6.5, 6.11, 6.12, 9.1, 9.2, 9.3, 9.4, 10.1, 10.2, 10.3_

- [x] 6. Update LangGraph Flow with Conditional Routing
  - Update `agent/graph.py` to add voice_input, conversation_intake, missing_info_detector, clarification_agent nodes
  - Update `agent/graph.py` to add hospital_suggestion and scheduling_orchestrator nodes
  - Update `agent/graph.py` to implement `confidence_router(state)` function that routes based on confidence_score threshold (0.8)
  - Update workflow to set entry point to voice_input node
  - Add edge: voice_input → conversation_intake
  - Add edge: conversation_intake → missing_info_detector
  - Add conditional edge: missing_info_detector → clarification_agent (if confidence < 0.8) or process_intake (if confidence >= 0.8)
  - Add edge: clarification_agent → END (wait for user response)
  - Add edge: admin_prep → hospital_suggestion
  - Add edge: hospital_suggestion → scheduling_orchestrator
  - Add edge: scheduling_orchestrator → clinical_briefing
  - Update reasoning trace logging for all new nodes
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.11, 6.12, 6.17, 6.18, 6.19_

- [x] 7. Add Voice Transcription API Route
  - Update `app.py` to add POST `/api/transcribe` route
  - Import voice_service in app.py
  - Implement route to accept multipart/form-data with audio file
  - Call voice_service.transcribe_audio(audio_file) and return JSON with transcribed text
  - Handle errors gracefully and return error JSON with appropriate HTTP status codes
  - Log all transcription requests and responses
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.12, 13.13_

- [x] 8. Add Hospital Lookup API Route
  - Update `app.py` to add POST `/api/hospital-lookup` route
  - Import hospital_lookup_service in app.py
  - Implement route to accept JSON with procedure type and optional location
  - Call hospital_lookup_service.search_hospitals() and return ranked hospital list
  - Handle errors gracefully and return error JSON
  - Log all hospital lookup requests
  - _Requirements: 13.5, 13.6, 13.7, 13.12, 13.13_

- [x] 9. Add Analysis API Route
  - Update `app.py` to add POST `/api/analyze` route for step 2 of wizard
  - Implement route to accept intake data and perform triage
  - Call agent workflow up to hospital_suggestion node
  - Return JSON with triage results, urgency level, doctor suggestions, and available slots
  - Handle errors gracefully
  - _Requirements: 13.8, 13.9, 13.12, 13.13_

- [x] 10. Add Booking API Route
  - Update `app.py` to add POST `/api/book-appointment` route for step 4 of wizard
  - Implement route to accept booking details (doctor, slot, patient info)
  - Run full agent workflow from intake to save
  - Return JSON with booking confirmation, prep summary, and clinician briefing
  - Handle errors gracefully
  - _Requirements: 13.10, 13.11, 13.12, 13.13_

- [x] 11. Add Voice Input UI Component
  - Update `templates/agent_workspace.html` to add microphone button next to conversational query textarea
  - Add recording indicator (pulsing red dot) that shows during recording
  - Add status text elements for "Listening...", "Transcribing...", "Complete", and error messages
  - Update `static/css/agent_workspace.css` to style microphone button and recording indicator
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.9, 8.10_

- [x] 12. Implement Voice Input JavaScript
  - Update `static/js/agent_workspace.js` to add voice input functionality using Web Speech API
  - Implement microphone button click handler to start/stop recording
  - Implement recording state management (idle, recording, transcribing, complete, error)
  - Implement audio capture and conversion to WAV format
  - Implement POST request to `/api/transcribe` with audio file
  - Populate textarea with transcribed text on success
  - Display error messages on failure
  - Check browser support for Web Speech API and disable button if not supported
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 8.5, 8.6, 8.7, 8.8_

- [x] 13. Implement 5-Step Wizard UI
  - Update `templates/agent_workspace.html` to add wizard structure with 5 steps: Intake → Analysis → Confirm → Booking → Results
  - Add progress indicator in sidebar showing current step and completed steps
  - Add step navigation buttons (Next, Back, Confirm)
  - Add doctor cards display for step 2 with ratings, specialties, and available slots
  - Add booking confirmation display for step 3
  - Add results display for step 5 with prep summary and clinician briefing
  - Update `static/css/agent_workspace.css` to style wizard steps and progress indicator
  - _Requirements: 14.1, 14.8, 14.9, 14.10, 14.12_

- [x] 14. Implement Wizard JavaScript Logic
  - Update `static/js/agent_workspace.js` to add wizard step management
  - Implement step 1 submission that calls `/api/analyze`
  - Implement step 2 doctor card rendering with ratings and slot selection
  - Implement step 3 confirmation display with selected doctor and slot details
  - Implement step 4 booking that calls `/api/book-appointment`
  - Implement step 5 results display with prep summary and clinician briefing
  - Implement back button navigation that preserves form data
  - Display urgency tag based on triage results
  - Handle errors inline without blocking workflow
  - _Requirements: 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.11_

- [x] 15. Update EHR Service Integration in Agent
  - Update `agent/tools.py` to modify `intake_node_tool` to check for fhir_patient_id in raw_intake
  - If fhir_patient_id exists, call ehr_service.enrich_intake() to merge FHIR data with manual data
  - Update state with enriched intake_data and ehr_context
  - Log EHR enrichment status to reasoning trace
  - Handle EHR fetch failures gracefully by continuing with manual data
  - _Requirements: 2.11, 2.12, 2.13, 2.14, 9.3, 9.4, 9.8, 9.9, 9.10_

- [x] 16. Checkpoint - Verify Core Workflow
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Add Mock Mode Configuration
  - Update `app.py` to read MOCK_MODE environment variable (default: True)
  - Pass mock_mode flag to all services (voice_service, ehr_service, hospital_lookup_service, scheduling_orchestrator)
  - Update `.env.example` to document MOCK_MODE, FHIR_BASE_URL, OVERPASS_API_URL environment variables
  - Verify all services work in mock mode without external API credentials
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9_

- [x] 18. Update Scheduling Orchestrator
  - Update `services/calendar_service.py` to add `get_available_slots(doctor_id, date_range)` method
  - Update `services/calendar_service.py` to add `create_appointment_event(slot, patient, doctor)` method
  - Update `services/calendar_service.py` to support mock mode for slot generation and event creation
  - Update `agent/tools.py` scheduling_orchestrator_node to call calendar_service methods
  - Update state with event_id and booking confirmation status
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

- [x] 19. Add Confirmation Notifications
  - Update `services/sms_service.py` to add `send_booking_confirmation(phone, booking_details)` method
  - Update `services/email_service.py` to add `send_booking_confirmation(email, booking_details)` method
  - Update scheduling_orchestrator_node to send SMS/email confirmation after booking
  - Include appointment details, doctor name, location, and prep summary in confirmation
  - Support mock mode for notifications
  - _Requirements: 5.4, 5.5_

- [x] 20. Attach Prep Summary to Calendar Event
  - Update `services/calendar_service.py` to add `attach_prep_summary(event_id, prep_summary)` method
  - Update scheduling_orchestrator_node to attach patient_message to calendar event as note
  - Support mock mode for attachment
  - _Requirements: 5.7_

- [x] 21. Final Checkpoint - End-to-End Verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks reference specific requirements for traceability
- Checkpoints ensure incremental validation
- Mock mode is enabled by default for all external services
- RulesEngine remains unchanged and is the source of truth for medical instructions
- LLM is used only for phrasing enhancement, not medical decision-making
- All new API routes follow consistent error handling pattern (return JSON with error field)
- Voice input works in both HTTPS and localhost environments
- Frontend wizard preserves form data when navigating between steps
