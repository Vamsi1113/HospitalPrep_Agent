# Project Context Summary: Hospital Pre-Appointment Management System

## 1. 🧾 Project Overview
This system is an AI-enhanced healthcare orchestration platform designed to streamline the pre-appointment experience for both patients and clinical staff. It automates the generation of highly personalized, procedure-specific preparation instructions by combining a **deterministic medical rules engine** with **LangGraph-driven AI agents**. The core purpose is to eliminate medical prep errors (such as fasting mistakes), reduce same-day cancellations, and provide clinicians with high-fidelity pre-visit briefings. It targets medical office coordinators, clinicians, and patients scheduled for complex procedures like surgeries, imaging, or specialized lab work.

## 2. ⚙️ Current Features (Implemented)
*   **Intake Processing**: Automated symptom normalization and follow-up question generation. (Handled by `intake` node)
*   **Symptom Triage**: Real-time classification of urgency (Routine, Urgent, Emergency) and red-flag identification. (Handled by `triage` node)
*   **Protocol Retrieval (RAG)**: Dynamic fetching of clinic-specific protocols based on appointment type. (Handled by `protocol_retrieval` node)
*   **Deterministic Prep Rules**: High-safety engine for fasting, transport, and document requirements. (Handled by `admin_prep` node)
*   **Clinical Summary Generation**: AI-summarized patient history and medication conflict alerts for physicians. (Handled by `clinical_briefing` and `clinician_summary` nodes)
*   **Personalized Patient Guides**: Dynamic generation of friendly, warm, and thorough preparation messages without using static templates. (Handled by `patient_message` node)
*   **Agent Reasoning Trace**: Full explainability logs showing every decision step made by the agent for auditability. (Handled by LangGraph orchestration)
*   **Persistence & History**: Secure SQLite storage for all generated instructions and patient interactions. (Handled by `save` node)

## 3. 🧠 Agent Architecture (LangGraph)
The system utilizes a **Linear StateGraph** orchestration to ensure a consistent three-phase clinical workflow.
*   **Nodes & Responsibilities**:
    *   `intake`: Extracts and normalizes patient symptoms using LLM.
    *   `triage`: Determines clinical urgency and identifies immediate risks.
    *   `protocol_retrieval`: Queries available protocols (or falls back to rules).
    *   `admin_prep`: Calculates logistics (arrival times, fasting windows) using `RulesEngine`.
    *   `clinical_briefing`: Analyzes EHR context for medical conflicts.
    *   `patient_message`: Synthesizes state into a friendly, detailed patient guide.
    *   `clinician_summary`: Creates a structured clinical note for the attending doctor.
    *   `save`: Commits the entire final state to the database.
*   **State Management**: Uses a central `AgentState` (TypedDict) that accumulates data through each phase (IntakeData, TriageData, AdminPrepData, etc.).
*   **Flow**: START → intake → triage → protocol_retrieval → admin_prep → clinical_briefing → patient_message → clinician_summary → save → END.

## 4. 🔄 Workflow / Execution Flow
1.  **Trigger**: User submits a "Generate Instructions" request via the Dashboard (containing patient name, procedure, and time).
2.  **Phase I (Intake & Triage)**: The agent normalizes the patient's chief complaint and checks for "Emergency" status. If red flags are found, they are highlighted in the final trace.
3.  **Phase II (Admin Prep)**: The system fetches medical rules (e.g., "8-hour fasting for surgery"). It calculates specific time-relative instructions (e.g., "Stop eating at 10:00 PM").
4.  **Phase III (Output Generation)**: The agent uses the combined context to build a detailed clinical brief for the doctor and a warm, supportive guide for the patient.
5.  **Decision Points**: The system automatically switches to **Template Fallback Mode** if the LLM (OpenAI) is unavailable or if the API key is missing.

## 5. 🗂️ Tech Stack
*   **Agent Framework**: LangGraph (Orchestration) & LangChain (Utility).
*   **LLM Usage**: OpenAI (primary) with support for context-aware prompt engineering.
*   **Web Framework**: Flask (Python) with Jinja2 templating.
*   **Database**: SQLite (Local persistence via `storage.py`).
*   **Testing**: Pytest & Hypothesis (Property-based testing for rule correctness).
*   **Styling**: Modern Healthcare UI (Sleek CSS/JS with medical-grade aesthetics).

## 6. 📊 Data Handling
*   **Inputs**: Patient demographics, appointment type/category, procedure description, clinician name, and schedule.
*   **Flow**: Data is validated via `validation.py`, processed by the `RulesEngine`, and then passed to the LLM as a "Context Dictionary" to prevent hallucination.
*   **Guardrails**: Medical rules are deterministic (hardcoded in `RulesEngine`) and override AI suggestions to ensure safety.

## 7. 🚧 Current Limitations
*   **PII/HIPAA**: Not currently HIPAA compliant (no encryption at rest, no Auth/MFA).
*   **Live EHR Integration**: Uses a mock/simulated EHR context; not yet connected to Epic/Cerner APIs.
*   **Cycle Dependency**: Currently a linear flow; does not support "loops" where the agent asks the patient clarifying questions mid-flow.
*   **Local Execution**: Only supports SQLite; not yet scaled for cloud-native distributed databases.

## 8. 🚀 Suggested Next Steps
*   **Multi-Agent Q&A**: Implement a "Patient Chatbot" node that allows patients to ask follow-up questions about their specific prep guide.
*   **EHR Connector**: Build a service layer to pull real medical history and allergy data from HL7/FHIR interfaces.
*   **Scheduling Node**: Add a "reschedule" logic branch where the agent can suggest alternative slots if prep criteria aren't met.
*   **Security Layer**: Integrate Flask-Login and SQLCipher for HIPAA-ready data protection.

## 9. ⚠️ Constraints & Rules
*   **Safety Over AI**: NEVER allow the LLM to invent fasting hours; always use values from the `RulesEngine`.
*   **Tone Constraint**: Use warm, professional coordinator tone — strictly avoid robotic or overly alarmist language.
*   **Output Format**: Patient-facing messages must be in **Plain English** (No markdown syntax) to ensure readability on older device screens.
