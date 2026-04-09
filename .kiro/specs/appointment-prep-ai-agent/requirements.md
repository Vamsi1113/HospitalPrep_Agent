# Requirements Document: Appointment Prep AI Agent

## Introduction

The Appointment Prep AI Agent is a local-ready Flask web application that generates personalized pre-appointment instructions for patients. The system ensures patient safety by using a deterministic rules engine for all medical instructions while optionally leveraging AI to improve message clarity and tone. The application runs entirely locally with SQLite persistence, requires no cloud services, and provides a premium medical UI experience suitable for healthcare environments.

## Glossary

- **System**: The Appointment Prep AI Agent application
- **Rules_Engine**: The deterministic component that determines all medical preparation requirements
- **Message_Builder**: The component that generates human-readable messages from structured rules
- **LLM_Client**: The optional AI component that rewrites messages in a friendly tone without inventing medical instructions
- **Storage_Service**: The SQLite-based persistence layer for generated messages
- **Agent_Orchestrator**: The workflow coordinator that manages the message generation pipeline
- **PrepRules**: A structured data object containing all preparation requirements for an appointment
- **Medical_Instruction**: Any requirement related to fasting, medications, items to bring, or arrival time
- **Template_Fallback**: The non-AI message generation mode used when LLM is unavailable
- **Appointment_Data**: Patient and appointment information including name, type, procedure, clinician, datetime, and channel preference

## Requirements

### Requirement 1: Appointment Data Validation

**User Story:** As a medical office staff member, I want the system to validate appointment data before generating instructions, so that I can ensure all required information is present and correct.

#### Acceptance Criteria

1. WHEN appointment data is submitted THEN the System SHALL validate that patient_name, appointment_type, procedure, clinician_name, appointment_datetime, and channel_preference are present and non-empty
2. WHEN patient_name exceeds 100 characters THEN the System SHALL reject the input with a descriptive error message
3. WHEN appointment_type is not in the predefined valid types list THEN the System SHALL reject the input with a descriptive error message
4. WHEN procedure description exceeds 200 characters THEN the System SHALL reject the input with a descriptive error message
5. WHEN clinician_name exceeds 100 characters THEN the System SHALL reject the input with a descriptive error message
6. WHEN appointment_datetime is not a valid ISO format datetime THEN the System SHALL reject the input with a descriptive error message
7. WHEN appointment_datetime is in the past or present THEN the System SHALL reject the input with error message "Appointment date must be in the future"
8. WHEN channel_preference is not one of "email", "sms", or "print" THEN the System SHALL reject the input with a descriptive error message
9. WHEN validation fails THEN the System SHALL return all error messages in a list
10. WHEN validation succeeds THEN the System SHALL return (True, empty list)

### Requirement 2: Deterministic Preparation Rules

**User Story:** As a medical office staff member, I want the system to apply consistent preparation rules based on appointment type, so that patients receive accurate and safe instructions.

#### Acceptance Criteria

1. WHEN appointment_type is "Surgery" or procedure contains "surgery" THEN the Rules_Engine SHALL set fasting_required to True, fasting_hours to 8, arrival_minutes_early to 60, and requires_responsible_adult to True
2. WHEN procedure contains "colonoscopy" or "endoscopy" THEN the Rules_Engine SHALL set fasting_required to True, fasting_hours to 12, arrival_minutes_early to 30, and requires_responsible_adult to True
3. WHEN appointment_type is "Imaging" or procedure contains "mri", "ct", "x-ray", or "ultrasound" THEN the Rules_Engine SHALL set arrival_minutes_early to 15
4. WHEN procedure contains "contrast" and appointment_type is "Imaging" THEN the Rules_Engine SHALL set fasting_required to True and fasting_hours to 4
5. WHEN procedure contains "blood" or "lab" THEN the Rules_Engine SHALL set arrival_minutes_early to 10
6. WHEN procedure contains "fasting" and procedure contains "blood" or "lab" THEN the Rules_Engine SHALL set fasting_required to True and fasting_hours to 8
7. FOR ALL appointment types THEN the Rules_Engine SHALL include "Photo ID" and "Insurance Card" in items_to_bring
8. WHEN fasting_required is False THEN the Rules_Engine SHALL set fasting_hours to 0
9. WHEN fasting_required is True THEN the Rules_Engine SHALL set fasting_hours to a positive integer
10. FOR ALL rules applications THEN the Rules_Engine SHALL assign category to one of "surgery", "endoscopy", "imaging", "lab", or "consultation"

