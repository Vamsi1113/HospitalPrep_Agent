"""
Flask Application for Appointment Prep AI Agent.

This is the main entry point for the web application. It provides routes for:
- Landing page (/)
- Dashboard (/dashboard)
- Message generation (/generate)
- Message history (/history)
- Sample data loading (/load-sample/<id>)

Validates: Requirements 6.1-6.10, 8.1-8.3, 8.7, 9.1-9.3
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from services.rules_engine import RulesEngine
from services.message_builder import MessageBuilder
from services.llm_client import LLMClient
from services.storage import StorageService
from services.prep_plan_builder import PrepPlanBuilder
from services.retrieval import ProtocolRetrieval
from services.calendar_service import CalendarService
from services.sms_service import SMSService
from services.email_service import EmailService
from services.context_manager import get_context_manager
from agent.graph import run_agent
from agent.prompts import build_chat_prompt
import tempfile
import speech_recognition as sr
import io

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Load configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['OPENROUTER_API_KEY'] = os.getenv('OPENROUTER_API_KEY')

# Initialize services
rules_engine = RulesEngine()
llm_client = LLMClient(api_key=app.config['OPENROUTER_API_KEY'])
message_builder = MessageBuilder(llm_client)
prep_plan_builder = PrepPlanBuilder()
retrieval_service = ProtocolRetrieval(protocols_dir="data/protocols")
calendar_service = CalendarService()
sms_service = SMSService()
email_service = EmailService()
storage = StorageService()

# Initialize database on startup
storage.init_db()

# Load design tokens and page content
with open('data/design_tokens.json', 'r') as f:
    design_tokens = json.load(f)

with open('data/page_content.json', 'r') as f:
    page_content = json.load(f)


@app.route('/')
def index():
    """
    Render agent workspace - single-page AI agent interface.
    
    This replaces the old home page + dashboard split with a unified
    agent workspace experience.
    """
    return render_template('agent_workspace.html')


@app.route('/generate', methods=['POST'])
def generate_prep_message():
    """
    Generate THREE-PHASE appointment prep via AJAX.
    
    Expects JSON request body with:
    - chief_complaint: Patient's symptom description
    - symptoms_description: Detailed symptom info
    - current_medications: List of medications
    - allergies: List of allergies
    - age_group: Patient age range
    - prior_conditions: List of conditions
    - appointment_type: Type of appointment
    - procedure: Specific procedure
    - clinician_name: Doctor name
    - appointment_datetime: Appointment date/time
    - ehr_context: Optional EHR data
    
    Returns JSON with:
    - patient_message: Patient-facing prep instructions
    - clinician_summary: Clinician-facing summary
    - agent_trace: Reasoning steps
    """
    try:
        # Parse request data
        raw_intake = request.get_json()
        
        if not raw_intake:
            app.logger.warning("Generate endpoint called with no data")
            return jsonify({
                "error": True,
                "messages": ["No intake data provided"]
            }), 400
        
        # Build shared context
        session_id = raw_intake.get("session_id", "default_session")
        ctx_mgr = get_context_manager()
        ctx_mgr.build_from_intake(session_id, raw_intake)

        # Generate THREE-PHASE prep using LangGraph agent
        result = run_agent(
            raw_intake,
            rules_engine,
            retrieval_service,
            llm_client,
            storage
        )

        if not result.get("error"):
            # Update shared context with generated outputs
            ctx_mgr.update_context(session_id, {
                "prep_output": result.get("patient_message"),
                "clinical_briefing": result.get("clinician_summary")
            })
        
        # Check for errors
        if result.get("error"):
            app.logger.info(f"Agent errors: {result.get('messages')}")
            return jsonify(result), 400
        
        # Return success with both patient and clinician outputs
        return jsonify(result), 200
        
    except ValueError as e:
        app.logger.warning(f"Validation error: {str(e)}")
        return jsonify({
            "error": True,
            "messages": [str(e)]
        }), 400
    except Exception as e:
        app.logger.error(f"Server error: {type(e).__name__}: {str(e)}")
        return jsonify({
            "error": True,
            "messages": ["An unexpected error occurred. Please try again."]
        }), 500


@app.route('/history')
def get_history():
    """
    Retrieve recent message history.
    
    Returns JSON with list of recent messages.
    
    Validates: Requirements 6.6, 8.5, 8.6
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        
        # Validate limit parameter
        if limit < 1 or limit > 100:
            app.logger.warning(f"Invalid history limit requested: {limit}")
            return jsonify({
                "error": True,
                "messages": ["Limit must be between 1 and 100"]
            }), 400
        
        history = storage.get_history(limit=limit)
        
        return jsonify({
            "error": False,
            "history": history
        }), 200
        
    except ValueError as e:
        # Validation error (Requirement 8.1, 8.2)
        app.logger.warning(f"Validation error in history endpoint: {str(e)}")
        return jsonify({
            "error": True,
            "messages": [str(e)]
        }), 400
    except Exception as e:
        # Server error handling (Requirement 8.5, 8.6)
        app.logger.error(f"Server error in history endpoint: {type(e).__name__}")
        return jsonify({
            "error": True,
            "messages": ["Failed to retrieve history. Please try again."]
        }), 500


