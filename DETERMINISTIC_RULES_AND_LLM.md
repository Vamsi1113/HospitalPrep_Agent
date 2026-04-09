# Deterministic Rules and LLM Configuration

## Question 1: All Hard-Coded Deterministic Rules

Your system has deterministic rules in **TWO locations**:

### Location 1: `services/rules_engine.py` - Core Medical Rules

This is the **primary rules engine** that determines all medical preparation requirements.

#### Rule Categories

##### 1. SURGERY RULES
**Trigger**: `appointment_type == "surgery"` OR `"surgery"` in procedure name

**Rules Applied**:
- ✅ Fasting Required: **YES**
- ⏰ Fasting Hours: **8 hours**
- 🕐 Arrival Time: **60 minutes early**
- 🚗 Requires Responsible Adult: **YES** (cannot drive home)
- 📋 Items to Bring:
  - Photo ID (mandatory for all)
  - Insurance Card (mandatory for all)
  - List of current medications
  - Completed pre-op forms
- ⚠️ Special Warnings:
  - "Do not drive yourself home after surgery"
- 📂 Category: **"surgery"**

**File**: `services/rules_engine.py`, lines 48-63

---

##### 2. ENDOSCOPY/COLONOSCOPY RULES
**Trigger**: `"colonoscopy"` in procedure OR `"endoscopy"` in procedure

**Rules Applied**:
- ✅ Fasting Required: **YES**
- ⏰ Fasting Hours: **12 hours** (longest fasting period)
- 🕐 Arrival Time: **30 minutes early**
- 🚗 Requires Responsible Adult: **YES**
- 📋 Items to Bring:
  - Photo ID (mandatory for all)
  - Insurance Card (mandatory for all)
  - Prep kit instructions
- ⚠️ Special Warnings:
  - "Complete bowel prep as instructed"
- 📂 Category: **"endoscopy"**

**File**: `services/rules_engine.py`, lines 65-76

---

##### 3. IMAGING RULES
**Trigger**: `appointment_type == "imaging"` OR procedure contains `"mri"`, `"ct"`, `"x-ray"`, or `"ultrasound"`

**Base Rules**:
- ✅ Fasting Required: **NO** (unless contrast)
- ⏰ Fasting Hours: **0 hours**
- 🕐 Arrival Time: **15 minutes early**
- 🚗 Requires Responsible Adult: **NO**
- 📋 Items to Bring:
  - Photo ID (mandatory for all)
  - Insurance Card (mandatory for all)
- 📂 Category: **"imaging"**

**CONTRAST SUB-RULE**:
If `"contrast"` in procedure:
- ✅ Fasting Required: **YES**
- ⏰ Fasting Hours: **4 hours**
- ⚠️ Special Warnings:
  - "Inform technician of any allergies"

**File**: `services/rules_engine.py`, lines 78-91

---

##### 4. LAB WORK RULES
**Trigger**: `"blood"` in procedure OR `"lab"` in procedure

**Base Rules**:
- ✅ Fasting Required: **NO** (unless "fasting" keyword)
- ⏰ Fasting Hours: **0 hours**
- 🕐 Arrival Time: **10 minutes early** (shortest arrival time)
- 🚗 Requires Responsible Adult: **NO**
- 📋 Items to Bring:
  - Photo ID (mandatory for all)
  - Insurance Card (mandatory for all)
- 📂 Category: **"lab"**

**FASTING SUB-RULE**:
If `"fasting"` in procedure:
- ✅ Fasting Required: **YES**
- ⏰ Fasting Hours: **8 hours**

**File**: `services/rules_engine.py`, lines 93-100

---

##### 5. DEFAULT CONSULTATION RULES
**Trigger**: None of the above match

**Rules Applied**:
- ✅ Fasting Required: **NO**
- ⏰ Fasting Hours: **0 hours**
- 🕐 Arrival Time: **15 minutes early**
- 🚗 Requires Responsible Adult: **NO**
- 📋 Items to Bring:
  - Photo ID (mandatory for all)
  - Insurance Card (mandatory for all)
  - List of current medications
- 📂 Category: **"consultation"**

**File**: `services/rules_engine.py`, lines 102-104

---

##### 6. UNIVERSAL RULES (Apply to ALL appointments)

**Mandatory Items** (always included):
- Photo ID
- Insurance Card

**Medication Instructions** (default):
- "Take regular medications unless instructed otherwise"

**Fasting Consistency Rule**:
- If `fasting_required == False`, then `fasting_hours` MUST be 0

**File**: `services/rules_engine.py`, lines 38-42, 106-108

---

