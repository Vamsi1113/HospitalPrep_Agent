# API and Data Sources Analysis - Hospital Pre-Appointment System

**Generated:** April 15, 2026  
**Analysis Type:** Complete codebase review of all APIs, data sources, and tools

---

## Executive Summary

This document provides a comprehensive analysis of all APIs, data sources, and tools used in the Hospital Pre-Appointment Management System. The analysis is based on actual code inspection, not just recent updates.

### System Architecture Overview
- **Backend:** Flask (Python)
- **Agent Framework:** LangGraph for multi-phase workflow orchestration
- **Frontend:** Vanilla JavaScript with Web APIs
- **Database:** SQLite for appointment storage
- **LLM Provider:** OpenRouter API (Claude/GPT models)

---

## 1. VOICE INPUT & TRANSCRIPTION

### 1.1 Browser Web Speech API (Frontend)
**Location:** `static/js/agent_workspace.js`  
**Type:** Browser Native API  
**Status:** ✅ REAL API (Production)

**Implementation:**
```javascript
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.continuous = true;
recognition.interimResults = true;
recognition.lang = 'en-US';
```

**Data Flow:**
1. User clicks microphone button
2. Browser requests microphone permission
3. Real-time speech → text transcription
4. Interim results shown during speech
5. Final transcript sent to backend

**Endpoint:** None (client-side only)

### 1.2 LLM-Based Intake Extraction
**Location:** `agent/tools.py` → `extract_intake_from_transcript()`  
**API:** OpenRouter LLM API  
**Status:** ✅ REAL API (Production)

**Implementation:**
- Takes raw voice transcript
- Uses LLM to extract structured fields:
  - Patient name
  - Age, gender
  - Chief complaint
  - Symptoms description
  - Current medications
  - Allergies
  - Prior conditions
  - Procedure type

**Endpoint:** `POST /api/extract-intake`  
**Request:**
```json
{
  "transcript": "My name is John, I'm 45 years old and having chest pain..."
}
```

**Response:**
```json
{
  "extracted": {
    "name": "John",
    "age": "45",
    "chief_complaint": "chest pain",
    "symptoms_description": "...",
    "current_medications": [],
    "allergies": []
  }
}
```

---

## 2. GEOLOCATION

### 2.1 Browser Geolocation API (Frontend)
**Location:** `static/js/agent_workspace.js`  
**Type:** Browser Native API  
**Status:** ✅ REAL API (Production)

**Implementation:**
```javascript
navigator.geolocation.getCurrentPosition(
  (position) => {
    userLocation = {
      lat: position.coords.latitude,
      lng: position.coords.longitude
    };
  },
  (error) => {
    // Graceful fallback - continues without location
  },
  { timeout: 5000 }
);
```

**Data Flow:**
1. User clicks "Analyze" button
2. Browser requests location permission
3. GPS coordinates captured
4. Sent to backend with intake data
5. Used for hospital proximity search

**Endpoint:** None (client-side only)

---

## 3. HOSPITAL LOOKUP

### 3.1 Google Places API (Primary)
**Location:** `services/hospital_lookup_service.py`  
**API:** Google Places Nearby Search + Place Details  
**Status:** ✅ REAL API (Production-ready, requires API key)

**Implementation:**
```python
class HospitalLookupService:
    def search_real_hospitals(self, lat, lng, specialty, radius):
        # Nearby Search
        nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "type": "hospital",
            "keyword": specialty,
            "key": self.google_api_key
        }
        
        # Place Details for each result
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
```

**Data Retrieved:**
- Hospital name
- Address
- Phone number
- Website
- Rating (0-5 stars)
- Total reviews
- Opening hours
- GPS coordinates
- Distance from user

**Specialty Mapping:**
- "cardiology" → Heart/chest symptoms
- "gastroenterology" → Colonoscopy/endoscopy
- "radiology" → MRI/CT/imaging
- "surgery" → Surgical procedures

**Fallback:** Mock data with 3 synthetic hospitals if API key not configured