@app.route('/load-sample/<int:sample_id>')
def load_sample(sample_id: int):
    """
    Load a specific sample appointment.
    
    Args:
        sample_id: The ID of the sample to load
    
    Returns:
        JSON with sample appointment data or 404 if not found
    
    Validates: Requirements 6.7, 7.2, 7.3, 8.5, 8.6, 8.9
    """
    try:
        # Validate sample_id range
        if sample_id < 0:
            app.logger.warning(f"Invalid sample_id requested: {sample_id}")
            return jsonify({
                "error": True,
                "messages": ["Invalid sample ID"]
            }), 400
        
        # Load sample appointments from JSON file
        with open('data/sample_appointments.json', 'r') as f:
            samples = json.load(f)
        
        # Find sample by ID (Requirement 7.2)
        if 0 <= sample_id < len(samples):
            return jsonify(samples[sample_id]), 200
        else:
            # Sample not found (Requirement 7.3)
            app.logger.info(f"Sample not found: {sample_id}")
            return jsonify({
                "error": True,
                "messages": ["Sample not found"]
            }), 404
            
    except FileNotFoundError:
        # Sample data file missing (Requirement 7.4, 8.9)
        app.logger.warning("Sample data file not found")
        return jsonify({
            "error": True,
            "messages": ["No sample data available"]
        }), 404
    except json.JSONDecodeError as e:
        # JSON parsing error (Requirement 8.5, 8.6)
        app.logger.error(f"Failed to parse sample data: {type(e).__name__}")
        return jsonify({
            "error": True,
            "messages": ["Sample data is corrupted"]
        }), 500
    except Exception as e:
        # Server error handling (Requirement 8.5, 8.6)
        app.logger.error(f"Server error in load_sample endpoint: {type(e).__name__}")
        return jsonify({
            "error": True,
            "messages": ["Failed to load sample. Please try again."]
        }), 500


@app.route('/load-sample-case/<int:case_id>')
def load_sample_case(case_id: int):
    """
    Load a specific sample case with symptoms and EHR context.
    
    Args:
        case_id: The ID of the case to load
    
    Returns:
        JSON with sample case data or 404 if not found
    """
    try:
        # Validate case_id range
        if case_id < 0:
            app.logger.warning(f"Invalid case_id requested: {case_id}")
            return jsonify({
                "error": True,
                "messages": ["Invalid case ID"]
            }), 400
        
        # Load sample cases from JSON file
        with open('data/sample_cases.json', 'r') as f:
            cases = json.load(f)
        
        # Find case by ID
        if 0 <= case_id < len(cases):
            return jsonify(cases[case_id]), 200
        else:
            # Case not found
            app.logger.info(f"Case not found: {case_id}")
            return jsonify({
                "error": True,
                "messages": ["Case not found"]
            }), 404
            
    except FileNotFoundError:
        app.logger.warning("Sample cases file not found")
        return jsonify({
            "error": True,
            "messages": ["No sample cases available"]
        }), 404
    except json.JSONDecodeError as e:
        app.logger.error(f"Failed to parse sample cases: {type(e).__name__}")
        return jsonify({
            "error": True,
            "messages": ["Sample cases data is corrupted"]
        }), 500
    except Exception as e:
        app.logger.error(f"Server error in load_sample_case endpoint: {type(e).__name__}")
        return jsonify({
            "error": True,
            "messages": ["Failed to load sample case. Please try again."]
        }), 500