### Requirement 3: Message Generation with Safety Constraints

**User Story:** As a medical office staff member, I want the system to generate clear appointment preparation messages, so that patients understand what they need to do before their appointment.

#### Acceptance Criteria

1. WHEN generating a message THEN the Message_Builder SHALL include a greeting with the patient's name
2. WHEN generating a message THEN the Message_Builder SHALL include appointment details with appointment_type, procedure, clinician_name, and formatted appointment_datetime
3. WHEN fasting_required is True THEN the Message_Builder SHALL include fasting instructions with the specific number of fasting_hours
4. FOR ALL messages THEN the Message_Builder SHALL include a section listing all items from items_to_bring
5. FOR ALL messages THEN the Message_Builder SHALL include arrival time instructions with arrival_minutes_early
6. FOR ALL messages THEN the Message_Builder SHALL include medication_instructions from PrepRules
7. WHEN requires_responsible_adult is True THEN the Message_Builder SHALL include transportation warning about needing a responsible adult driver
8. FOR ALL warnings in special_warnings THEN the Message_Builder SHALL include each warning prefixed with "IMPORTANT:"
9. FOR ALL messages THEN the Message_Builder SHALL include a closing with contact information
10. WHEN generating a message THEN the Message_Builder SHALL produce output between 200 and 2000 characters
11. FOR ALL generated messages THEN the System SHALL ensure no medical instructions are present that were not determined by the Rules_Engine

### Requirement 4: LLM Integration with Graceful Fallback

**User Story:** As a medical office staff member, I want the system to generate friendly, readable messages when AI is available, but still function when AI is unavailable, so that the system is reliable regardless of API availability.

#### Acceptance Criteria

1. WHEN LLM_Client is initialized with a valid API key THEN the LLM_Client SHALL set available to True
2. WHEN LLM_Client is initialized without an API key THEN the LLM_Client SHALL set available to False
3. WHEN LLM_Client.is_available() returns False THEN the Message_Builder SHALL use template_fallback mode
4. WHEN LLM_Client.is_available() returns True THEN the Message_Builder SHALL attempt to use LLM for message rewriting
5. WHEN LLM API call fails or times out THEN the LLM_Client SHALL return None
6. WHEN LLM_Client returns None THEN the Message_Builder SHALL fall back to template-based message generation
7. WHEN using LLM for rewriting THEN the System SHALL provide a system prompt that explicitly forbids inventing medical instructions
8. WHEN LLM rewrites a message THEN the System SHALL preserve all medical instructions, times, items, and requirements from the structured content
9. FOR ALL message generation requests THEN the System SHALL return a result with llm_used flag indicating whether LLM was used

### Requirement 5: Message Persistence and Retrieval

**User Story:** As a medical office staff member, I want the system to save generated messages to a local database, so that I can retrieve message history and track what instructions were sent to patients.

#### Acceptance Criteria

1. WHEN the System starts THEN the Storage_Service SHALL initialize the SQLite database schema if it does not exist
2. WHEN a message is generated THEN the Storage_Service SHALL save the appointment_data, generated_text, and rules_used to the database
3. WHEN saving a message THEN the Storage_Service SHALL return a positive integer message_id
4. WHEN saving a message THEN the Storage_Service SHALL automatically set generated_at timestamp to current datetime
5. WHEN retrieving a message by message_id THEN the Storage_Service SHALL return the complete message record or None if not found
6. WHEN retrieving message history THEN the Storage_Service SHALL return the most recent messages up to the specified limit
7. WHEN deleting a message by message_id THEN the Storage_Service SHALL remove the record and return True if successful
8. WHEN a database error occurs during save THEN the Storage_Service SHALL raise an exception with a descriptive error message

