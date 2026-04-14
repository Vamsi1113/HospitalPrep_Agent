"""
Context-Aware Agent Prompts.

All prompts accept a full patient context dict and build personalized,
procedure-specific instructions. No static templates — everything is
dynamically constructed from the patient's actual data.

Output format rules enforced in every prompt:
  - Plain English, NO markdown syntax (no **, no #, no *, no backticks)
  - Section headings on their own line, ending with a colon
  - Bullet items prefixed with a dash (-)
  - Warm, professional, direct medical-coordinator tone
"""

from typing import Tuple


# ──────────────────────────────────────────────────────────────────────────────
# PATIENT PREPARATION GUIDE
# ──────────────────────────────────────────────────────────────────────────────

def build_prep_prompt(context: dict) -> Tuple[str, str]:
    """
    Build a HIGH-DETAIL, personalized appointment preparation prompt.
    """
    patient_name   = context.get("patient_name", "the patient")
    procedure      = context.get("procedure", "General Consultation")
    apt_type       = context.get("appointment_type", "Consultation")
    clinician      = context.get("clinician_name", "your doctor")
    apt_dt         = context.get("appointment_datetime", "your scheduled time")
    complaint      = context.get("chief_complaint", "")
    symptoms       = context.get("symptoms", "")
    medications    = context.get("current_medications", [])
    allergies      = context.get("allergies", [])
    conditions     = context.get("prior_conditions", [])
    age_group      = context.get("age_group", "")

    meds_str       = ", ".join(medications) if medications else "None reported"
    allergy_str    = ", ".join(allergies)   if allergies  else "None reported"
    conditions_str = ", ".join(conditions)  if conditions else "None reported"
    
    hospitals = context.get("hospital_data", {}).get("suggested_hospitals", [])
    hospitals_str = "\n".join([f"- {h['name']} ({h['rating']} stars) - {h['location']} - {h['specialty']}" for h in hospitals]) if hospitals else "No specific suggestions found."

    prep_hints = _get_procedure_hints(procedure, apt_type)

    system_prompt = """You are an expert Senior Healthcare Coordinator.
Your goal is to provide an exceptionally thorough, personalized, and supportive preparation guide.

STRICT OUTPUT RULES:
- DEPTH: Be detailed. Instead of "fast", explain "Do not eat or drink anything, including water or gum, for 8 hours before because...".
- CHRONOLOGY: Organize instructions by timeline (Day Before, Night Before, Morning of).
- FORMAT: NO markdown (no **, no #, no *, no `). Use section headings on their own line ending with a colon. Use a dash (-) for bullets.
- TONE: Professional, warm, and highly focused on patient safety and comfort.
- NO BOILERPLATE: Every sentence should feel like it was written for THIS patient and THIS procedure.
- INTEGRATION: Mention their specific medications or allergies if they impact the procedure (e.g., "Since you take Aspirin, please note...").
- Write in second person ("You will...", "Please arrive...")."""

    user_prompt = f"""Generate a COMPREHENSIVE preparation guide for:

PATIENT: {patient_name} ({age_group or "Adult"})
REASON: {complaint or "Routine review"} / {symptoms or "Not specified"}
MEDS: {meds_str} | ALLERGIES: {allergy_str} | HISTORY: {conditions_str}

APPOINTMENT:
- Type: {apt_type}
- Procedure: {procedure}
- Clinician: {clinician}
- Schedule: {apt_dt}

TOP-RATED HOSPITALS FOR YOUR PROCEDURE:
{hospitals_str}

PROCEDURAL PROTOCOLS TO INCLUDE:
{prep_hints}

REQUIRED SECTIONS (Use exact headings):

Appointment Overview:
(Provide a warm introduction and explain specifically why this appointment is happening in the context of their symptoms: {complaint}. Mention the hospital suggestions if relevant.)

What to Expect During Your Visit:
(Walk through the procedure step-by-step. What will happen first? How long will it take? Will it be uncomfortable? Be detailed.)

Preparation Instructions:
(Detailed timeline: 24 hours before, Night before, Morning of. Be specific about diet, liquids, and activities.)

Medication Instructions:
(Given their medications: {meds_str}, provide specific guidance on what to continue or hold, and how to take them the morning of. If they have allergies: {allergy_str}, mention how the clinic handles this.)

What to Bring:
(Beyond just ID. Mention specific records, comfortable clothes for {procedure}, or items for the waiting room.)

Arrival and Check-In:
(Specific timing and what happens at the front desk.)

Important Warnings:
(Red flags specific to {procedure} and their {conditions_str}.)

Questions and Contact:
(Closing encouragement.)

WRITE NATURALLY. NO MARKDOWN. BE THOROUGH."""

    return system_prompt, user_prompt