@app.route('/api/slots', methods=['POST'])
def get_available_slots():
    """
    Get available appointment slots.
    
    Expects JSON with:
    - appointment_type: Type of appointment
    - preferred_date: Optional preferred date (ISO format)
    - duration_minutes: Optional duration (default 30)
    
    Returns JSON with available slots.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": True,
                "messages": ["No data provided"]
            }), 400
        
        appointment_type = data.get("appointment_type", "Consultation")
        preferred_date = data.get("preferred_date", "")
        duration = data.get("duration_minutes", 30)
        
        slots = calendar_service.get_available_slots(
            appointment_type=appointment_type,
            preferred_date=preferred_date,
            duration_minutes=duration
        )
        
        return jsonify({
            "error": False,
            "slots": slots
        }), 200
        
    except Exception as e:
        app.logger.error(f"Get slots error: {type(e).__name__}: {str(e)}")
        return jsonify({
            "error": True,
            "messages": ["Failed to retrieve available slots"]
        }), 500


@app.route('/api/book', methods=['POST'])
def book_slot():
    """
    Book an appointment slot.
    
    Expects JSON with:
    - slot: Selected slot object
    - patient_name: Patient name
    - appointment_type: Type of appointment
    - procedure: Procedure name
    - email: Patient email (optional)
    - phone: Patient phone (optional)
    
    Returns JSON with booking confirmation.
    """
    try:
        data = request.get_json()
        
        if not data or not data.get("slot"):
            return jsonify({
                "error": True,
                "messages": ["No slot selected"]
            }), 400
        
        slot = data["slot"]
        
        # Create calendar event
        event_id = calendar_service.create_appointment_event(
            title=f"{data.get('appointment_type', 'Appointment')} - {data.get('patient_name', 'Patient')}",
            start_time=slot["start"],
            end_time=slot["end"],
            description=f"Procedure: {data.get('procedure', 'N/A')}",
            attendee_email=data.get("email", ""),
            location=slot.get("location", "Main Clinic")
        )
        
        # Send confirmations
        if data.get("phone"):
            sms_service.send_booking_confirmation(
                to_phone=data["phone"],
                appointment_datetime=slot["start_formatted"],
                doctor=slot.get("doctor", "Doctor TBD"),
                location=slot.get("location", "Main Clinic")
            )
        
        if data.get("email"):
            email_service.send_booking_confirmation(
                to_email=data["email"],
                patient_name=data.get("patient_name", "Patient"),
                appointment_datetime=slot["start_formatted"],
                doctor=slot.get("doctor", "Doctor TBD"),
                location=slot.get("location", "Main Clinic"),
                prep_summary="Detailed prep instructions will be sent 24 hours before your appointment."
            )
        
        return jsonify({
            "error": False,
            "event_id": event_id,
            "message": "Appointment booked successfully"
        }), 200
        
    except Exception as e:
        app.logger.error(f"Book appointment error: {type(e).__name__}: {str(e)}")
        return jsonify({
            "error": True,
            "messages": ["Failed to book appointment"]
        }), 500


@app.route('/api/cancel', methods=['POST'])
def cancel_appointment():
    """
    Cancel an appointment.
    
    Expects JSON with:
    - event_id: Calendar event ID
    - phone: Patient phone (optional, for SMS notification)
    - appointment_datetime: Formatted date/time for notification
    
    Returns JSON with cancellation confirmation.
    """
    try:
        data = request.get_json()
        
        if not data or not data.get("event_id"):
            return jsonify({
                "error": True,
                "messages": ["No event ID provided"]
            }), 400
        
        # Cancel calendar event
        success = calendar_service.cancel_appointment(data["event_id"])
        
        if not success:
            return jsonify({
                "error": True,
                "messages": ["Failed to cancel appointment"]
            }), 500
        
        # Send cancellation notice
        if data.get("phone"):
            sms_service.send_cancellation_notice(
                to_phone=data["phone"],
                appointment_datetime=data.get("appointment_datetime", "your appointment")
            )
        
        return jsonify({
            "error": False,
            "message": "Appointment cancelled successfully"
        }), 200
        
    except Exception as e:
        app.logger.error(f"Cancel appointment error: {type(e).__name__}: {str(e)}")
        return jsonify({
            "error": True,
            "messages": ["Failed to cancel appointment"]
        }), 500


@app.route('/api/chat', methods=['POST'])
def patient_chat():
    """
    Handle patient Q&A chat.
    
    Expects JSON with:
    - question: Patient question
    - session_id: Session identifier
    - appointment_type: Type of appointment (for context)
    - procedure: Procedure name (for context)
    
    Returns JSON with agent response.
    """
    try:
        data = request.get_json()
        
        if not data or not data.get("question"):
            return jsonify({
                "error": True,
                "messages": ["No question provided"]
            }), 400
        
        session_id = data.get("session_id", "default_session")
        
        ctx_mgr = get_context_manager()
        context = ctx_mgr.get_context(session_id)
        
        # If no context found (e.g. server restart), create a minimal one
        if not context:
            context = ctx_mgr.build_from_intake(session_id, data)
            
        # Add patient question to context
        ctx_mgr.append_chat(session_id, "patient", data["question"])
        chat_history = ctx_mgr.get_context(session_id).get("chat_history", [])
        
        # Generate response using context-aware prompt
        if llm_client and llm_client.is_available():
            system_prompt, user_prompt = build_chat_prompt(
                context=context,
                question=data["question"],
                chat_history=chat_history
            )
            response = llm_client.generate_with_prompt(system_prompt, user_prompt)
            if not response:
                response = "I'm having a little trouble connecting right now. Please try again or contact the clinic."
        else:
            response = "I'm here to help with appointment preparation questions. For specific medical advice, please contact the clinic directly."
        
        # Add agent response to context
        ctx_mgr.append_chat(session_id, "agent", response)
        
        # Save session state to persistent storage
        storage.save_session_state(session_id, ctx_mgr.get_context(session_id))
        
        return jsonify({
            "error": False,
            "response": response,
            "chat_history": ctx_mgr.get_context(session_id).get("chat_history", [])
        }), 200
        
    except Exception as e:
        app.logger.error(f"Chat error: {type(e).__name__}: {str(e)}")
        return jsonify({
            "error": True,
            "messages": ["Failed to process chat message"]
        }), 500


@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """
    Transcribe audio from frontend voice recording.
    Expects a WAV file in the 'audio' field of FormData.
    """
    try:
        if 'audio' not in request.files:
            return jsonify({"error": True, "messages": ["No audio provided. Please ensure the microphone was recorded."]}), 400
            
        file = request.files['audio']
        
        recognizer = sr.Recognizer()
        
        with sr.AudioFile(file) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return jsonify({"error": False, "text": text}), 200
            
    except sr.UnknownValueError:
        return jsonify({"error": False, "text": ""}), 200  # No text detected but no hard error
    except sr.RequestError as e:
        app.logger.error(f"Speech recognition API error: {e}")
        return jsonify({"error": True, "messages": ["Speech recognition service is currently unavailable."]}), 503
    except Exception as e:
        app.logger.error(f"Transcribe error: {type(e).__name__}: {str(e)}")
        return jsonify({"error": True, "messages": ["Failed to transcribe audio. Ensure it is a valid WAV format."]}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_patient():
    """
    Step 2 of the agentic flow: Analyze patient intake data.
    - Triages the symptoms (urgency, red flags)
    - Generates doctor suggestions based on procedure/complaint
    - Returns scheduling slots for each suggested doctor

    Expects JSON with patient intake fields.
    Returns: doctors[], hospital_suggestions[], slots[]
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": True, "messages": ["No data provided"]}), 400

        complaint = data.get("chief_complaint", "").lower()
        procedure = data.get("procedure", "").lower()
        symptoms  = data.get("symptoms_description", "").lower()

        combined = f"{complaint} {procedure} {symptoms}"

        # ── Triage ──────────────────────────────────────────────
        urgency = "routine"
        red_flags = []
        if any(k in combined for k in ["chest pain", "chest tight", "chest pressure", "heart", "cardiac"]):
            urgency = "urgent"
            red_flags.append("Potential cardiac symptoms — expedited consult recommended")
        if any(k in combined for k in ["severe", "emergency", "cannot breathe", "unconscious"]):
            urgency = "emergency"
            red_flags.append("Emergency indicators detected — immediate care needed")

        # ── Specialty detection ──────────────────────────────────
        specialty_map = {
            "cardiology": ["chest", "heart", "cardiac", "palpitation", "blood pressure"],
            "gastroenterology": ["colonoscopy", "endoscopy", "stomach", "bowel", "colon", "abdomen"],
            "radiology": ["mri", "ct scan", "x-ray", "imaging", "scan"],
            "orthopedics": ["knee", "hip", "bone", "joint", "fracture", "spine"],
            "neurology": ["headache", "dizziness", "migraine", "nerve", "seizure"],
            "general medicine": ["checkup", "consultation", "fever", "flu", "general"],
            "oncology": ["cancer", "tumor", "biopsy", "chemotherapy"],
            "pulmonology": ["lung", "breathing", "asthma", "cough", "respiratory"],
        }

        matched_specialty = "general medicine"
        for specialty, keywords in specialty_map.items():
            if any(k in combined for k in keywords):
                matched_specialty = specialty
                break

        # ── Doctor pool (with scheduling slots) ─────────────────
        from datetime import timedelta
        now = datetime.now()

        def slots_for_doctor(doc_id):
            return [
                {
                    "slot_id": f"{doc_id}_slot_{i}",
                    "datetime_display": (now + timedelta(days=i+1, hours=9)).strftime("%b %d, %Y at %I:%M %p"),
                    "datetime_iso": (now + timedelta(days=i+1, hours=9)).isoformat(),
                    "duration": "45 min",
                    "location": "Main Clinic",
                    "available": True
                }
                for i in range(3)
            ]

        all_doctors = {
            "cardiology": [
                {"id": "dr_001", "name": "Dr. Sarah Johnson", "specialty": "Cardiologist", "rating": 4.9, "hospital": "St. Jude Premier Health", "hospital_rating": 4.9, "hospital_location": "Downtown", "experience": "15 years", "image_initial": "SJ"},
                {"id": "dr_002", "name": "Dr. Michael Chen", "specialty": "Interventional Cardiologist", "rating": 4.8, "hospital": "Metro Heart Institute", "hospital_rating": 4.7, "hospital_location": "East Side", "experience": "12 years", "image_initial": "MC"},
            ],
            "gastroenterology": [
                {"id": "dr_003", "name": "Dr. Priya Patel", "specialty": "Gastroenterologist", "rating": 4.9, "hospital": "Metro General Hospital", "hospital_rating": 4.5, "hospital_location": "East Side", "experience": "10 years", "image_initial": "PP"},
                {"id": "dr_004", "name": "Dr. James Wilson", "specialty": "GI Specialist", "rating": 4.7, "hospital": "Hope Medical Center", "hospital_rating": 4.6, "hospital_location": "Central Hills", "experience": "18 years", "image_initial": "JW"},
            ],
            "radiology": [
                {"id": "dr_005", "name": "Dr. Lisa Park", "specialty": "Radiologist", "rating": 4.8, "hospital": "Valley Imaging Center", "hospital_rating": 4.8, "hospital_location": "North Suburbs", "experience": "11 years", "image_initial": "LP"},
            ],
            "neurology": [
                {"id": "dr_006", "name": "Dr. Robert Martinez", "specialty": "Neurologist", "rating": 4.7, "hospital": "NeuroHealth Institute", "hospital_rating": 4.6, "hospital_location": "West Park", "experience": "16 years", "image_initial": "RM"},
            ],
            "general medicine": [
                {"id": "dr_007", "name": "Dr. Emily Brown", "specialty": "General Physician", "rating": 4.6, "hospital": "City Medical Clinic", "hospital_rating": 4.5, "hospital_location": "Central", "experience": "9 years", "image_initial": "EB"},
                {"id": "dr_008", "name": "Dr. David Kim", "specialty": "Internal Medicine", "rating": 4.5, "hospital": "Hope Medical Center", "hospital_rating": 4.6, "hospital_location": "Central Hills", "experience": "14 years", "image_initial": "DK"},
            ],
            "orthopedics": [
                {"id": "dr_009", "name": "Dr. Susan Lee", "specialty": "Orthopedic Surgeon", "rating": 4.8, "hospital": "Bone & Joint Institute", "hospital_rating": 4.7, "hospital_location": "North", "experience": "20 years", "image_initial": "SL"},
            ],
            "oncology": [
                {"id": "dr_010", "name": "Dr. Thomas Grant", "specialty": "Oncologist", "rating": 4.9, "hospital": "Regional Cancer Center", "hospital_rating": 4.9, "hospital_location": "Medical District", "experience": "22 years", "image_initial": "TG"},
            ],
            "pulmonology": [
                {"id": "dr_011", "name": "Dr. Nancy Wright", "specialty": "Pulmonologist", "rating": 4.7, "hospital": "Lung Health Clinic", "hospital_rating": 4.5, "hospital_location": "South Side", "experience": "13 years", "image_initial": "NW"},
            ],
        }

        doctors = all_doctors.get(matched_specialty, all_doctors["general medicine"])
        for doc in doctors:
            doc["slots"] = slots_for_doctor(doc["id"])

        app.logger.info(f"Analyzed: specialty={matched_specialty}, urgency={urgency}")

        return jsonify({
            "error": False,
            "triage": {
                "urgency": urgency,
                "red_flags": red_flags,
                "specialty": matched_specialty
            },
            "doctors": doctors,
            "intake_snapshot": data  # echo back so frontend can pass to next step
        }), 200

    except Exception as e:
        app.logger.error(f"Analyze error: {type(e).__name__}: {str(e)}")
        return jsonify({"error": True, "messages": [f"Analysis failed: {str(e)}"]}), 500