### Location 2: `services/prep_plan_builder.py` - Detailed Content Rules

This service generates the **detailed text content** for each section based on the rules from the rules engine.

#### Fasting Plan Rules (`_build_fasting_plan`)

**Clear Fluids Rule**:
- If fasting ≥ 8 hours:
  - Clear fluids allowed until **2 hours before appointment**
  - Examples: water, clear juice, black coffee/tea
  - After 2-hour cutoff: **nothing by mouth including water**
- If fasting < 8 hours:
  - No food or drink after cutoff time

**Cutoff Time Calculation**:
- Fasting start time = appointment_datetime - fasting_hours
- Clear fluids cutoff = appointment_datetime - 2 hours

**File**: `services/prep_plan_builder.py`, lines 52-73

---

#### Diet Guidance Rules (`_build_diet_guidance`)

**Endoscopy/Colonoscopy Diet**:
- **3 days before**:
  - Avoid: seeds, nuts, popcorn, raw vegetables
  - Stick to low-fiber foods
- **1 day before**:
  - Clear liquids only (broth, clear juice, gelatin, popsicles)
  - No red or purple colored liquids
  - Complete bowel prep as instructed

**Surgery Diet** (if fasting ≥ 8 hours):
- **Day before surgery**:
  - Eat light, easily digestible meals
  - Avoid heavy, fatty, or spicy foods
  - Stay well hydrated until fasting begins
  - Avoid alcohol

**Other Categories**: No special diet guidance

**File**: `services/prep_plan_builder.py`, lines 75-99

---

#### Medication Instructions Rules (`_build_medication_instructions`)

**Universal Instructions**:
- Bring complete list of all medications
- Include prescription, OTC, vitamins, supplements
- Note any medication allergies

**Surgery/Endoscopy Additional Instructions**:
- Blood thinners: Clinician will provide specific instructions
- Diabetes medications: May need adjustment on procedure day
- Blood pressure medications: Usually taken with small sip of water
- Warning: Contact clinician BEFORE appointment with questions

**File**: `services/prep_plan_builder.py`, lines 101-120

---

#### Arrival Instructions Rules (`_build_arrival_instructions`)

**Arrival Time Calculation**:
- Arrival time = appointment_datetime - arrival_minutes_early

**Universal Steps**:
- Check in at reception desk
- Complete any remaining paperwork
- Verify insurance information

**Surgery/Endoscopy Additional Steps**:
- Change into gown if required
- Meet with clinical staff for pre-procedure assessment

**File**: `services/prep_plan_builder.py`, lines 122-141

---

#### Transportation Rules (`_build_transport_instructions`)

**Applies When**: `requires_responsible_adult == True`

**Restrictions** (cannot do):
- Drive yourself home
- Take public transportation alone
- Use ride-sharing services (Uber/Lyft) alone

**Requirements** (must have):
- Responsible adult must drive you home
- They must stay at facility during procedure
- They must be able to assist you at home

**Consequence**: Procedure will be rescheduled if no appropriate transportation

**File**: `services/prep_plan_builder.py`, lines 143-161

---

#### Red Flag Warnings Rules (`_build_red_flag_warnings`)

**Universal Warnings** (all appointments):
- Fever over 101°F (38.3°C)
- Severe or worsening pain
- Difficulty breathing or chest pain
- Signs of infection at any surgical site
- Unusual or severe symptoms
- Any concerns about ability to safely prepare

**Surgery-Specific Warnings**:
- Excessive bleeding or drainage
- Swelling, redness, or warmth at incision site
- Inability to keep down fluids

**Endoscopy-Specific Warnings**:
- Severe abdominal pain or cramping
- Vomiting blood or black stools
- Inability to complete bowel prep

**File**: `services/prep_plan_builder.py`, lines 163-189

---

#### Procedure-Specific Notes Rules (`_build_procedure_notes`)

**Colonoscopy**:
- "Colonoscopy is a safe, effective screening tool. The preparation is often the most challenging part, but it's essential for a successful exam. Stay near a bathroom during prep, and don't hesitate to call if you have concerns."

**MRI**:
- "MRI uses magnetic fields and radio waves - no radiation. Remove all metal objects before the scan. The machine can be loud; earplugs or headphones will be provided. Let the technician know if you feel claustrophobic."

**CT with Contrast**:
- "CT with contrast provides detailed images. You may feel warm or have a metallic taste when contrast is injected - this is normal and passes quickly. Drink plenty of water after the scan to help flush the contrast."

**Surgery**:
- "Your surgical team will review the procedure, risks, and benefits with you. Don't hesitate to ask questions. Follow all pre-op instructions carefully to minimize risks and promote healing."