### Requirement 6: Web Interface and User Experience

**User Story:** As a medical office staff member, I want a clean, professional web interface to generate appointment prep messages, so that I can efficiently create instructions for patients.

#### Acceptance Criteria

1. WHEN accessing the root URL "/" THEN the System SHALL render a landing page with application overview
2. WHEN accessing "/dashboard" THEN the System SHALL render the main appointment prep form
3. WHEN submitting the form via POST to "/generate" THEN the System SHALL return JSON with preview, full_message, rules_explanation, message_id, and llm_used
4. WHEN validation errors occur THEN the System SHALL return HTTP 400 with error messages in JSON format
5. WHEN a server error occurs THEN the System SHALL return HTTP 500 with error message in JSON format
6. WHEN accessing "/history" THEN the System SHALL return JSON with recent message history
7. WHEN accessing "/load-sample/<sample_id>" THEN the System SHALL return JSON with pre-filled sample appointment data
8. FOR ALL rendered pages THEN the System SHALL use Jinja2 templates with design tokens from design_tokens.json
9. FOR ALL rendered pages THEN the System SHALL apply premium healthcare UI styling with appropriate colors, typography, and spacing
10. WHEN displaying generated messages THEN the System SHALL provide a preview card with 2-3 sentence summary

### Requirement 7: Sample Data Loading

**User Story:** As a medical office staff member, I want to load sample appointment data, so that I can quickly test the system and see example outputs.

#### Acceptance Criteria

1. WHEN the System starts THEN the System SHALL load sample appointment data from data/sample_appointments.json
2. WHEN accessing "/load-sample/<sample_id>" with a valid ID THEN the System SHALL return the corresponding sample appointment data
3. WHEN accessing "/load-sample/<sample_id>" with an invalid ID THEN the System SHALL return HTTP 404 with error message
4. WHEN sample_appointments.json file is missing THEN the System SHALL return an empty list and display "No sample data available"
5. FOR ALL sample data THEN the System SHALL include at least examples for surgery, imaging, and lab work appointment types

### Requirement 8: Error Handling and Recovery

**User Story:** As a medical office staff member, I want the system to handle errors gracefully and provide clear recovery options, so that I can resolve issues without losing work.

#### Acceptance Criteria

1. WHEN required fields are missing THEN the System SHALL display error messages in a red alert box above the form
2. WHEN form fields have errors THEN the System SHALL highlight those fields with a red border
3. WHEN LLM API fails THEN the System SHALL automatically use template fallback without user intervention
4. WHEN LLM API fails THEN the System SHALL log a warning message for administrator review
5. WHEN database write fails THEN the System SHALL display error "Failed to save message. Please try again."
6. WHEN database write fails THEN the System SHALL still display the generated message so it is not lost
7. WHEN database write fails THEN the System SHALL provide a "Copy to Clipboard" button as a workaround
8. WHEN an invalid date is entered THEN the System SHALL display error message below the date input field
9. WHEN sample data file is missing THEN the System SHALL disable sample data buttons but allow manual form entry
10. WHEN database schema is not initialized THEN the System SHALL automatically create it on app startup

### Requirement 9: Configuration Management

**User Story:** As a system administrator, I want to configure the application using environment variables, so that I can manage API keys and settings securely.

#### Acceptance Criteria

1. WHEN the System starts THEN the System SHALL load configuration from a .env file if present
2. WHEN OPENAI_API_KEY is present in .env THEN the System SHALL initialize LLM_Client with the API key
3. WHEN OPENAI_API_KEY is not present in .env THEN the System SHALL initialize LLM_Client in fallback mode
4. FOR ALL deployments THEN the System SHALL provide a .env.example file with placeholder values
5. FOR ALL deployments THEN the System SHALL include .env in .gitignore to prevent accidental commits
6. WHEN an invalid API key is provided THEN the System SHALL gracefully fall back to template mode
7. FOR ALL configuration errors THEN the System SHALL log clear error messages to help administrators diagnose issues

