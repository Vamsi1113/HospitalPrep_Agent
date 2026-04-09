# Implementation Plan: Appointment Prep AI Agent

## Overview

This implementation plan breaks down the Flask-based appointment prep AI agent into discrete coding tasks. The system uses a deterministic rules engine for all medical instructions, with optional LLM integration for message rewriting. All data is stored locally in SQLite, and the application provides a premium healthcare UI experience.

The implementation follows a bottom-up approach: core services first, then agent orchestration, then Flask routes, and finally frontend integration.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create directory structure: services/, agent/, templates/, static/, data/
  - Create requirements.txt with Flask, python-dotenv, openai, pytest, hypothesis
  - Create .env.example with OPENAI_API_KEY placeholder
  - Create .gitignore for .env, __pycache__, *.db files
  - _Requirements: 9.4, 9.5_

- [x] 2. Implement data models and validation
  - [x] 2.1 Create data models in services/models.py
    - Define AppointmentData dataclass with validation rules
    - Define PrepRules dataclass with all preparation fields
    - Define GeneratedMessage dataclass for persistence
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [ ]* 2.2 Write property test for data model validation
    - **Property 2: Validation Idempotence**
    - **Validates: Requirements 1.1, 1.9, 1.10**

  - [x] 2.3 Implement validation logic in services/validation.py
    - Write validate_appointment_data() function with all field checks
    - Implement required field validation
    - Implement field length validation
    - Implement date validation (future dates only)
    - Implement appointment_type and channel_preference whitelist validation
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10_

  - [ ]* 2.4 Write property test for validation error completeness
    - **Property 7: Validation Error Non-Empty**
    - **Validates: Requirements 1.9**

  - [ ]* 2.5 Write property test for future date validation
    - **Property 11: Future Date Validation**
    - **Validates: Requirements 1.7**

- [x] 3. Implement rules engine
  - [x] 3.1 Create RulesEngine class in services/rules_engine.py
    - Implement apply_rules() method with all appointment type logic
    - Implement surgery rules (8hr fasting, 60min early, responsible adult)
    - Implement endoscopy/colonoscopy rules (12hr fasting, 30min early)
    - Implement imaging rules (15min early, conditional 4hr fasting for contrast)
    - Implement lab work rules (10min early, conditional 8hr fasting)
    - Implement default consultation rules
    - Ensure all rules include mandatory items: Photo ID, Insurance Card
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

  - [ ]* 3.2 Write property test for fasting rules consistency
    - **Property 3: Fasting Rules Consistency**
    - **Validates: Requirements 2.8, 2.9**

  - [ ]* 3.3 Write property test for category assignment
    - **Property 8: Category Assignment Completeness**
    - **Validates: Requirements 2.10**

  - [ ]* 3.4 Write property test for mandatory items inclusion
    - **Property 9: Mandatory Items Inclusion**
    - **Validates: Requirements 2.7**

  - [ ]* 3.5 Write unit tests for rules engine
    - Test each appointment type category
    - Test edge cases for procedure string matching
    - Test combination rules (e.g., imaging with contrast)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement LLM client with graceful fallback
  - [x] 5.1 Create LLMClient class in services/llm_client.py
    - Implement __init__ with optional API key parameter
    - Implement is_available() method
    - Implement rewrite_message() with error handling and None return on failure
    - Implement generate_with_prompt() with system prompt support
    - Add timeout handling (5 seconds) for API calls
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

  - [ ]* 5.2 Write property test for LLM fallback equivalence
    - **Property 6: LLM Fallback Equivalence**
    - **Validates: Requirements 4.3, 4.5, 4.6**

  - [ ]* 5.3 Write unit tests for LLM client
    - Test API availability check
    - Test successful API call (mocked)
    - Test API failure handling
    - Test None return on error
    - _Requirements: 4.1, 4.2, 4.5_