**Endpoint:** `POST /api/analyze` (calls hospital lookup internally)

### 3.2 Mock Hospital Data (Fallback)
**Location:** `services/hospital_lookup_service.py` → `_mock_search_hospitals()`  
**Type:** Synthetic data  
**Status:** ✅ ACTIVE (when Google API unavailable)

**Mock Hospitals:**
1. St. Jude Premier Health (Downtown, 4.9★, 2.3km)
2. Metropolitan Medical Center (Midtown, 4.7★, 5.1km)
3. Riverside Community Hospital (Upper West Side, 4.5★, 8.7km)

**Mock Doctors:** Generated dynamically (2 doctors per hospital)

---

## 4. DOCTOR AVAILABILITY

### 4.1 Mock Doctor Generation
**Location:** `services/hospital_lookup_service.py` → `_generate_mock_doctors_for_hospital()`  
**Type:** Synthetic data  
**Status:** ⚠️ SYNTHETIC (No real doctor API)

**Implementation:**
- Generates 1-2 doctors per hospital
- Creates realistic appointment slots (next 2 days, 9 AM - 5 PM)
- Assigns specialty based on procedure type
- Includes doctor ratings, experience, and availability

**Doctor Data Structure:**
```python
{
  "id": "dr_001",
  "name": "Dr. Rajesh Kumar",
  "specialty": "Cardiologist",
  "rating": 4.9,
  "experience": "15 years",
  "hospital": "St. Jude Premier Health",
  "slots": [
    {
      "slot_id": "slot_001",
      "datetime_display": "Jan 16, 2024 at 09:00 AM",
      "datetime_iso": "2024-01-16T09:00:00",
      "duration": "30 min",
      "available": true
    }
  ]
}
```

**Note:** This is currently the ONLY source of doctor data. There is NO integration with real doctor scheduling systems.

---

## 5. TRAVEL TIME & DISTANCE

### 5.1 OpenRouteService API
**Location:** `services/travel_service.py`  
**API:** OpenRouteService Directions API  
**Status:** ✅ REAL API (Production-ready, requires API key)

**Implementation:**
```python
class TravelService:
    def get_travel_time(self, origin_lat, origin_lng, dest_lat, dest_lng):
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        params = {
            "start": f"{origin_lng},{origin_lat}",  # Note: lng,lat format
            "end": f"{dest_lng},{dest_lat}"
        }
        headers = {"Authorization": self.api_key}
```

**Data Retrieved:**
- Duration (minutes)
- Distance (kilometers)
- Route type: driving-car

**Display:** Shows as "🚗 ~X min" pill on doctor cards

**Fallback:** Returns `null` values if API unavailable (no error shown to user)

**Endpoint:** `POST /api/analyze` (calculates travel time for each hospital in parallel)

---

## 6. TRIAGE & SYMPTOM ANALYSIS

### 6.1 LangGraph Agent Workflow
**Location:** `agent/graph.py`, `agent/tools.py`  
**Type:** Multi-phase agent orchestration  
**Status:** ✅ ACTIVE (Production)

**Phases:**
1. **Phase I: Triage & Intake**
   - Symptom normalization (LLM-based)
   - Urgency classification (rule-based + LLM)
   - Red flag detection

2. **Phase II: Admin Prep**
   - Protocol retrieval (RAG)
   - Fasting/transport instructions
   - Document checklist

3. **Phase III: Clinical Briefing**
   - Patient-facing prep message
   - Clinician-facing summary

### 6.2 Urgency Classification
**Location:** `agent/tools.py` → `_classify_urgency()`  
**Type:** Rule-based logic  
**Status:** ✅ ACTIVE (Deterministic)

**Rules:**
- **EMERGENCY:** Chest pain, can't breathe, severe bleeding
- **URGENT:** Red flags present, elderly with dizziness
- **ROUTINE:** Default for standard appointments

**Red Flags Detected:**
- Chest pain/pressure
- Difficulty breathing
- Severe pain
- Elderly patient with dizziness (fall risk)