def _get_procedure_hints(procedure: str, apt_type: str) -> str:
    """Enhanced procedure protocols for high-detail output."""
    proc_lower = procedure.lower()
    type_lower = apt_type.lower()

    if any(w in proc_lower for w in ["colonoscopy", "lower gi", "sigmoidoscopy"]):
        return (
            "COLONOSCOPY PROTOCOL: High-depth requirements. "
            "- 3 Days Before: Low-fiber diet (avoid seeds, nuts, raw veg). "
            "- 1 Day Before: Clear liquid diet ONLY (broth, apple juice, plain gelatin - NO red/purple). "
            "- Prep solution: Split-dose logic (half at 6pm, half 6 hours before procedure). "
            "- Day of: NPO (nothing by mouth) 4 hours before. "
            "- Sedation: Patient CANNOT drive or work for 24 hours. A responsible adult MUST stay at the clinic."
        )

    if any(w in proc_lower for w in ["endoscopy", "upper gi", "egd", "gastroscopy"]):
        return (
            "ENDOSCOPY PROTOCOL: "
            "- NPO after midnight (including water and gum). "
            "- Hold antacids 24 hours before if specified. "
            "- Arrange driver for sedation. "
            "- Total time in clinic approx 2-3 hours."
        )

    if any(w in proc_lower + type_lower for w in ["surgery", "surgical", "operation", "procedure under anesthesia"]):
        return (
            "SURGERY PROTOCOL: "
            "- Scrub with Hibiclens/antibacterial soap the night before and morning of. "
            "- Clean sheets and pajamas the night before. "
            "- NPO after midnight. Zero liquids (including water) 4 hours before. "
            "- No jewelry, makeup, contact lenses, or dentures. "
            "- Hold blood thinners (Aspirin/Warfarin) 7 days prior - VERIFY with surgeon. "
            "- Wear loose-fitting, button-down clothing."
        )

    if "mri" in proc_lower:
        return (
            "MRI PROTOCOL: "
            "- Metal screening: pacemaker, stents, shunts, or metal shavings in eyes must be disclosed. "
            "- No jewelry/piercings. Wear athletic clothes (no metal zippers/snaps). "
            "- If claustrophobic: contact doctor for oral sedative 1 hour before arrival. "
            "- If contrast used: drink 64oz water day before and day after."
        )

    if any(w in proc_lower for w in ["ct scan", "ct with contrast", "computed tomography"]):
        return (
            "CT SCAN PROTOCOL: "
            "- Fast 4 hours before (water allowed). "
            "- If oral contrast: arrive 60-90 mins early to drink contrast media. "
            "- Lab work: Creatinine/BUN req within 30 days if contrast-ordered. "
            "- Discontinue Metformin for 48 hours following scan if contrast used."
        )

    if any(w in proc_lower + type_lower for w in ["blood", "lab", "laboratory", "blood test", "bloodwork"]):
        return (
            "LAB PROTOCOL: "
            "- Fasting: 8-12 hours required (water only, no coffee/tea). "
            "- Hydration: Drink 16oz water 1 hour before to simplify draw. "
            "- Medications: Take regular medications unless specifically told to hold for fasting panel."
        )

    return (
        f"This is a {procedure} appointment. Provide a dense, step-by-step guide. "
        "Include arrival times, specific items to bring, and physical preparation logic."
    )


# ──────────────────────────────────────────────────────────────────────────────
# CLINICIAN BRIEFING
# ──────────────────────────────────────────────────────────────────────────────