@app.route('/api/book-appointment', methods=['POST'])
def book_appointment():
    """
    Step 4 of the agentic flow: Confirm booking and generate patient prep.
    Expects JSON with:
    - intake_data: original patient intake
    - selected_doctor: {name, specialty, hospital}
    - selected_slot: {datetime_display, datetime_iso, location}

    Returns: booking_confirmation + patient_message + clinician_summary
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": True, "messages": ["No booking data provided"]}), 400

        intake = data.get("intake_data", {})
        doctor = data.get("selected_doctor", {})
        slot   = data.get("selected_slot", {})

        if not doctor or not slot:
            return jsonify({"error": True, "messages": ["Doctor and slot selection required"]}), 400

        # Merge the confirmed booking details into the raw_intake
        raw_intake = {**intake}
        raw_intake["clinician_name"]        = doctor.get("name", intake.get("clinician_name", ""))
        raw_intake["appointment_datetime"]  = slot.get("datetime_display", intake.get("appointment_datetime", ""))
        raw_intake["appointment_type"]      = intake.get("appointment_type", "Consultation")
        raw_intake["procedure"]             = intake.get("procedure", doctor.get("specialty", "Consultation"))

        # Run the full agent to generate patient prep + clinician brief
        result = run_agent(raw_intake, rules_engine, retrieval_service, llm_client, storage)

        if result.get("error"):
            app.logger.warning(f"Agent error during booking: {result.get('messages')}")
            return jsonify(result), 400

        # Build booking confirmation
        confirmation = {
            "error": False,
            "booking": {
                "doctor_name":   doctor.get("name"),
                "specialty":     doctor.get("specialty"),
                "hospital":      doctor.get("hospital"),
                "hospital_location": doctor.get("hospital_location"),
                "date_time":     slot.get("datetime_display"),
                "location":      slot.get("location", "Main Clinic"),
                "duration":      slot.get("duration", "45 min"),
                "confirmation_id": f"PREPCARE-{int(datetime.now().timestamp())}"
            },
            "patient_message":   result.get("patient_message"),
            "clinician_summary": result.get("clinician_summary"),
        }

        app.logger.info(f"Appointment booked: {confirmation['booking']['confirmation_id']}")
        return jsonify(confirmation), 200

    except Exception as e:
        app.logger.error(f"Book appointment error: {type(e).__name__}: {str(e)}")
        return jsonify({"error": True, "messages": [f"Booking failed: {str(e)}"]}), 500


@app.route('/api/post-procedure', methods=['POST'])
def post_procedure():
    """
    Generate post-procedure recovery plan.
    
    Expects JSON with:
    - procedure: Procedure name
    - patient_name: Patient name
    - email: Patient email (optional, for sending instructions)
    
    Returns JSON with recovery plan.
    """
    try:
        data = request.get_json()
        
        if not data or not data.get("procedure"):
            return jsonify({
                "error": True,
                "messages": ["No procedure specified"]
            }), 400
        
        procedure = data["procedure"]
        
        # Get post-procedure rules
        recovery_rules = rules_engine.get_post_procedure_rules(procedure)
        
        # Build recovery instructions
        instructions_parts = []
        instructions_parts.append("POST-PROCEDURE RECOVERY INSTRUCTIONS\n")
        
        if recovery_rules.get("rest_period"):
            instructions_parts.append(f"REST PERIOD: {recovery_rules['rest_period']}")
        
        if recovery_rules.get("activity_restrictions"):
            instructions_parts.append("\nACTIVITY RESTRICTIONS:")
            for restriction in recovery_rules["activity_restrictions"]:
                instructions_parts.append(f"  • {restriction}")
        
        if recovery_rules.get("medication_schedule"):
            instructions_parts.append("\nMEDICATION SCHEDULE:")
            for med in recovery_rules["medication_schedule"]:
                instructions_parts.append(f"  • {med.get('name')}: {med.get('schedule')}")
        
        if recovery_rules.get("diet_guidance"):
            instructions_parts.append(f"\nDIET: {recovery_rules['diet_guidance']}")
        
        if recovery_rules.get("warning_signs"):
            instructions_parts.append("\n⚠️ CALL DOCTOR IF YOU EXPERIENCE:")
            for sign in recovery_rules["warning_signs"]:
                instructions_parts.append(f"  • {sign}")
        
        if recovery_rules.get("follow_up_needed"):
            instructions_parts.append(f"\nFOLLOW-UP: Schedule appointment within {recovery_rules.get('follow_up_timeframe', '1-2 weeks')}")
        
        instructions = "\n".join(instructions_parts)
        
        # Send recovery email if email provided
        if data.get("email"):
            email_service.send_post_procedure_instructions(
                to_email=data["email"],
                patient_name=data.get("patient_name", "Patient"),
                procedure=procedure,
                instructions=instructions
            )
        
        return jsonify({
            "error": False,
            "recovery_plan": {
                "procedure": procedure,
                "instructions": instructions,
                "activity_restrictions": recovery_rules.get("activity_restrictions", []),
                "medication_schedule": recovery_rules.get("medication_schedule", []),
                "warning_signs": recovery_rules.get("warning_signs", []),
                "follow_up_needed": recovery_rules.get("follow_up_needed", False),
                "follow_up_timeframe": recovery_rules.get("follow_up_timeframe")
            }
        }), 200
        
    except Exception as e:
        app.logger.error(f"Post-procedure error: {type(e).__name__}: {str(e)}")
        return jsonify({
            "error": True,
            "messages": ["Failed to generate recovery plan"]
        }), 500


# Error handlers
@app.errorhandler(400)
def bad_request(error):
    """
    Handle 400 Bad Request errors.
    
    Validates: Requirements 8.1, 8.2
    """
    app.logger.warning(f"400 Bad Request: {error}")
    return jsonify({
        "error": True,
        "messages": ["Invalid request. Please check your input."]
    }), 400


@app.errorhandler(404)
def not_found(error):
    """
    Handle 404 Not Found errors.
    
    Validates: Requirement 8.2
    """
    app.logger.info(f"404 Not Found: {error}")
    return jsonify({
        "error": True,
        "messages": ["Resource not found"]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """
    Handle 500 Internal Server Error.
    
    Validates: Requirements 8.5, 8.6
    """
    # Log error without exposing details (Requirement 8.4)
    app.logger.error(f"500 Internal Server Error: {type(error).__name__}")
    return jsonify({
        "error": True,
        "messages": ["An unexpected error occurred. Please try again."]
    }), 500


if __name__ == '__main__':
    # use_reloader=False  → prevents the Werkzeug reloader from killing
    #                       in-flight requests when source files change
    # threaded=True       → each request runs in its own thread so the
    #                       LLM call doesn't block history/health endpoints
    app.run(debug=True, host='0.0.0.0', port=5000,
            use_reloader=False, threaded=True)