---

## 7. EHR/FHIR INTEGRATION

### 7.1 FHIR Client
**Location:** `services/fhir_client.py`  
**API:** HAPI FHIR Test Server (R4)  
**Status:** ⚠️ MOCK MODE (Can connect to real FHIR servers)

**Default Server:** `https://hapi.fhir.org/baseR4`

**Resources Fetched:**
- Patient demographics
- AllergyIntolerance
- MedicationStatement
- Procedure history
- Observations (vitals)

**Authentication:** Supports OAuth2/SMART on FHIR (not currently configured)

**Current Mode:** Mock data only (returns synthetic patient records)

### 7.2 EHR Service
**Location:** `services/ehr_service.py`  
**Type:** High-level wrapper around FHIR client  
**Status:** ⚠️ MOCK MODE

**Capabilities:**
- Fetch complete patient data
- Search patients by demographics
- Enrich manual intake with EHR data
- Normalize FHIR resources to internal schema

**Usage in Agent:**
- Triggered when `fhir_patient_id` provided in intake
- Enriches intake with medications, allergies, conditions
- Falls back gracefully if EHR unavailable

---

## 8. APPOINTMENT BOOKING

### 8.1 Booking Workflow
**Location:** `app.py` → `/api/book-appointment`  
**Type:** Multi-step orchestration  
**Status:** ✅ ACTIVE (Production)

**Data Flow:**
1. User selects doctor + time slot
2. Backend runs full agent workflow
3. Generates prep instructions
4. Saves to SQLite database
5. Returns confirmation

**Database:** SQLite (`data/appointments.db`)  
**Storage Service:** `services/storage.py`

**Booking Response:**
```json
{
  "booking_confirmed": true,
  "booking": {
    "confirmation_id": "PREP-A1B2C3D4",
    "doctor_name": "Dr. Sarah Johnson",
    "hospital": "St. Jude Premier Health",
    "date_time": "Jan 16, 2024 at 09:00 AM"
  },
  "patient_message": "Full prep instructions...",
  "clinician_summary": "Clinical briefing..."
}
```

**Note:** Currently does NOT send real emails/SMS or create calendar events during booking. These services are configured but not called in the booking endpoint.

---

## 9. EMAIL NOTIFICATIONS

### 9.1 SendGrid Integration
**Location:** `services/email_service.py`  
**API:** SendGrid Email API  
**Status:** ✅ CONFIGURED (Not actively used in booking flow)

**Implementation:**
```python
class EmailService:
    def _send_real_email(self, to_email, subject, html_content):
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        message = Mail(
            from_email=self.from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        response = self._client.send(message)
```

**Email Types:**
1. **Prep Instructions** - Full appointment preparation guide
2. **Booking Confirmation** - Appointment confirmed with details
3. **Post-Procedure** - Recovery instructions

**Fallback:** Console logging (mock mode)

**Environment Variables:**
- `SENDGRID_API_KEY`
- `SENDGRID_FROM_EMAIL`

**Current Usage:** Available via `/api/book` endpoint (separate from main booking flow)

---

## 10. SMS NOTIFICATIONS

### 10.1 Twilio Integration
**Location:** `services/sms_service.py`  
**API:** Twilio SMS API  
**Status:** ✅ CONFIGURED (Not actively used in booking flow)

**Implementation:**
```python
class SMSService:
    def _send_real_sms(self, to_phone, message):
        from twilio.rest import Client
        result = self._client.messages.create(
            body=message,
            from_=self.from_phone,
            to=to_phone
        )
```

**SMS Types:**
1. **Appointment Reminder** - With prep instructions
2. **Booking Confirmation** - Short confirmation message
3. **Cancellation Notice** - Appointment cancelled

**Fallback:** Console logging (mock mode)

