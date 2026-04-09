# Appointment Prep AI Agent

A local-ready Flask web application that generates personalized pre-appointment instructions for patients. The system combines a deterministic rules engine with optional AI-powered message generation to create safe, accurate, and friendly appointment preparation instructions.

## Overview

The Appointment Prep AI Agent helps medical office staff quickly generate customized appointment preparation instructions for patients. The application:

- **Runs entirely locally** with SQLite persistence (no cloud services required)
- **Uses deterministic rules** for all medical instructions (no AI invention)
- **Optionally leverages OpenAI** to rewrite messages in a friendly tone
- **Gracefully falls back** to template-based messages when AI is unavailable
- **Provides a premium medical UI** suitable for healthcare environments

## Features

- ✅ Generate personalized appointment prep instructions
- ✅ Support for multiple appointment types (Surgery, Imaging, Lab Work, Consultation)
- ✅ Deterministic rules engine for medical safety
- ✅ **LangGraph-powered AI agent architecture**
- ✅ **Node-based workflow with state management**
- ✅ **Agent reasoning trace for explainability**
- ✅ Optional AI-powered message enhancement
- ✅ Local SQLite database for message history
- ✅ Sample appointment data for quick testing
- ✅ Clean, professional healthcare UI
- ✅ No cloud dependencies (except optional OpenAI API)

## Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- 150MB disk space

### Step 1: Clone or Download

```bash
# If using git
git clone <repository-url>
cd appointment-prep-ai-agent

# Or download and extract the ZIP file
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- Flask (web framework)
- python-dotenv (environment configuration)
- openai (optional AI integration)
- **langgraph (agent orchestration framework)**
- **langchain (agent framework core)**
- **langchain-core (core components)**
- **langchain-openai (OpenAI integration)**
- pytest & hypothesis (testing frameworks)

### Step 3: Verify Installation

```bash
# Run tests to verify everything is working
python -m pytest tests/ -v
```

You should see all tests passing (149 tests).

## Configuration

### Environment Variables Setup

The application uses a `.env` file for configuration. This file is **not** included in the repository for security reasons.

#### Step 1: Create .env File

Copy the example file and customize it:

```bash
# On Windows
copy .env.example .env

# On macOS/Linux
cp .env.example .env
```

#### Step 2: Configure OpenAI API Key (Optional)

Open `.env` in a text editor and add your OpenAI API key:

```env
# OpenAI API Configuration
# Get your API key from: https://platform.openai.com/api-keys
# The application will work without this key using template fallback mode
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Important Notes:**
- The application works **without** an API key (uses template fallback)
- If you want AI-enhanced messages, get an API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- Never commit your `.env` file to version control
- Keep your API key secure and private

#### Step 3: Verify Configuration

```bash
# Test with API key
python app.py

# Test without API key (comment out OPENAI_API_KEY in .env)
python app.py
```

Both modes should work correctly.

## Usage Instructions

### Starting the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

You should see output like:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

### Using the Web Interface

1. **Open your browser** and navigate to `http://localhost:5000`

2. **View the landing page** with application overview

3. **Click "Go to Dashboard"** or navigate to `http://localhost:5000/dashboard`

4. **Fill out the appointment form:**
   - Patient Name
   - Appointment Type (Surgery, Imaging, Lab Work, Consultation, Procedure)
   - Procedure Description
   - Clinician Name
   - Appointment Date & Time
   - Channel Preference (Email, SMS, Print)
   - Special Notes (optional)

5. **Or load sample data:**
   - Click one of the "Load Sample" buttons
   - Sample data will pre-fill the form
   - Modify as needed

6. **Click "Generate Instructions"**
   - The system validates your input
   - Applies deterministic preparation rules
   - Generates a friendly message (AI or template)
   - Displays the result with preview and full message

7. **Review the generated message:**
   - Preview card shows a 2-3 sentence summary
   - Full message shows complete instructions
   - Rules explanation shows what requirements were applied
   - **Agent Reasoning Trace shows step-by-step agent execution**

8. **Copy or save the message:**
   - Click "Copy to Clipboard" to copy the message
   - Message is automatically saved to local database
   - View history by clicking "View History"

### Sample Appointment Types

The application includes sample data for:

1. **Surgery (Colonoscopy)**
   - 12-hour fasting required
   - Responsible adult driver needed
   - Arrive 30 minutes early

2. **Imaging (MRI with contrast)**
   - 4-hour fasting required
   - Allergy information important
   - Arrive 15 minutes early

3. **Lab Work (Fasting blood work)**
   - 8-hour fasting required
   - Arrive 10 minutes early

4. **Consultation (Follow-up)**
   - No fasting required
   - Bring medication list
   - Arrive 15 minutes early

## Testing Instructions

### Running All Tests

```bash
# Run all tests with verbose output
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=services --cov=agent --cov-report=html

# Run specific test file
python -m pytest tests/test_rules_engine.py -v
```

### Test Categories

**Unit Tests:**
- `test_rules_engine.py` - Deterministic rules logic
- `test_validation.py` - Input validation
- `test_message_builder.py` - Message generation
- `test_llm_client.py` - OpenAI API integration
- `test_storage.py` - Database operations

