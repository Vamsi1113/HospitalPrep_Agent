"""
Centralized Patient Context Manager.

Maintains a shared, persistent patient context across every agent module:
  intake → scheduling → preparation → chat → recovery

All stages read from and write to this single context object, keyed by
session_id, so the entire system behaves as one connected AI agent.
"""

import threading
from typing import Dict, Any, Optional
from datetime import datetime


class PatientContextManager:
    """
    Thread-safe in-memory patient context store.

    Each session (patient visit) is keyed by a session_id string.
    All agent modules update and read from the same context, enabling
    shared reasoning and personalization across the full workflow.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Core CRUD                                                            #
    # ------------------------------------------------------------------ #

    def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return full context for a session, or None if not found."""
        with self._lock:
            return self._store.get(session_id)

    def set_context(self, session_id: str, context: Dict[str, Any]) -> None:
        """Overwrite the full context for a session."""
        with self._lock:
            context["last_updated"] = datetime.now().isoformat()
            self._store[session_id] = context

    def update_context(self, session_id: str, partial: Dict[str, Any]) -> None:
        """Merge partial dict into existing context."""
        with self._lock:
            if session_id not in self._store:
                self._store[session_id] = {}
            self._store[session_id].update(partial)
            self._store[session_id]["last_updated"] = datetime.now().isoformat()

    def append_chat(self, session_id: str, role: str, content: str) -> None:
        """Append a message to the chat history inside the context."""
        with self._lock:
            ctx = self._store.setdefault(session_id, {})
            history = ctx.setdefault("chat_history", [])
            history.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            })
            ctx["last_updated"] = datetime.now().isoformat()

    # ------------------------------------------------------------------ #
    # Factory                                                              #
    # ------------------------------------------------------------------ #

    def build_from_intake(
        self, session_id: str, intake_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build and store the initial context from raw patient intake.

        Called once at the start of the /generate route so every
        downstream module immediately has full patient information.
        """
        context = {
            # Identity
            "session_id":          session_id,
            "patient_name":        intake_data.get("patient_name", "Patient"),
            "age_group":           intake_data.get("age_group", ""),
            # Clinical
            "chief_complaint":     intake_data.get("chief_complaint", ""),
            "symptoms":            intake_data.get("symptoms_description", ""),
            "current_medications": intake_data.get("current_medications", []),
            "allergies":           intake_data.get("allergies", []),
            "prior_conditions":    intake_data.get("prior_conditions", []),
            # Appointment
            "appointment_type":    intake_data.get("appointment_type", ""),
            "procedure":           intake_data.get("procedure", ""),
            "clinician_name":      intake_data.get("clinician_name", "your doctor"),
            "appointment_datetime":intake_data.get("appointment_datetime", ""),
            "channel_preference":  intake_data.get("channel_preference", ""),
            # Outputs (filled in later by each module)
            "prep_output":         None,
            "schedule_info":       None,
            "recovery_plan":       None,
            "chat_history":        [],
            # Metadata
            "created_at":          datetime.now().isoformat(),
            "last_updated":        datetime.now().isoformat(),
        }
        self.set_context(session_id, context)
        return context

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def format_for_prompt(self, session_id: str) -> str:
        """
        Return a compact, plain-text summary of the patient context
        suitable for injecting into any LLM prompt.
        """
        ctx = self.get_context(session_id)
        if not ctx:
            return "No patient context available."

        meds = ", ".join(ctx.get("current_medications", [])) or "None"
        allergies = ", ".join(ctx.get("allergies", [])) or "None"
        conditions = ", ".join(ctx.get("prior_conditions", [])) or "None"

        return (
            f"Patient: {ctx.get('patient_name')} ({ctx.get('age_group', 'age unknown')})\n"
            f"Procedure: {ctx.get('procedure')} ({ctx.get('appointment_type')})\n"
            f"Clinician: {ctx.get('clinician_name')}\n"
            f"Appointment: {ctx.get('appointment_datetime')}\n"
            f"Chief Complaint: {ctx.get('chief_complaint')}\n"
            f"Symptoms: {ctx.get('symptoms') or 'Not elaborated'}\n"
            f"Medications: {meds}\n"
            f"Allergies: {allergies}\n"
            f"Prior Conditions: {conditions}"
        )

    def list_sessions(self) -> list:
        """Return all active session IDs (for debugging)."""
        with self._lock:
            return list(self._store.keys())


# ------------------------------------------------------------------ #
# Singleton — imported everywhere as a shared instance               #
# ------------------------------------------------------------------ #

_context_manager = PatientContextManager()


def get_context_manager() -> PatientContextManager:
    """Return the application-wide singleton context manager."""
    return _context_manager