- [x] 6. Implement message builder
  - [x] 6.1 Create MessageBuilder class in services/message_builder.py
    - Implement build_preview() for 2-3 sentence summary
    - Implement build_full_message() with LLM integration
    - Implement build_template_message() for fallback mode
    - Implement format_rules_explanation() for structured rule display
    - Ensure all message sections: greeting, appointment details, fasting, items, arrival, medications, warnings, closing
    - Implement calculate_fasting_start_time() helper function
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 4.7, 4.8, 4.9_

  - [ ]* 6.2 Write property test for message completeness
    - **Property 4: Message Completeness**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9**

  - [ ]* 6.3 Write property test for message length bounds
    - **Property 10: Message Length Bounds**
    - **Validates: Requirements 3.10**

  - [ ]* 6.4 Write property test for no invented medical instructions
    - **Property 1: No Invented Medical Instructions**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.11, 4.7, 4.8**

  - [ ]* 6.5 Write unit tests for message builder
    - Test preview generation
    - Test template fallback mode
    - Test section inclusion based on rules
    - Test special character handling
    - _Requirements: 3.1, 3.2, 3.3, 3.10_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement storage service
  - [x] 8.1 Create StorageService class in services/storage.py
    - Implement __init__ with db_path parameter
    - Implement init_db() to create SQLite schema
    - Design schema: messages table with id, patient_name, appointment_type, procedure, clinician_name, appointment_datetime, channel_preference, full_message, rules_used (JSON), generated_at, llm_used
    - Implement save_message() with parameterized queries
    - Implement get_message() by message_id
    - Implement get_history() with limit parameter
    - Implement delete_message() by message_id
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [ ]* 8.2 Write property test for database round-trip
    - **Property 5: Database Round-Trip**
    - **Validates: Requirements 5.3, 5.5**

  - [ ]* 8.3 Write property test for positive message ID
    - **Property 12: Positive Message ID**
    - **Validates: Requirements 5.3**

  - [ ]* 8.4 Write unit tests for storage service
    - Test database initialization
    - Test message save and retrieve
    - Test history retrieval with pagination
    - Test message deletion
    - Test error handling for database failures
    - _Requirements: 5.1, 5.2, 5.3, 5.5, 5.7, 5.8_

- [x] 9. Implement agent orchestrator
  - [x] 9.1 Create orchestration function in agent/orchestrator.py
    - Implement orchestrate_prep_generation() main function
    - Step 1: Call validate_appointment_data()
    - Step 2: Call rules_engine.apply_rules()
    - Step 3: Call message_builder.build_full_message() with LLM or fallback
    - Step 4: Call message_builder.build_preview()
    - Step 5: Call message_builder.format_rules_explanation()
    - Step 6: Call storage.save_message()
    - Step 7: Return complete result dictionary
    - Add error handling for each step
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9_

  - [ ]* 9.2 Write integration tests for orchestrator
    - Test end-to-end flow with valid data
    - Test validation error handling
    - Test LLM fallback integration
    - Test database persistence
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Create sample data and configuration files
  - [x] 11.1 Create data/sample_appointments.json
    - Add sample for surgery appointment (colonoscopy)
    - Add sample for imaging appointment (MRI with contrast)
    - Add sample for lab work appointment (fasting blood work)
    - Add sample for consultation appointment
    - _Requirements: 7.1, 7.2, 7.5_

  - [x] 11.2 Create data/design_tokens.json
    - Define color palette (primary, secondary, accent, neutral shades)
    - Define typography (font families, sizes, weights, line heights)
    - Define spacing scale (xs, sm, md, lg, xl, 2xl, 3xl)
    - Define effects (shadows, border-radius, transitions)
    - _Requirements: 6.8, 6.9_

  - [x] 11.3 Create data/page_content.json
    - Define brand information (name, tagline)
    - Define navigation items
    - Define hero section content
    - Define metrics and features for landing page
    - _Requirements: 6.1, 6.8_

- [x] 12. Implement Flask application and routes
  - [x] 12.1 Create Flask app in app.py
    - Initialize Flask app
    - Load configuration from .env using python-dotenv
    - Initialize all services (rules_engine, llm_client, message_builder, storage)
    - Call storage.init_db() on startup
    - Load design_tokens.json and page_content.json
    - _Requirements: 6.1, 6.2, 9.1, 9.2, 9.3, 5.1_

  - [x] 12.2 Implement route handlers
    - Implement GET / for landing page
    - Implement GET /dashboard for main form
    - Implement POST /generate for message generation (calls orchestrate_prep_generation)
    - Implement POST /save for explicit save (if needed)
    - Implement GET /history for message history
    - Implement GET /load-sample/<int:sample_id> for sample data loading
    - Add error handling for 400 and 500 responses
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.2, 7.3_

  - [ ]* 12.3 Write integration tests for Flask routes
    - Test GET / returns 200
    - Test GET /dashboard returns 200
    - Test POST /generate with valid data returns 200 with expected JSON
    - Test POST /generate with invalid data returns 400 with errors
    - Test GET /history returns 200 with JSON array
    - Test GET /load-sample/0 returns 200 with sample data
    - Test GET /load-sample/999 returns 404
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.2, 7.3, 7.4_