**Integration Tests:**
- `test_orchestrator_integration.py` - End-to-end workflow
- `test_message_builder_integration.py` - Message generation with rules
- `test_storage_integration.py` - Database round-trip
- `test_validation_integration.py` - Validation with models

**Property-Based Tests:**
- Uses Hypothesis library for property testing
- Tests universal properties across many inputs
- Validates correctness properties from requirements

### Running Property-Based Tests

```bash
# Run with Hypothesis examples
python -m pytest tests/ -v --hypothesis-show-statistics

# Run with more examples (slower but more thorough)
python -m pytest tests/ -v --hypothesis-seed=random
```

### Test Coverage

Current test coverage: **90%+** across all modules

```bash
# Generate HTML coverage report
python -m pytest tests/ --cov=services --cov=agent --cov-report=html

# Open htmlcov/index.html in browser to view detailed coverage
```

## HIPAA Compliance Disclaimer

⚠️ **IMPORTANT: This application is NOT HIPAA compliant out of the box.**

### Current Limitations

This application is designed for **local development and testing** purposes. It does **NOT** include the following features required for HIPAA compliance:

1. **No User Authentication** - Anyone with access to the server can view all data
2. **No Access Controls** - No role-based permissions or audit logging
3. **No Encryption at Rest** - SQLite database is not encrypted
4. **No Encryption in Transit** - HTTP (not HTTPS) by default
5. **No Audit Logging** - No tracking of who accessed what data
6. **No Data Retention Policies** - No automatic data deletion
7. **No Business Associate Agreement** - OpenAI API usage may not be HIPAA compliant

### Making This Application HIPAA Compliant

If you need to use this application in a HIPAA-regulated environment, you must:

1. **Add Authentication & Authorization**
   - Implement user login (Flask-Login or similar)
   - Add role-based access control
   - Require strong passwords and MFA

2. **Encrypt Data**
   - Use SQLCipher for encrypted SQLite database
   - Deploy behind HTTPS (SSL/TLS certificates)
   - Encrypt backups

3. **Implement Audit Logging**
   - Log all data access and modifications
   - Include user, timestamp, and action
   - Store logs securely with retention policy

4. **Secure API Integration**
   - Use HIPAA-compliant LLM provider (or disable LLM)
   - Sign Business Associate Agreement with any third-party services
   - Ensure all PHI is de-identified before sending to external APIs

5. **Add Data Retention Policies**
   - Implement automatic data deletion after retention period
   - Provide secure data export and deletion features
   - Document data lifecycle

6. **Conduct Security Assessment**
   - Perform risk assessment
   - Implement security controls
   - Document policies and procedures
   - Train staff on HIPAA requirements

### Recommendations

- **For Production Use:** Consult with a HIPAA compliance expert
- **For Testing Only:** Use fake/synthetic patient data
- **For Development:** Do not use real patient information

## Troubleshooting

### Issue: Application won't start

**Symptoms:**
```
ModuleNotFoundError: No module named 'flask'
```

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Verify Python version
python --version  # Should be 3.11 or higher
```

### Issue: Database errors

**Symptoms:**
```
sqlite3.OperationalError: unable to open database file
```

**Solution:**
```bash
# Ensure data directory exists
mkdir data

# Check file permissions
# On Windows: Right-click data folder → Properties → Security
# On macOS/Linux: chmod 755 data/

# Delete and recreate database
rm data/appointments.db
python app.py  # Will recreate database
```

### Issue: OpenAI API errors

**Symptoms:**
```
openai.error.AuthenticationError: Invalid API key
```

**Solution:**
1. Check your `.env` file has correct API key format: `sk-...`
2. Verify API key is active at [OpenAI Platform](https://platform.openai.com/api-keys)
3. Check for extra spaces or quotes around the key
4. If issues persist, comment out `OPENAI_API_KEY` to use template fallback

### Issue: Template fallback always used

**Symptoms:**
- Messages are generated but not in friendly AI tone
- Console shows: "LLM client unavailable, using template fallback"

**Solution:**
1. Check `.env` file exists and contains `OPENAI_API_KEY`
2. Verify API key is not empty or whitespace
3. Restart the application after modifying `.env`
4. Check OpenAI API status at [status.openai.com](https://status.openai.com)

### Issue: Sample data not loading

**Symptoms:**
```
FileNotFoundError: data/sample_appointments.json
```

**Solution:**
```bash
# Verify file exists
ls data/sample_appointments.json  # macOS/Linux
dir data\sample_appointments.json  # Windows

# If missing, restore from backup or repository
```

### Issue: Port 5000 already in use

**Symptoms:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 5000
# On macOS/Linux:
lsof -i :5000
kill -9 <PID>

# On Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Or change port in app.py:
# app.run(debug=True, host='0.0.0.0', port=5001)
```

### Issue: Tests failing

**Symptoms:**
```
FAILED tests/test_storage.py::test_save_message
```

