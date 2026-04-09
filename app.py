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
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from services.rules_engine import RulesEngine
from services.message_builder import MessageBuilder
from services.llm_client import LLMClient
from services.storage import StorageService
from services.prep_plan_builder import PrepPlanBuilder
from agent.graph import run_agent

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Load configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

# Initialize services
rules_engine = RulesEngine()
llm_client = LLMClient(api_key=app.config['OPENAI_API_KEY'])
message_builder = MessageBuilder(llm_client)
prep_plan_builder = PrepPlanBuilder()
storage = StorageService()

# Initialize database on startup (Requirement 8.10)
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
    Generate appointment prep instructions via AJAX.
    
    Expects JSON request body with appointment data.
    Returns JSON with preview, full_message, rules_explanation, message_id, llm_used.
    
    Validates: Requirements 6.3, 6.4, 6.5, 8.1, 8.2, 8.4, 8.5, 8.6, 8.8, 8.9
    """
    try:
        # Parse request data
        appointment_data = request.get_json()
        
        if not appointment_data:
            app.logger.warning("Generate endpoint called with no appointment data")
            return jsonify({
                "error": True,
                "messages": ["No appointment data provided"]
            }), 400
        
        # Generate message using LangGraph agent
        result = run_agent(
            appointment_data,
            rules_engine,
            prep_plan_builder,
            message_builder,
            llm_client,
            storage
        )
        
        # Check for validation errors (Requirement 6.4, 8.1, 8.2)
        if result.get("error"):
            app.logger.info(f"Validation errors: {result.get('messages')}")
            return jsonify(result), 400
        
        # Return success (Requirement 6.3)
        return jsonify(result), 200
        
    except ValueError as e:
        # Validation error handling (Requirement 8.1, 8.2)
        app.logger.warning(f"Validation error in generate endpoint: {str(e)}")
        return jsonify({
            "error": True,
            "messages": [str(e)]
        }), 400
    except Exception as e:
        # Server error handling (Requirement 6.5, 8.5, 8.6)
        # Log error without exposing PII (Requirement 8.4)
        app.logger.error(f"Server error in generate endpoint: {type(e).__name__}: {str(e)}")
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
