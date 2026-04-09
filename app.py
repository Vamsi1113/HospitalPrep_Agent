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
from agent.graph import run_agent

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
        
        # Generate THREE-PHASE prep using LangGraph agent
        result = run_agent(
            raw_intake,
            rules_engine,
            retrieval_service,
            llm_client,
            storage
        )
        
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
def book_appointment():
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
        
        session_id = data.get("session_id", "default")
        
        # Get or create session state
        session_state = storage.get_session_state(session_id)
        if not session_state:
            session_state = {
                "chat_history": [],
                "appointment_type": data.get("appointment_type", ""),
                "procedure": data.get("procedure", "")
            }
        
        # Add patient question
        session_state["chat_history"].append({
            "role": "patient",
            "content": data["question"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Generate response using retrieval + LLM
        context_docs = []
        if retrieval_service and retrieval_service.is_available():
            protocols = retrieval_service.retrieve_protocols(
                appointment_type=session_state.get("appointment_type", ""),
                procedure=session_state.get("procedure", ""),
                max_results=2
            )
            context_docs = [p.get("content", "") for p in protocols]
        
        if llm_client and llm_client.is_available():
            context_str = "\n\n".join(context_docs)
            prompt = f"""You are a helpful medical appointment assistant. Answer the patient's question based on the context provided.

Context:
{context_str}

Patient Question: {data['question']}

Provide a clear, helpful answer. If the question is outside the scope of appointment preparation, politely redirect to contacting the clinic."""
            
            response = llm_client.generate_with_prompt(
                "You are a medical appointment assistant.",
                prompt
            )
        else:
            response = "I'm here to help with appointment preparation questions. For specific medical advice, please contact your doctor."
        
        # Add agent response
        session_state["chat_history"].append({
            "role": "agent",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Save session state
        storage.save_session_state(session_id, session_state)
        
        return jsonify({
            "error": False,
            "response": response,
            "chat_history": session_state["chat_history"]
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
    # Run Flask development server
    app.run(debug=True, host='0.0.0.0', port=5000)