### Requirement 10: Agent Workflow Orchestration

**User Story:** As a developer, I want the system to orchestrate the message generation workflow through clear stages, so that the process is maintainable and extensible.

#### Acceptance Criteria

1. WHEN generating a message THEN the Agent_Orchestrator SHALL execute stages in order: intake, rules, draft, review, persist
2. WHEN in intake stage THEN the Agent_Orchestrator SHALL validate appointment data and normalize inputs
3. WHEN in rules stage THEN the Agent_Orchestrator SHALL apply deterministic preparation rules
4. WHEN in draft stage THEN the Agent_Orchestrator SHALL generate the message text using LLM or template
5. WHEN in review stage THEN the Agent_Orchestrator SHALL format preview and rules explanations
6. WHEN in persist stage THEN the Agent_Orchestrator SHALL save the result to the database
7. WHEN any stage fails THEN the Agent_Orchestrator SHALL capture errors and include them in the result
8. FOR ALL workflow executions THEN the Agent_Orchestrator SHALL maintain state across stages
9. WHEN workflow completes THEN the Agent_Orchestrator SHALL return a complete result dictionary

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: No Invented Medical Instructions

*For any* appointment data and generated message, all medical instructions in the generated message must come from the Rules_Engine output and not be invented by the LLM or any other component.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.11, 4.7, 4.8**

### Property 2: Validation Idempotence

*For any* appointment data, validating it multiple times must always produce the same result (same validity status and same error messages).

**Validates: Requirements 1.1, 1.9, 1.10**

### Property 3: Fasting Rules Consistency

*For any* PrepRules object, if fasting_required is False then fasting_hours must be 0, and if fasting_required is True then fasting_hours must be greater than 0.

**Validates: Requirements 2.8, 2.9**

### Property 4: Message Completeness

*For any* appointment data and PrepRules, the generated message must contain greeting, appointment details, items to bring, and arrival time sections, and must conditionally include fasting instructions when fasting_required is True and transportation warning when requires_responsible_adult is True.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9**

### Property 5: Database Round-Trip

*For any* appointment data, generated message, and rules, if a message is saved with save_message() returning message_id, then get_message(message_id) must return a record where the full_message field equals the original generated message.

**Validates: Requirements 5.3, 5.5**

### Property 6: LLM Fallback Equivalence

*For any* appointment data and PrepRules, when LLM is unavailable, calling build_full_message() with use_llm=True must produce the same result as calling build_template_message().

**Validates: Requirements 4.3, 4.5, 4.6**

### Property 7: Validation Error Non-Empty

*For any* appointment data, if validate_appointment_data() returns (False, errors), then the errors list must be non-empty and every error message must be a non-empty string.

**Validates: Requirements 1.9**

### Property 8: Category Assignment Completeness

*For any* appointment_type and procedure, apply_rules() must return a PrepRules object where category is one of "surgery", "endoscopy", "imaging", "lab", or "consultation".

**Validates: Requirements 2.10**

### Property 9: Mandatory Items Inclusion

*For any* appointment_type and procedure, the PrepRules returned by apply_rules() must include "Photo ID" and "Insurance Card" in the items_to_bring list.

**Validates: Requirements 2.7**

### Property 10: Message Length Bounds

*For any* appointment data and PrepRules, the message generated by build_full_message() must be between 200 and 2000 characters in length.

**Validates: Requirements 3.10**

### Property 11: Future Date Validation

*For any* appointment data where appointment_datetime is in the past or present, validate_appointment_data() must return (False, errors) where errors contains "Appointment date must be in the future".

**Validates: Requirements 1.7**

### Property 12: Positive Message ID

*For any* successful save_message() operation, the returned message_id must be a positive integer greater than 0.

**Validates: Requirements 5.3**