- [x] 13. Create Jinja2 templates
  - [x] 13.1 Create base template in templates/base.html
    - Define HTML structure with head, body, navigation
    - Include design tokens CSS variables
    - Include static CSS and JS references
    - Define blocks for title, content, scripts
    - _Requirements: 6.8, 6.9_

  - [x] 13.2 Create landing page template in templates/index.html
    - Extend base.html
    - Render hero section with page_content data
    - Render features section
    - Render metrics section
    - Add CTA button linking to /dashboard
    - _Requirements: 6.1, 6.8_

  - [x] 13.3 Create dashboard template in templates/dashboard.html
    - Extend base.html
    - Create appointment form with all required fields
    - Add patient_name, appointment_type, procedure, clinician_name inputs
    - Add appointment_datetime datetime-local input
    - Add channel_preference radio buttons
    - Add special_notes textarea
    - Add sample data loading buttons
    - Add result display area for preview and full message
    - Add rules explanation display area
    - Add error message display area
    - _Requirements: 6.2, 6.3, 6.10, 7.2_

- [x] 14. Create static assets
  - [x] 14.1 Create CSS in static/styles.css
    - Apply design tokens for colors, typography, spacing
    - Style landing page with premium healthcare aesthetic
    - Style dashboard form with clear labels and inputs
    - Style result cards with preview and full message
    - Style error messages with red alert styling
    - Style loading spinner for async operations
    - Add responsive design for mobile and tablet
    - _Requirements: 6.8, 6.9, 8.1, 8.2_

  - [x] 14.2 Create JavaScript in static/app.js
    - Implement form submission via AJAX to POST /generate
    - Implement form validation with error display
    - Implement sample data loading via GET /load-sample/<id>
    - Implement result display with preview and full message
    - Implement "Copy to Clipboard" functionality
    - Implement loading spinner during generation
    - Add debounced validation on form fields (300ms)
    - _Requirements: 6.3, 6.4, 6.10, 7.2, 8.3, 8.7_

- [x] 15. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 16. Implement error handling and recovery
  - [x] 16.1 Add error handling to Flask routes
    - Add try-catch blocks for all route handlers
    - Return 400 for validation errors with descriptive messages
    - Return 500 for server errors with safe error messages
    - Log errors without exposing PII
    - _Requirements: 8.1, 8.2, 8.4, 8.5, 8.6, 8.8, 8.9_

  - [x] 16.2 Add frontend error handling
    - Display validation errors in red alert box above form
    - Highlight form fields with errors using red border
    - Display server errors with user-friendly messages
    - Provide "Copy to Clipboard" button when save fails
    - Disable sample data buttons if sample file missing
    - _Requirements: 8.1, 8.2, 8.6, 8.7, 8.9_

  - [x] 16.3 Add LLM fallback logging
    - Log warning when LLM API fails
    - Log info when template fallback is used
    - Ensure no API keys are logged
    - _Requirements: 8.3, 8.4, 9.7_

- [x] 17. Add configuration and documentation
  - [x] 17.1 Create README.md
    - Add project overview and features
    - Add installation instructions
    - Add configuration instructions (.env setup)
    - Add usage instructions
    - Add testing instructions
    - Add HIPAA compliance disclaimer
    - Add troubleshooting section
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.6, 9.7_

  - [x] 17.2 Finalize .env.example
    - Add OPENAI_API_KEY with placeholder
    - Add comments explaining each variable
    - Add instructions for obtaining API key
    - _Requirements: 9.4_

  - [x] 17.3 Create requirements.txt
    - Pin all dependency versions
    - Add comments for optional dependencies
    - Group dependencies by purpose (core, testing, development)
    - _Requirements: 9.1, 9.2, 9.3_

- [x] 18. Final integration and testing
  - [x] 18.1 Run full test suite
    - Run pytest with coverage report
    - Ensure 90%+ coverage for services layer
    - Ensure 100% coverage for rules_engine
    - Fix any failing tests
    - _Requirements: All_

  - [ ]* 18.2 Run property-based tests
    - Run hypothesis tests with increased example count
    - Verify all 12 correctness properties pass
    - Document any property test failures
    - _Requirements: All correctness properties_

  - [x] 18.3 Manual end-to-end testing
    - Start Flask app locally
    - Test landing page loads correctly
    - Test dashboard form submission with valid data
    - Test sample data loading
    - Test message generation with LLM (if API key available)
    - Test message generation without LLM (template fallback)
    - Test error handling for invalid inputs
    - Test message history retrieval
    - Test responsive design on mobile
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6, 6.7, 7.2, 7.3_

- [x] 19. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation follows a bottom-up approach: services → orchestration → routes → frontend
- All medical instructions are determined by the rules engine (no AI invention)
- LLM is only used for message rewriting in a friendly tone
- The system gracefully falls back to template-based messages when LLM is unavailable
- All data is stored locally in SQLite (no cloud services except optional OpenAI API)
