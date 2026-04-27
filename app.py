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
from services.voice_service import VoiceService
from services.hospital_lookup_service import HospitalLookupService
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

# Initialize services
rules_engine = RulesEngine()
# Initialize LLM client with OpenRouter API key
openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
llm_client = LLMClient(api_key=openrouter_api_key)
message_builder = MessageBuilder(llm_client)
prep_plan_builder = PrepPlanBuilder()
retrieval_service = ProtocolRetrieval(protocols_dir="data/protocols")
calendar_service = CalendarService()
sms_service = SMSService()
email_service = EmailService()
voice_service = VoiceService(mock_mode=False)  # Use real Web Speech API
hospital_lookup_service = HospitalLookupService(mock_mode=False)  # Use real Geoapify
storage = StorageService()

# Log service initialization modes
app.logger.info("=" * 60)
app.logger.info("SERVICE INITIALIZATION STATUS")
app.logger.info("=" * 60)
app.logger.info(f"HOSPITAL MODE: {'REAL (Geoapify)' if hospital_lookup_service.use_real_api else 'MOCK'}")
app.logger.info(f"EMAIL MODE: {'REAL (Gmail)' if email_service.use_gmail else 'REAL (SendGrid)' if email_service.use_sendgrid else 'MOCK'}")
app.logger.info(f"SMS MODE: {'REAL (Fast2SMS)' if sms_service.use_fast2sms else 'REAL (Twilio)' if sms_service.use_twilio else 'MOCK'}")
app.logger.info(f"CALENDAR MODE: {'REAL (Google)' if calendar_service.use_real_calendar else 'MOCK'}")
app.logger.info(f"VOICE MODE: {'REAL (Browser API)' if not voice_service.mock_mode else 'MOCK'}")
app.logger.info("=" * 60)

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


# ============================================================================
# NEW API ROUTES FOR AGENTIC UPGRADE
# ============================================================================

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """
    Transcribe audio file to text using voice service.
    
    Expects multipart/form-data with 'audio' file field.
    
    Returns JSON with:
    - error: Boolean indicating success/failure
    - text: Transcribed text (on success)
    - confidence: Confidence score (on success)
    - language: Detected language (on success)
    - messages: Error messages (on failure)
    
    Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.12, 13.13
    """
    try:
        app.logger.info("Transcription request received")
        
        # Check if audio file is present
        if 'audio' not in request.files:
            app.logger.warning("No audio file in request")
            return jsonify({
                "error": True,
                "messages": ["No audio file provided"]
            }), 400
        
        audio_file = request.files['audio']
        
        # Check if file is empty
        if audio_file.filename == '':
            app.logger.warning("Empty audio filename")
            return jsonify({
                "error": True,
                "messages": ["No audio file selected"]
            }), 400
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            audio_file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Transcribe audio
            result = voice_service.transcribe_audio(temp_path)
            
            if result.get("error"):
                app.logger.error(f"Transcription error: {result.get('error')}")
                return jsonify({
                    "error": True,
                    "messages": [result.get("error")]
                }), 500
            
            app.logger.info(f"Transcription successful: {len(result.get('text', ''))} chars")
            
            return jsonify({
                "error": False,
                "text": result.get("text", ""),
                "confidence": result.get("confidence", 0.0),
                "language": result.get("language", "en-US")
            }), 200
            
        finally:
            # Clean up temporary file
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        app.logger.error(f"Transcription endpoint error: {type(e).__name__}: {str(e)}")
        return jsonify({
            "error": True,
            "messages": ["Failed to transcribe audio. Please try again."]
        }), 500


@app.route('/api/hospital-lookup', methods=['POST'])
def hospital_lookup():
    """
    Search for hospitals based on procedure type.
    
    Expects JSON with:
    - procedure: Procedure type (required)
    - location: Optional location for proximity search
    
    Returns JSON with:
    - error: Boolean indicating success/failure
    - hospitals: List of ranked hospitals (on success)
    - messages: Error messages (on failure)
    
    Validates: Requirements 13.5, 13.6, 13.7, 13.12, 13.13
    """
    try:
        app.logger.info("Hospital lookup request received")
        
        data = request.get_json()
        
        if not data:
            app.logger.warning("No JSON data in request")
            return jsonify({
                "error": True,
                "messages": ["No data provided"]
            }), 400
        
        procedure = data.get("procedure", "")
        
        if not procedure:
            app.logger.warning("No procedure specified")
            return jsonify({
                "error": True,
                "messages": ["Procedure type is required"]
            }), 400
        
        # Search for hospitals
        loc_data = data.get("location", None)
        location = None
        if isinstance(loc_data, dict):
            lat = loc_data.get("lat")
            lng = loc_data.get("lng")
            if lat is not None and lng is not None:
                location = (float(lat), float(lng))
        
        hospitals = hospital_lookup_service.search_hospitals(procedure, location=location)
        
        app.logger.info(f"Found {len(hospitals)} hospitals for procedure: {procedure}")
        
        all_doctors = []
        for hospital in hospitals:
            doctors = hospital.get("doctors", [])
            all_doctors.extend(doctors)
        
        return jsonify({
            "error": False,
            "hospitals": hospitals,
            "doctors": all_doctors
        }), 200
    
    except Exception as e:
        app.logger.error(f"Hospital lookup endpoint error: {type(e).__name__}: {str(e)}")
        return jsonify({
            "error": True,
            "messages": ["Failed to search hospitals. Please try again."]
        }), 500