**File**: `services/prep_plan_builder.py`, lines 191-209

---

## Question 2: Which LLM is Being Used?

### LLM Model: **GPT-3.5-Turbo** (OpenAI)

**Location**: `services/llm_client.py`, line 103

```python
response = self._client.chat.completions.create(
    model="gpt-3.5-turbo",  # <-- HERE
    messages=[...],
    temperature=0.7,
    max_tokens=1000
)
```

### LLM Configuration Details

**Model**: `gpt-3.5-turbo`
**Temperature**: `0.7` (balanced creativity/consistency)
**Max Tokens**: `1000` (limits response length)
**Timeout**: `5 seconds` (prevents hanging)

**File**: `services/llm_client.py`, lines 103-109

---

### How to Configure the LLM

#### 1. Set API Key

The LLM requires an OpenAI API key to function. You configure it via environment variable:

**File**: `.env` (create this file in project root)

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

**Example File**: `.env.example` shows the format

#### 2. Where API Key is Loaded

**File**: `app.py`, lines 18-20

```python
from dotenv import load_dotenv
load_dotenv()
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
```

#### 3. Where LLM Client is Initialized

**File**: `app.py`, lines 28-29

```python
llm_client = LLMClient(api_key=app.config['OPENAI_API_KEY'])
message_builder = MessageBuilder(llm_client)
```

---

### LLM Safety Features

The system has **strict safety controls** to prevent the LLM from inventing medical advice:

#### 1. System Prompt Restrictions

**File**: `services/llm_client.py`, lines 73-84

```python
system_prompt = (
    f"You are a medical office assistant. Rewrite the following "
    f"appointment preparation instructions in a {tone} tone. "
    f"CRITICAL RULES:\n"
    f"- DO NOT add, remove, or modify any medical instructions, requirements, or warnings\n"
    f"- DO NOT invent new medical advice or preparation steps\n"
    f"- ONLY improve the wording, flow, and readability\n"
    f"- Keep all specific times, items, and requirements exactly as stated\n"
    f"- Preserve all safety warnings and important notices\n"
    f"- Maintain the same level of detail and completeness"
)
```

#### 2. Graceful Fallback

If the LLM fails or is unavailable, the system **automatically falls back** to template-based messages:

**File**: `agent/tools.py`, lines 234-253

```python
if llm_client.is_available():
    enhanced = llm_client.rewrite_message(state["draft_message"], tone="friendly")
    if enhanced:
        state["final_message"] = enhanced
        state["llm_used"] = True
    else:
        # LLM failed, use template fallback
        state["final_message"] = state["draft_message"]
        state["llm_used"] = False
else:
    # LLM not available, use template
    state["final_message"] = state["draft_message"]
    state["llm_used"] = False
```

#### 3. LLM is OPTIONAL

The system works **perfectly fine without an LLM**:
- All medical instructions come from deterministic rules
- Template-based messages are clear and complete
- LLM only improves tone/readability, not content

---

### How to Change the LLM Model

If you want to use a different OpenAI model (e.g., GPT-4):

**File**: `services/llm_client.py`, line 103

Change:
```python
model="gpt-3.5-turbo",
```

To:
```python
model="gpt-4",  # or "gpt-4-turbo", "gpt-4o", etc.
```

**Note**: Different models have different costs and capabilities. GPT-4 is more expensive but potentially better at following instructions.

---

### How to Use a Different LLM Provider

If you want to use a different provider (e.g., Anthropic Claude, local LLM):

1. Modify `services/llm_client.py` to use the new provider's SDK
2. Update the `__init__` method to initialize the new client
3. Update the `rewrite_message` method to call the new API
4. Keep the same safety prompts and fallback behavior

---

## Summary

### Deterministic Rules Locations

1. **`services/rules_engine.py`** - Core medical rules (fasting, arrival, items, warnings)
2. **`services/prep_plan_builder.py`** - Detailed content rules (diet plans, medication instructions, red flags)

### LLM Configuration

- **Model**: GPT-3.5-Turbo (OpenAI)
- **Location**: `services/llm_client.py`, line 103
- **API Key**: Set via `.env` file → `OPENAI_API_KEY=sk-...`
- **Purpose**: Optional tone enhancement only (NOT medical content)
- **Safety**: Strict system prompts prevent medical invention
- **Fallback**: Automatic fallback to templates if LLM unavailable

### Key Principle

**ALL medical instructions come from deterministic rules. The LLM ONLY rewrites tone/wording, NEVER invents medical advice.**