**Solution:**
```bash
# Clean test artifacts
rm -rf .pytest_cache .hypothesis

# Reinstall test dependencies
pip install pytest hypothesis pytest-mock

# Run tests with verbose output
python -m pytest tests/ -v --tb=short

# If specific test fails, run it individually
python -m pytest tests/test_storage.py::test_save_message -v
```

### Issue: Form validation errors

**Symptoms:**
- Red error messages appear below form fields
- "Appointment date must be in the future"

**Solution:**
1. Ensure all required fields are filled
2. Check date is in the future (not today or past)
3. Verify appointment type is from dropdown list
4. Check patient name is under 100 characters
5. Verify procedure description is under 200 characters

### Getting Help

If you encounter issues not covered here:

1. Check the console output for error messages
2. Review the application logs
3. Verify all dependencies are installed correctly
4. Ensure Python version is 3.11 or higher
5. Try running with a fresh virtual environment

## Project Structure

```
appointment-prep-ai-agent/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment configuration template
├── .gitignore                      # Git ignore rules
├── README.md                       # This file
│
├── agent/                          # LangGraph Agent
│   ├── graph.py                   # LangGraph StateGraph definition
│   ├── state.py                   # Agent state TypedDict
│   ├── tools.py                   # Service wrappers as tools
│   ├── prompts.py                 # System prompts
│   └── README.md                  # Agent documentation
│
├── services/                       # Core business logic
│   ├── rules_engine.py            # Deterministic rules
│   ├── message_builder.py         # Message generation
│   ├── llm_client.py              # OpenAI integration
│   ├── storage.py                 # SQLite persistence
│   ├── validation.py              # Input validation
│   └── models.py                  # Data models
│
├── templates/                      # Jinja2 HTML templates
│   ├── base.html                  # Base template
│   ├── index.html                 # Landing page
│   └── dashboard.html             # Main dashboard
│
├── static/                         # Static assets
│   ├── css/
│   │   └── styles.css             # Application styles
│   └── js/
│       └── app.js                 # Frontend JavaScript
│
├── data/                           # Data files
│   ├── design_tokens.json         # UI design system
│   ├── page_content.json          # Page content
│   ├── sample_appointments.json   # Sample data
│   └── appointments.db            # SQLite database (auto-created)
│
└── tests/                          # Test suite
    ├── test_rules_engine.py       # Rules engine tests
    ├── test_validation.py         # Validation tests
    ├── test_message_builder.py    # Message builder tests
    ├── test_llm_client.py         # LLM client tests
    ├── test_storage.py            # Storage tests
    ├── test_orchestrator.py       # Orchestrator tests
    └── *_integration.py           # Integration tests
```

## Architecture

### Component Overview

1. **Flask Application (app.py)**
   - HTTP request/response handling
   - Route definitions
   - Template rendering
   - Configuration loading

2. **LangGraph Agent (agent/graph.py)**
   - **NEW**: Core orchestration using LangGraph StateGraph
   - Node-based workflow execution
   - State management across agent steps
   - Conditional routing and error handling

3. **Agent State (agent/state.py)**
   - **NEW**: TypedDict defining agent state structure
   - Tracks data flow through the agent
   - Maintains reasoning trace for explainability

4. **Agent Tools (agent/tools.py)**
   - **NEW**: Service wrappers as LangGraph tools
   - Each tool updates agent state
   - Logging and tracing for transparency

5. **Rules Engine (services/rules_engine.py)**
   - Deterministic medical rules
   - Appointment type mapping
   - Safety-critical logic
   - No AI involvement

6. **Message Builder (services/message_builder.py)**
   - Message generation
   - Template fallback
   - LLM coordination
   - Preview generation

7. **LLM Client (services/llm_client.py)**
   - OpenAI API integration
   - Graceful error handling
   - Fallback on failure
   - System prompt enforcement

8. **Storage Service (services/storage.py)**
   - SQLite database management
   - CRUD operations
   - Message history
   - Persistence layer

### Data Flow (LangGraph Agent Architecture)

```
User Input → Flask → LangGraph Agent → Tools → Response
                         ↓
                    Agent State
                         ↓
            ┌────────────┴────────────┐
            ↓                         ↓
    validate_input              apply_rules
            ↓                         ↓
    build_message            enhance_message
            ↓                         ↓
       save_output ──────────→ Agent Trace
```

**Agent Flow:**

1. User submits appointment data via web form
2. Flask calls LangGraph agent with input data
3. Agent creates initial state
4. **Node: validate_input** - Validates all required fields
5. **Node: apply_rules** - Applies deterministic preparation rules
6. **Node: build_message** - Generates structured template message
7. **Node: enhance_message** - Optionally enhances with LLM (if available)
8. **Node: save_output** - Saves to SQLite database
9. Agent returns final state with results and reasoning trace
10. Flask returns JSON response with message and agent trace

## License

This project is provided as-is for educational and development purposes.

## Contributing

This is a demonstration project. For production use, please implement proper security, authentication, and HIPAA compliance measures.

## Support

For questions or issues, please refer to the Troubleshooting section above.