@app.route('/api/generate-medication', methods=['POST'])
def generate_medication():
    """
    Generate medication recommendations based on symptoms.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": True, "messages": ["No data provided"]}), 400
        
        chief_complaint = data.get("chief_complaint", "")
        symptoms = data.get("symptoms_description", "")
        medications = data.get("current_medications", [])
        allergies = data.get("allergies", [])
        
        prompt = f"""
        Analyze the following patient details and recommend over-the-counter medications and lifestyle advice for symptom management.
        Chief Complaint: {chief_complaint}
        Symptoms: {symptoms}
        Current Medications: {', '.join(medications) if medications else 'None'}
        Allergies: {', '.join(allergies) if allergies else 'None'}
        
        Provide the response in the following JSON format ONLY:
        {{
            "medications": [
                {{"name": "Medication Name", "dosage": "Recommended dosage", "reason": "Why this is recommended"}}
            ],
            "advice": ["Lifestyle advice 1", "Lifestyle advice 2"],
            "warnings": ["Warning 1", "Warning 2"]
        }}
        """
        
        if llm_client and llm_client.is_available():
            response = llm_client.generate_with_prompt(
                "You are a medical assistant providing conservative symptom management advice. Output ONLY valid JSON.",
                prompt
            )
            if response:
                import json
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                json_str = json_match.group(1) if json_match else response
                return jsonify({"error": False, "data": json.loads(json_str)}), 200
        
        # Fallback
        return jsonify({
            "error": False,
            "data": {
                "medications": [{"name": "Rest & Hydration", "dosage": "As needed", "reason": "General recovery"}],
                "advice": ["Rest", "Drink plenty of fluids"],
                "warnings": ["Consult a doctor if symptoms worsen"]
            }
        }), 200
        
    except Exception as e:
        app.logger.error(f"Medication generation error: {e}")
        return jsonify({"error": True, "messages": [str(e)]}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_intake():
    """
    Analyze intake data and perform triage (Step 2 of wizard).
    
    Expects JSON with intake data (chief_complaint, symptoms, lat, lng, etc.)
    
    Returns JSON with:
    - error: Boolean indicating success/failure
    - triage: Triage results (urgency, specialty, red_flags)
    - doctors: Available doctors with slots
    - messages: Error messages (on failure)
    
    Validates: Requirements 13.8, 13.9, 13.12, 13.13
    """
    try:
        app.logger.info("Analysis request received")
        
        data = request.get_json()
        
        if not data:
            app.logger.warning("No JSON data in request")
            return jsonify({
                "error": True,
                "messages": ["No data provided"]
            }), 400
        
        # Extract location if provided
        lat = data.get("lat")
        lng = data.get("lng")
        location = (lat, lng) if lat and lng else None
        
        # DEBUG: Log location data
        app.logger.info(f"[DEBUG /api/analyze] lat={lat}, lng={lng}, location={location}")
        
        # Determine specialty from procedure or chief complaint
        procedure = data.get("procedure", "").lower()
        chief_complaint = data.get("chief_complaint", "").lower()
        
        # DEBUG: Log procedure and chief complaint
        app.logger.info(f"[DEBUG /api/analyze] procedure='{procedure}', chief_complaint='{chief_complaint}'")
        
        specialty = "General Medicine"
        specialty_keyword = None
        
        if "cardio" in procedure or "cardiac" in procedure or "heart" in chief_complaint or "chest" in chief_complaint:
            specialty = "Cardiology"
            specialty_keyword = "cardiology"
        elif "colon" in procedure or "endoscopy" in procedure:
            specialty = "Gastroenterology"
            specialty_keyword = "gastroenterology"
        elif "mri" in procedure or "ct" in procedure or "imaging" in procedure or "scan" in procedure:
            specialty = "Radiology"
            specialty_keyword = "radiology"
        elif "surgery" in procedure or "surgical" in procedure:
            specialty = "Surgery"
            specialty_keyword = "surgery"
        
        # DEBUG: Log specialty determination
        app.logger.info(f"[DEBUG /api/analyze] specialty='{specialty}', specialty_keyword='{specialty_keyword}'")
        
        # Search hospitals with real API if location available
        if location and specialty_keyword:
            app.logger.info("[DEBUG /api/analyze] Taking REAL API path (Geoapify)")
            from services.hospital_lookup_service import HospitalLookupService
            
            hospital_service = HospitalLookupService(mock_mode=False)
            
            hospitals = hospital_service.search_hospitals(
                procedure=specialty_keyword,
                location=location,
                radius_km=10.0
            )
            
            # Extract doctors from hospitals
            all_doctors = []
            for hospital in hospitals:
                doctors = hospital.get("doctors", [])
                all_doctors.extend(doctors)
        else:
            app.logger.info("[DEBUG /api/analyze] Taking AGENT WORKFLOW path (fallback)")
            app.logger.info(f"[DEBUG /api/analyze] Reason: location={location is not None}, specialty_keyword={specialty_keyword is not None}")
            # Fallback to agent workflow
            from agent.state import create_initial_state
            from agent.tools import (
                intake_node_tool,
                triage_node_tool,
                hospital_suggestion_node
            )
            
            state = create_initial_state(data)
            state = intake_node_tool(state, llm_client)
            state = triage_node_tool(state)
            state = hospital_suggestion_node(state)
            
            if state.get("errors"):
                app.logger.error(f"Analysis error: {state['errors']}")
                return jsonify({
                    "error": True,
                    "messages": state["errors"]
                }), 500
            
            triage_data = state.get("triage_data", {})
            hospital_data = state.get("hospital_data", {})
            urgency = triage_data.get("urgency_level", "routine")
            red_flags = triage_data.get("red_flags", [])
            all_doctors = hospital_data.get("doctors", [])
        
        # Care-Path Analysis using LLM
        care_path_prompt = f"""
        Analyze the following patient intake details and determine the care path.
        Patient Complaint: {chief_complaint}
        Procedure: {procedure}
        Location: {location}
        
        Provide the response in the following JSON format ONLY:
        {{
            "urgency": "routine", // or "urgent" or "emergency"
            "red_flags": ["list of red flags if any"],
            "care_path": "short patient-facing summary of the care path",
            "doctor_type": "type of doctor needed",
            "options": [
                {{"id": "medication", "title": "Medication & Rest", "desc": "Manage symptoms with prescribed medication"}},
                {{"id": "consultation", "title": "Consult a Specialist", "desc": "Visit a doctor for a thorough evaluation"}},
                {{"id": "surgery", "title": "Urgent Procedure/Surgery", "desc": "Immediate surgical intervention may be required"}}
            ]
        }}
        """
        
        urgency = "routine"
        red_flags = []
        care_path_summary = "General consultation and evaluation."
        doctor_type = specialty
        options = [
            {"id": "medication", "title": "Medication & Rest", "desc": "Manage symptoms with prescribed medication"},
            {"id": "consultation", "title": "Consult a Specialist", "desc": "Visit a doctor for a thorough evaluation"},
            {"id": "surgery", "title": "Urgent Procedure/Surgery", "desc": "Immediate surgical intervention may be required"}
        ]
        
        try:
            if llm_client and llm_client.is_available():
                response = llm_client.generate_with_prompt(
                    "You are a medical triage assistant determining care paths. Output ONLY valid JSON, no markdown formatting.",
                    care_path_prompt
                )
                if response:
                    import json
                    import re
                    # Strip markdown block if present
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                    json_str = json_match.group(1) if json_match else response
                    
                    analysis = json.loads(json_str)
                    urgency = analysis.get("urgency", "routine")
                    red_flags = analysis.get("red_flags", [])
                    care_path_summary = analysis.get("care_path", care_path_summary)
                    doctor_type = analysis.get("doctor_type", specialty)
                    specialty = doctor_type # Update specialty with LLM suggestion
                    if "options" in analysis:
                        options = analysis["options"]
        except Exception as e:
            app.logger.warning(f"Care-path LLM analysis failed: {e}")
            # Fallback to heuristics
            if "chest" in chief_complaint and "pain" in chief_complaint:
                urgency = "urgent"
                red_flags.append("Chest pain - requires urgent evaluation")
            elif "breath" in chief_complaint or "breathing" in chief_complaint:
                urgency = "urgent"
                red_flags.append("Difficulty breathing")
            elif "severe" in chief_complaint and "pain" in chief_complaint:
                urgency = "urgent"
                red_flags.append("Severe pain")
        
        app.logger.info(f"Analysis complete: urgency={urgency}, specialty={specialty}, doctors={len(all_doctors)}")
        
        return jsonify({
            "error": False,
            "triage": {
                "urgency": urgency,
                "specialty": specialty,
                "red_flags": red_flags,
                "care_path": care_path_summary,
                "options": options
            },
            "doctors": all_doctors
        }), 200
    
    except Exception as e:
        app.logger.error(f"Analysis endpoint error: {type(e).__name__}: {str(e)}")
        return jsonify({
            "error": True,
            "messages": ["Failed to analyze intake. Please try again."]
        }), 500


@app.route('/api/book-appointment', methods=['POST'])
def book_appointment():
    """
    Book appointment and generate prep summary (Step 4 of wizard).
    
    Expects JSON with:
    - intake_data: All intake data from Step 1
    - selected_doctor: Doctor object with name, specialty, hospital, etc.
    - selected_slot: Slot object with datetime_iso, duration, location
    
    Returns JSON with:
    - error: Boolean indicating success/failure
    - booking_confirmed: Boolean
    - booking: Booking details (confirmation_id, doctor_name, hospital, date_time)
    - patient_message: Prep instructions
    - clinician_summary: Clinician briefing
    - messages: Error messages (on failure)
    
    Validates: Requirements 13.10, 13.11, 13.12, 13.13
    """
    try:
        app.logger.info("Booking request received")
        
        data = request.get_json()
        
        if not data:
            app.logger.warning("No JSON data in request")
            return jsonify({
                "error": True,
                "messages": ["No data provided"]
            }), 400
        
        # Validate required booking fields
        intake_data = data.get("intake_data", {})
        selected_doctor = data.get("selected_doctor", {})
        selected_slot = data.get("selected_slot", {})
        
        if not selected_doctor:
            return jsonify({
                "error": True,
                "messages": ["Doctor selection is required"]
            }), 400
        
        if not selected_slot:
            return jsonify({
                "error": True,
                "messages": ["Time slot selection is required"]
            }), 400
        
        # Merge intake data with booking selections
        raw_intake = intake_data.copy()
        raw_intake["clinician_name"] = selected_doctor.get("name", "Doctor")
        raw_intake["appointment_datetime"] = selected_slot.get("datetime_display", "")
        raw_intake["selected_hospital"] = selected_doctor.get("hospital", "")
        raw_intake["selected_location"] = selected_slot.get("location", "")
        
        # Run full agent workflow to generate prep instructions
        result = run_agent(
            raw_intake=raw_intake,
            rules_engine=rules_engine,
            retrieval_service=retrieval_service,
            llm_client=llm_client,
            storage=storage
        )
        
        if result.get("error"):
            app.logger.error(f"Booking error: {result.get('messages')}")
            return jsonify({
                "error": True,
                "messages": result.get("messages", ["Booking failed"])
            }), 500
        
        # Generate confirmation ID
        import uuid
        confirmation_id = f"PREP-{uuid.uuid4().hex[:8].upper()}"
        
        # Extract patient info
        patient_name = intake_data.get("patient_name", "Patient")
        patient_email = intake_data.get("email", "")
        patient_phone = intake_data.get("phone", "")
        doctor_name = selected_doctor.get("name", "Doctor")
        hospital_name = selected_doctor.get("hospital", "Hospital")
        hospital_location = selected_doctor.get("hospital_location", "")
        appointment_datetime = selected_slot.get("datetime_display", "")
        prep_message = result.get("patient_message", "")
        
        # Create calendar event if configured
        try:
            event_id = calendar_service.create_appointment_event(
                title=f"{intake_data.get('appointment_type', 'Appointment')} - {patient_name}",
                start_time=selected_slot.get("datetime_iso", ""),
                end_time=selected_slot.get("datetime_iso", ""),
                description=f"Procedure: {intake_data.get('procedure', 'N/A')}\nDoctor: {doctor_name}",
                attendee_email=patient_email if patient_email else "",
                location=f"{hospital_name}, {hospital_location}"
            )
            app.logger.info(f"Calendar event created: {event_id}")
        except Exception as e:
            app.logger.warning(f"Calendar event creation failed: {e}")
        
        # Send confirmation email to patient
        if patient_email:
            try:
                email_result = email_service.send_booking_confirmation(
                    to_email=patient_email,
                    patient_name=patient_name,
                    appointment_datetime=appointment_datetime,
                    doctor=doctor_name,
                    location=f"{hospital_name}, {hospital_location}",
                    prep_summary=prep_message[:500] + "..." if len(prep_message) > 500 else prep_message
                )
                if email_result.get("success"):
                    app.logger.info(f"Patient confirmation email sent: {email_result.get('message_id')}")
                else:
                    app.logger.error(f"Patient email failed: {email_result.get('error')}")
            except Exception as e:
                app.logger.warning(f"Patient email exception: {e}")
        
        # Send notification email to hospital
        hospital_notify_email = os.getenv("HOSPITAL_NOTIFY_EMAIL", "")
        if hospital_notify_email:
            try:
                hospital_email_result = email_service.send_email(
                    to_email=hospital_notify_email,
                    subject=f"New Appointment Booked - {patient_name}",
                    html_content=f"""
                    <html>
                    <body style="font-family: Arial, sans-serif;">
                        <h2>New Appointment Notification</h2>
                        <p><strong>Patient:</strong> {patient_name}</p>
                        <p><strong>Doctor:</strong> {doctor_name}</p>
                        <p><strong>Hospital:</strong> {hospital_name}</p>
                        <p><strong>Date/Time:</strong> {appointment_datetime}</p>
                        <p><strong>Procedure:</strong> {intake_data.get('procedure', 'N/A')}</p>
                        <p><strong>Chief Complaint:</strong> {intake_data.get('chief_complaint', 'N/A')}</p>
                        <p><strong>Confirmation ID:</strong> {confirmation_id}</p>
                    </body>
                    </html>
                    """,
                    plain_content=f"New appointment booked for {patient_name} with {doctor_name} on {appointment_datetime}"
                )
                app.logger.info(f"Hospital notification email sent: {hospital_email_result.get('message_id')}")
            except Exception as e:
                app.logger.warning(f"Hospital notification email failed: {e}")
        
        # Send confirmation SMS to patient
        if patient_phone:
            try:
                sms_result = sms_service.send_booking_confirmation(
                    to_phone=patient_phone,
                    appointment_datetime=appointment_datetime,
                    doctor=doctor_name,
                    location=f"{hospital_name}, {hospital_location}"
                )
                app.logger.info(f"Patient confirmation SMS sent: {sms_result.get('message_id')}")
            except Exception as e:
                app.logger.warning(f"Patient SMS failed: {e}")
        
        app.logger.info(f"Booking complete: confirmation_id={confirmation_id}")
        
        return jsonify({
            "error": False,
            "booking_confirmed": True,
            "booking": {
                "confirmation_id": confirmation_id,
                "doctor_name": doctor_name,
                "hospital": hospital_name,
                "date_time": appointment_datetime
            },
            "patient_message": result.get("patient_message", ""),
            "clinician_summary": result.get("clinician_summary", ""),
            "message_id": result.get("message_id")
        }), 200
    
    except Exception as e:
        app.logger.error(f"Booking endpoint error: {type(e).__name__}: {str(e)}")
        return jsonify({
            "error": True,
            "messages": ["Failed to book appointment. Please try again."]
        }), 500


@app.route('/api/extract-intake', methods=['POST'])
def extract_intake():
    """
    Extract structured intake fields from voice transcript using LLM.
    
    Expects JSON with:
    - transcript: Raw voice transcript text
    
    Returns JSON with extracted fields or error.
    """
    try:
        app.logger.info("Extract intake request received")
        
        data = request.get_json()
        
        if not data or not data.get("transcript"):
            return jsonify({
                "error": True,
                "messages": ["No transcript provided"]
            }), 400
        
        transcript = data["transcript"]
        
        # Import extraction function
        from agent.tools import extract_intake_from_transcript
        
        # Extract fields using LLM
        extracted = extract_intake_from_transcript(transcript, llm_client)
        
        if extracted.get("error"):
            return jsonify({
                "error": True,
                "messages": [extracted["error"]]
            }), 400
        
        app.logger.info(f"Successfully extracted intake from transcript")
        
        return jsonify({
            "error": False,
            "extracted": extracted
        }), 200
    
    except Exception as e:
        app.logger.error(f"Extract intake error: {type(e).__name__}: {str(e)}")
        return jsonify({
            "error": True,
            "messages": ["Failed to extract intake. Please try again."]
        }), 500


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