def build_clinical_prompt(context: dict) -> Tuple[str, str]:
    """Build a structured clinical pre-visit briefing for the physician."""

    patient_name = context.get("patient_name", "Patient")
    procedure    = context.get("procedure", "")
    apt_type     = context.get("appointment_type", "")
    complaint    = context.get("chief_complaint", "")
    symptoms     = context.get("symptoms", "")
    medications  = context.get("current_medications", [])
    allergies    = context.get("allergies", [])
    conditions   = context.get("prior_conditions", [])
    age_group    = context.get("age_group", "")

    meds_str       = ", ".join(medications) if medications else "None"
    allergy_str    = ", ".join(allergies)   if allergies  else "NKDA"
    conditions_str = ", ".join(conditions)  if conditions else "None reported"

    system_prompt = (
        "You are a clinical documentation assistant. Generate a concise, structured "
        "pre-visit briefing for the attending physician. Use clinical language. "
        "No markdown — plain text with labeled sections."
    )

    user_prompt = f"""Create a pre-visit clinical summary note.

Patient: {patient_name} | Age Group: {age_group or "Unknown"}
Procedure: {procedure} | Visit Type: {apt_type}

Chief Complaint: {complaint or "Not provided"}
Symptom Detail: {symptoms or "Not elaborated"}

Current Medications: {meds_str}
Allergies: {allergy_str}
Prior Conditions: {conditions_str}

Write a structured note with these sections:
Chief Complaint:
Clinical Context:
Medication and Allergy Review:
Pre-Procedure Considerations:
Triage Assessment:
Prep Status:

Use plain clinical language. No markdown. Keep each section concise."""

    return system_prompt, user_prompt


# ──────────────────────────────────────────────────────────────────────────────
# CHAT Q&A
# ──────────────────────────────────────────────────────────────────────────────

def build_chat_prompt(
    context: dict,
    question: str,
    chat_history: list
) -> Tuple[str, str]:
    """
    Build a context-aware chat prompt that injects full patient context
    and recent conversation history so responses are personalized.
    """
    patient_name = context.get("patient_name", "the patient")
    procedure    = context.get("procedure", "their appointment")
    apt_type     = context.get("appointment_type", "medical appointment")
    medications  = context.get("current_medications", [])
    allergies    = context.get("allergies", [])
    conditions   = context.get("prior_conditions", [])
    complaint    = context.get("chief_complaint", "")
    prep_done    = bool(context.get("prep_output"))

    meds_str  = ", ".join(medications) if medications else "None"
    allergy_str = ", ".join(allergies) if allergies  else "None"

    # Recent conversation (last 6 messages = 3 exchanges)
    recent = chat_history[-6:] if chat_history else []
    history_str = ""
    for msg in recent:
        role = "Patient" if msg.get("role") == "patient" else "Assistant"
        history_str += f"{role}: {msg.get('content', '')}\n"

    system_prompt = f"""You are a knowledgeable, empathetic medical appointment assistant helping {patient_name} prepare for their {procedure}.

Patient Context:
- Procedure: {procedure} ({apt_type})
- Chief Complaint: {complaint or 'Not specified'}
- Current Medications: {meds_str}
- Allergies: {allergy_str}
- Prior Conditions: {', '.join(conditions) if conditions else 'None'}
- Preparation guide has been provided: {'Yes' if prep_done else 'Not yet'}

Response Rules:
- Answer clearly and specifically, always referencing the patient's procedure and context.
- Do NOT use any markdown (no **, no ##, no asterisks, no backticks).
- Write in plain conversational prose with short paragraphs.
- Be warm but professional — like a healthcare coordinator on the phone.
- If the question involves clinical decisions (dosing, diagnosis), advise contacting the clinic or their doctor.
- If you reference their medications or allergies, be accurate to what is listed.
- Keep answers concise and actionable. End with a helpful note if relevant."""

    user_prompt = f"""Recent conversation:
{history_str if history_str else "No previous messages."}

Patient's question: {question}

Answer clearly and helpfully, staying focused on their {procedure} and context. No markdown."""

    return system_prompt, user_prompt


# ──────────────────────────────────────────────────────────────────────────────
# SYMPTOM NORMALIZATION (Phase I — unchanged, used in intake_node)
# ──────────────────────────────────────────────────────────────────────────────

SYMPTOM_NORMALIZATION_PROMPT = """You are a medical intake assistant. Normalize this patient's symptom description into concise clinical terminology.

Rules:
- Convert casual language to clinical terms
- Preserve the patient's meaning
- Do NOT diagnose or add new symptoms
- Return ONLY the normalized term(s), nothing else

Patient's description: {symptom_description}"""

FOLLOW_UP_QUESTIONS_PROMPT = """Based on the chief complaint, generate 2-3 relevant intake follow-up questions.
Return a JSON array only. Example: ["When did this start?", "Rate severity 1-10?"]
Chief complaint: {chief_complaint}
Already known: {known_info}"""

TRIAGE_CLASSIFICATION_PROMPT = """Classify urgency of this patient case. Return JSON only.
Chief complaint: {chief_complaint}
Symptoms: {symptoms}
Age group: {age_group}
Prior conditions: {prior_conditions}

Return: {{"urgency_level": "routine|urgent|emergency", "red_flags": [], "reasoning": "brief"}}"""