**Environment Variables:**
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`

**Current Usage:** Available via `/api/book` endpoint (separate from main booking flow)

---

## 11. CALENDAR INTEGRATION

### 11.1 Google Calendar API
**Location:** `services/calendar_service.py`  
**API:** Google Calendar API v3  
**Status:** ✅ CONFIGURED (Not actively used in booking flow)

**Implementation:**
```python
class CalendarService:
    def _init_google_calendar(self):
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        
        creds = service_account.Credentials.from_service_account_file(
            self.service_account_path,
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
        self._service = build("calendar", "v3", credentials=creds)
```

**Capabilities:**
1. **Get Available Slots** - Query free/busy times
2. **Create Event** - Book appointment
3. **Cancel Event** - Cancel appointment
4. **Reschedule Event** - Move to new time

**Fallback:** Mock slot generation (realistic times, 9 AM - 5 PM)

**Environment Variables:**
- `GOOGLE_CALENDAR_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

**Current Usage:** Available via `/api/slots`, `/api/book`, `/api/cancel` endpoints (separate from main booking flow)

---

## 12. LLM INTEGRATION

### 12.1 OpenRouter API
**Location:** `services/llm_client.py`  
**API:** OpenRouter (Claude/GPT models)  
**Status:** ✅ ACTIVE (Production)

**Implementation:**
```python
class LLMClient:
    def generate_with_prompt(self, system_prompt, user_prompt):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name
        }
```

**Use Cases:**
1. **Symptom Normalization** - Casual → clinical terms
2. **Intake Extraction** - Voice transcript → structured fields
3. **Prep Message Generation** - Context-aware patient instructions
4. **Clinical Briefing** - Clinician-facing summary
5. **Patient Chat** - Q&A about appointment prep

**Models Used:** Configurable (default: Claude Sonnet)

**Fallback:** Deterministic templates if LLM unavailable

**Environment Variable:** `OPENROUTER_API_KEY`

---

## 13. PROTOCOL RETRIEVAL (RAG)

### 13.1 Protocol Database
**Location:** `data/protocols/`  
**Type:** JSON files (local storage)  
**Status:** ✅ ACTIVE (Production)

**Protocol Files:**
- `endoscopy_prep.json`
- `imaging_prep.json`
- `surgery_prep.json`

**Retrieval Service:** `services/retrieval.py`  
**Method:** Simple keyword matching (not vector-based RAG)

**Data Structure:**
```json
{
  "protocol_id": "colonoscopy_prep",
  "procedure_type": "Colonoscopy",
  "instructions": {
    "fasting": {...},
    "medications": {...},
    "diet_restrictions": {...}
  }
}
```

**Usage:** Retrieved during Phase II (Admin Prep) of agent workflow

---

## 14. RULES ENGINE

### 14.1 Deterministic Rules
**Location:** `services/rules_engine.py`  
**Type:** Rule-based logic (no external API)  
**Status:** ✅ ACTIVE (Production)

**Rules Applied:**
- Fasting requirements (hours before procedure)
- Transport requirements (responsible adult needed)
- Arrival time (minutes before appointment)
- Items to bring (documents, medications)
- Medication restrictions

**Example:**
```python
if procedure == "Colonoscopy":
    fasting_hours = 8
    requires_responsible_adult = True
    arrival_minutes_early = 30
```

**No External API:** All logic is internal

---

## 15. FRONTEND WEB APIS

### 15.1 Browser APIs Used
**Location:** `static/js/agent_workspace.js`  
**Type:** Native browser APIs  
**Status:** ✅ ACTIVE (Production)

**APIs:**
1. **Web Speech API** - Voice transcription
2. **Geolocation API** - User location
3. **Fetch API** - HTTP requests to backend
4. **LocalStorage API** - Session persistence (not currently used)

**No External Dependencies:** All browser-native

---

## SUMMARY TABLE: ALL APIS & DATA SOURCES

| Component | Type | Status | API/Source | Fallback |
|-----------|------|--------|------------|----------|
| **Voice Input** | Browser API | ✅ Real | Web Speech API | None |
| **Intake Extraction** | LLM API | ✅ Real | OpenRouter | Basic parsing |
| **Geolocation** | Browser API | ✅ Real | Geolocation API | Continues without |
| **Hospital Lookup** | External API | ✅ Real | Google Places | Mock hospitals |
| **Doctor Availability** | Synthetic | ⚠️ Mock | Generated | N/A |
| **Travel Time** | External API | ✅ Real | OpenRouteService | Null values |
| **Triage** | Rule-based | ✅ Real | Internal logic | N/A |
| **EHR/FHIR** | External API | ⚠️ Mock | HAPI FHIR | Mock data |
| **Booking Storage** | Database | ✅ Real | SQLite | N/A |
| **Email** | External API | ✅ Ready | SendGrid | Console log |
| **SMS** | External API | ✅ Ready | Twilio | Console log |
| **Calendar** | External API | ✅ Ready | Google Calendar | Mock slots |
| **LLM** | External API | ✅ Real | OpenRouter | Templates |
| **Protocols** | Local Files | ✅ Real | JSON files | N/A |
| **Rules Engine** | Internal | ✅ Real | Python logic | N/A |

---

## KEY FINDINGS

### ✅ REAL APIs Currently Active:
1. **Web Speech API** - Real-time voice transcription
2. **Geolocation API** - User location capture
3. **Google Places API** - Real hospital search (when configured)
4. **OpenRouteService API** - Travel time calculation (when configured)
5. **OpenRouter LLM API** - Symptom analysis, intake extraction, message generation
6. **SQLite Database** - Appointment storage

### ⚠️ MOCK/SYNTHETIC Data:
1. **Doctor Availability** - Generated dynamically, not from real scheduling system
2. **EHR/FHIR Data** - Mock patient records (can connect to real FHIR servers)
3. **Hospital Data** - Falls back to 3 synthetic hospitals if Google API unavailable

### ✅ CONFIGURED But Not Used in Main Flow:
1. **SendGrid Email** - Ready but not called during booking
2. **Twilio SMS** - Ready but not called during booking
3. **Google Calendar** - Ready but not called during booking

### 🔧 REQUIRED API KEYS:
- `OPENROUTER_API_KEY` - ✅ Required (LLM)
- `GOOGLE_PLACES_API_KEY` - Optional (falls back to mock)
- `ORS_API_KEY` - Optional (travel time)
- `SENDGRID_API_KEY` - Optional (email)
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` - Optional (SMS)
- `GOOGLE_CALENDAR_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON` - Optional (calendar)

---

## BOOKING FLOW ANALYSIS

### Current Booking Endpoint: `/api/book-appointment`

**What It Does:**
1. ✅ Receives intake data + selected doctor + time slot
2. ✅ Runs full LangGraph agent workflow
3. ✅ Generates prep instructions (patient + clinician)
4. ✅ Saves to SQLite database
5. ✅ Returns confirmation ID + prep messages

**What It Does NOT Do:**
1. ❌ Send confirmation email to patient
2. ❌ Send notification email to hospital
3. ❌ Send SMS to patient
4. ❌ Create Google Calendar event

**Why:** The email/SMS/calendar services are configured and available, but the booking endpoint doesn't call them. They're only used in separate endpoints (`/api/book`, `/api/slots`, `/api/cancel`).

---

## RECOMMENDATIONS

### To Make Booking Flow Complete:
1. Update `/api/book-appointment` to call:
   - `email_service.send_booking_confirmation()` for patient
   - `email_service.send_email()` for hospital notification
   - `sms_service.send_booking_confirmation()` for patient
   - `calendar_service.create_appointment_event()` if configured

### To Get Real Doctor Data:
1. Integrate with hospital scheduling API (e.g., Epic MyChart, Cerner)
2. Or build doctor availability database
3. Or use Google Calendar API to query doctor calendars

### To Enable Real EHR Data:
1. Configure FHIR server connection
2. Set up OAuth2/SMART on FHIR authentication
3. Update `mock_mode=False` in EHR service initialization

---

**Document Version:** 1.0  
**Last Updated:** April 15, 2026  
**Analysis Method:** Complete codebase inspection
