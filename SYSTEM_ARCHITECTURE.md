# Appointment Prep AI Agent - System Architecture

## Overview

This is a **LangGraph-based AI agent system** that generates personalized appointment preparation instructions for medical appointments. The system uses a **deterministic rules engine** for all medical instructions and optionally enhances the output with an LLM for friendly tone.

## Core Philosophy

- **Safety-First**: All medical instructions come from deterministic rules, never AI invention
- **Agent-Based**: Uses LangGraph state machine for orchestration, not simple function pipelines
- **Explainable**: Every decision is tracked and visible to users
- **Local-First**: Runs entirely locally with optional OpenAI API for tone enhancement
- **Single-Page Interface**: Unified agent workspace, not a traditional multi-page website

---

## System Components

### 1. Flask Application (`app.py`)

**Purpose**: Web server and HTTP API layer

**Responsibilities**:
- Serves the single-page agent workspace UI
- Provides REST endpoints for agent execution, history, and sample data
- Initializes all services on startup
- Handles errors and returns JSON responses

**Key Routes**:
- `GET /` - Serves agent workspace HTML
- `POST /generate` - Executes agent with appointment data
- `GET /history` - Retrieves past generated plans
- `GET /load-sample/<id>` - Loads sample appointment data

**Services Initialized**:
```python
rules_engine = RulesEngine()
llm_client = LLMClient(api_key=...)
message_builder = MessageBuilder(llm_client)
prep_plan_builder = PrepPlanBuilder()
storage = StorageService()
```

---

### 2. LangGraph Agent System (`agent/`)

This is the **core orchestration layer** that implements the AI agent using LangGraph.

#### 2.1 Agent State (`agent/state.py`)

**Purpose**: Defines the state structure that flows through the agent graph

**Key Components**:

```python
class AgentState(TypedDict):
    # Input
    input_data: Dict[str, Any]
    
    # Processing stages
    validated_data: Optional[Dict[str, Any]]
    rules_output: Optional[PrepRules]
    prep_sections: Optional[PrepPlanSections]
    
    # Output
    draft_message: Optional[str]
    final_message: Optional[str]
    preview: Optional[str]
    rules_explanation: Optional[List[Dict]]
    
    # Metadata
    errors: List[str]
    reasoning_trace: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    llm_used: bool
    saved_record_id: Optional[int]
```

**PrepPlanSections Structure**:
```python
class PrepPlanSections(TypedDict):
    appointment_summary: str
    fasting_plan: Optional[str]
    diet_guidance: Optional[str]
    medication_instructions: str
    items_to_bring: List[str]
    arrival_instructions: str
    transport_instructions: Optional[str]
    red_flag_warnings: List[str]
    procedure_specific_notes: Optional[str]
    closing_note: str
```

**Why This Matters**: The state is the "memory" of the agent. As it flows through each node, it accumulates information and tracks the agent's reasoning process.

#### 2.2 Agent Tools (`agent/tools.py`)

**Purpose**: Wraps services as LangGraph tools (nodes in the graph)

Each tool:
1. Takes the current state
2. Performs an operation (validation, rules, message building, etc.)
3. Updates the state
4. Logs reasoning steps
5. Returns updated state

**Available Tools**:

1. **`validate_input_tool`**
   - Validates appointment data (required fields, formats)
   - Updates `validated_data` or adds errors
   - Logs validation results to reasoning trace

2. **`apply_rules_tool`**
   - Applies deterministic medical preparation rules
   - Updates `rules_output` with PrepRules object
   - Logs rule decisions (fasting hours, arrival time, etc.)

3. **`build_prep_plan_tool`**
   - Generates structured preparation sections
   - Updates `prep_sections` with comprehensive instructions
   - Logs section count

4. **`build_message_tool`**
   - Creates template-based message from rules
   - Updates `draft_message`, `preview`, `rules_explanation`
   - Logs message length and rule count

5. **`enhance_message_tool`**
   - Optionally rewrites message with LLM for friendly tone
   - Updates `final_message` and `llm_used` flag
   - Falls back to template if LLM unavailable
   - Logs enhancement status

6. **`save_output_tool`**
   - Persists message to SQLite database
   - Updates `saved_record_id`
   - Logs database ID

**Reasoning Trace**: Each tool appends steps to `state["metadata"]["steps"]` with:
- Step name
- Timestamp
- Description
- Relevant data (e.g., fasting hours, message length)

#### 2.3 Agent Graph (`agent/graph.py`)

**Purpose**: Defines the LangGraph workflow and orchestrates execution

**Graph Structure**:

```
START
  ↓
validate_input
  ↓
[Conditional: errors?]
  ↓ (no errors)
apply_rules
  ↓
build_prep_plan
  ↓
build_message
  ↓
enhance_message
  ↓
save_output
  ↓
END
```

**How LangGraph is Used**:

1. **StateGraph Creation**:
   ```python
   workflow = StateGraph(AgentState)
   ```
   Creates a graph where state flows through nodes

2. **Node Registration**:
   ```python
   workflow.add_node("validate_input", lambda state: validate_input_tool(state))
   workflow.add_node("apply_rules", lambda state: apply_rules_tool(state, rules_engine))
   # ... more nodes
   ```

3. **Edge Definition**:
   ```python
   workflow.add_edge("apply_rules", "build_prep_plan")
   workflow.add_edge("build_prep_plan", "build_message")
   # ... more edges
   ```

4. **Conditional Logic**:
   ```python
   def should_continue_after_validation(state: AgentState) -> str:
       if state["errors"]:
           return END
       return "apply_rules"
   
   workflow.add_conditional_edges(
       "validate_input",
       should_continue_after_validation,
       {"apply_rules": "apply_rules", END: END}
   )
   ```

5. **Graph Compilation**:
   ```python
   graph = workflow.compile()
   ```

6. **Execution**:
   ```python
   final_state = graph.invoke(initial_state)
   ```

**Why LangGraph?**:
- **State Management**: Automatic state passing between nodes
- **Conditional Routing**: Can skip nodes based on state (e.g., skip if validation fails)
- **Explainability**: Clear graph structure shows agent's decision flow
- **Extensibility**: Easy to add new nodes or modify workflow
- **Error Handling**: Each node can update errors without breaking the flow

---

### 3. Services Layer (`services/`)

These are the **business logic components** that the agent tools wrap.

#### 3.1 Validation Service (`services/validation.py`)

**Purpose**: Validates appointment data

**Key Function**:
```python
validate_appointment_data(data: Dict) -> Tuple[bool, List[str]]
```

**Checks**:
- Required fields present
- Field formats (datetime, string lengths)
- Valid enum values (appointment type, channel)

#### 3.2 Rules Engine (`services/rules_engine.py`)

**Purpose**: Deterministic medical preparation rules

**Key Function**:
```python
apply_rules(appointment_type: str, procedure: str) -> PrepRules
```

**Rules Applied**:
- Surgery: 8hr fasting, 60min early arrival, requires ride home
- Endoscopy/Colonoscopy: 12hr fasting, 30min early, requires ride home
- Imaging with contrast: 4hr fasting, 15min early
- Lab work (fasting): 8hr fasting, 10min early
- Default consultation: No fasting, 15min early

**Output**: `PrepRules` object with:
- `fasting_required`, `fasting_hours`
- `items_to_bring` (always includes ID and insurance)
- `arrival_minutes_early`
- `medication_instructions`
- `requires_responsible_adult`
- `special_warnings`
- `category`

#### 3.3 Prep Plan Builder (`services/prep_plan_builder.py`)

**Purpose**: Generates structured preparation sections

**Key Function**:
```python
build_prep_sections(appointment_data: Dict, rules: PrepRules) -> Dict
```

**Sections Generated**:
1. **Appointment Summary**: Patient, procedure, date/time, clinician
2. **Fasting Plan**: Cutoff times, clear fluids guidance
3. **Diet Guidance**: Pre-procedure diet restrictions (for endoscopy/surgery)
4. **Medication Instructions**: What to take/hold, bring medication list
5. **Items to Bring**: ID, insurance, medications, procedure-specific items
6. **Arrival Instructions**: When to arrive, what to expect
7. **Transport Instructions**: Ride home requirements (if sedation)
8. **Red Flag Warnings**: When to call clinic (fever, pain, etc.)
9. **Procedure-Specific Notes**: Helpful context about the procedure
10. **Closing Note**: Contact info and general guidance

**Smart Features**:
- Calculates exact cutoff times based on appointment datetime
- Includes procedure-specific warnings (e.g., bowel prep for colonoscopy)
- Conditional sections (only shows fasting if required)

#### 3.4 Message Builder (`services/message_builder.py`)

**Purpose**: Creates template-based messages

**Key Functions**:
- `build_template_message()`: Full text message from rules
- `build_preview()`: Short summary for UI
- `format_rules_explanation()`: Human-readable rule explanations

#### 3.5 LLM Client (`services/llm_client.py`)

**Purpose**: Optional OpenAI integration for tone enhancement

**Key Function**:
```python
rewrite_message(message: str, tone: str) -> Optional[str]
```

**Safety**:
- Only rewrites existing content, doesn't add medical facts
- Graceful fallback if API unavailable
- System prompt enforces "no medical invention" rule

#### 3.6 Storage Service (`services/storage.py`)

**Purpose**: SQLite database persistence

**Key Functions**:
- `save_message()`: Stores generated prep plan
- `get_history()`: Retrieves recent plans
- `init_db()`: Creates database schema

**Schema**:
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    patient_name TEXT,
    appointment_type TEXT,
    procedure TEXT,
    clinician_name TEXT,
    appointment_datetime TEXT,
    generated_text TEXT,
    rules_used TEXT,
    created_at TIMESTAMP
)
```

---

### 4. User Interface (`templates/`, `static/`)

#### 4.1 Agent Workspace (`templates/agent_workspace.html`)

**Purpose**: Single-page AI agent interface

**Layout**: 3-panel design

```
┌─────────────────────────────────────────────────────┐
│              🤖 Appointment Prep AI Agent            │
├──────────────┬──────────────────────┬───────────────┤
│              │                      │               │
│   INPUT      │      RESPONSE        │   REASONING   │
│   PANEL      │      PANEL           │   PANEL       │
│              │                      │               │
│ - Form       │ - Welcome state      │ - Agent trace │
│ - Fields     │ - Error state        │ - History     │
│ - Samples    │ - Success state      │               │
│              │   (prep sections)    │               │
│              │                      │               │
└──────────────┴──────────────────────┴───────────────┘
```

**States**:
1. **Welcome State**: Initial greeting with feature list
2. **Error State**: Validation errors with clear messages
3. **Success State**: Structured prep plan with all sections

#### 4.2 JavaScript (`static/js/agent_workspace.js`)

**Purpose**: Handles form submission and UI updates

**Key Functions**:

1. **`handleFormSubmit()`**
   - Collects form data
   - Calls `/generate` API
   - Shows loading spinner
   - Renders response or errors

2. **`renderStructuredSections()`**
   - Populates each prep section
   - Shows/hides conditional sections (fasting, diet, transport)
   - Formats lists and text

3. **`updateReasoningTrace()`**
   - Displays agent's step-by-step reasoning
   - Shows timestamps and descriptions

4. **`loadHistory()`**
   - Fetches recent plans from `/history`
   - Displays in right panel

5. **`handleCopy()` / `handlePrint()`**
   - Copy prep plan to clipboard
   - Print-friendly format

#### 4.3 CSS (`static/css/agent_workspace.css`)

**Purpose**: Styling for agent workspace

**Key Features**:
- 3-column grid layout
- Gradient header
- Card-based sections with icons
- Color-coded sections (summary, warnings, closing)
- Responsive design
- Smooth animations

---

## Agent Reasoning Panel

### Purpose

The **Agent Reasoning** panel (right side of UI) provides **explainability** and **transparency** into how the agent makes decisions.

### What It Shows

Each step the agent takes is logged with:
- **Step name**: e.g., "validate_input", "apply_rules", "build_prep_plan"
- **Timestamp**: When the step occurred
- **Description**: What happened in that step
- **Relevant data**: Key decisions made (e.g., "fasting_required: true, fasting_hours: 8")

### Example Trace

```
┌─────────────────────────────────────────┐
│ 🧠 Agent Reasoning                      │
├─────────────────────────────────────────┤
│ validate_input                          │
│ Validating appointment data             │
│ 2:30:15 PM                              │
├─────────────────────────────────────────┤
│ validate_input_success                  │
│ All fields validated successfully       │
│ 2:30:15 PM                              │
├─────────────────────────────────────────┤
│ apply_rules                             │
│ Applying deterministic preparation rules│
│ 2:30:15 PM                              │
├─────────────────────────────────────────┤
│ apply_rules_success                     │
│ category: surgery                       │
│ fasting_required: true                  │
│ fasting_hours: 8                        │
│ arrival_minutes: 60                     │
│ 2:30:16 PM                              │
├─────────────────────────────────────────┤
│ build_prep_plan                         │
│ Building structured preparation plan    │
│ 2:30:16 PM                              │
├─────────────────────────────────────────┤
│ build_prep_plan_success                 │
│ sections_count: 10                      │
│ 2:30:16 PM                              │
└─────────────────────────────────────────┘
```

### Why This Matters

1. **Trust**: Users can see exactly how the agent arrived at its recommendations
2. **Debugging**: Developers can trace issues through the workflow
3. **Compliance**: Medical systems need audit trails
4. **Education**: Users learn what factors influence prep instructions

---

## Recent Plans Panel

### Purpose

The **Recent Plans** panel (bottom right of UI) shows **history** of previously generated preparation plans.

### What It Shows

- Patient name and procedure
- Timestamp of generation
- Clickable items (future: could reload that plan)

### Example

```
┌─────────────────────────────────────────┐
│ 📚 Recent Plans                         │
├─────────────────────────────────────────┤
│ John Smith - Colonoscopy                │
│ 2:30 PM, April 8, 2026                  │
├─────────────────────────────────────────┤
│ Jane Doe - MRI with contrast            │
│ 1:15 PM, April 8, 2026                  │
├─────────────────────────────────────────┤
│ Bob Johnson - Fasting blood work        │
│ 11:45 AM, April 8, 2026                 │
└─────────────────────────────────────────┘
```

### Why This Matters

1. **Convenience**: Quickly reference past plans
2. **Comparison**: See how different procedures have different requirements
3. **Audit**: Track what instructions were given to which patients
4. **Workflow**: In a real clinic, staff could review and resend plans

---

## Data Flow: Complete Request Lifecycle

### 1. User Submits Form

```
User fills form → JavaScript collects data → POST /generate
```

### 2. Flask Receives Request

```python
appointment_data = request.get_json()
result = run_agent(appointment_data, rules_engine, prep_plan_builder, ...)
```

### 3. Agent Execution (LangGraph)

```
Initial State Created
  ↓
validate_input node
  - Checks required fields
  - Updates validated_data or errors
  - Logs to reasoning trace
  ↓
[Conditional: errors?]
  - If errors: END (return error response)
  - If no errors: continue
  ↓
apply_rules node
  - Determines fasting, arrival time, items
  - Updates rules_output
  - Logs rule decisions
  ↓
build_prep_plan node
  - Generates 10 structured sections
  - Calculates cutoff times
  - Updates prep_sections
  - Logs section count
  ↓
build_message node
  - Creates template message
  - Updates draft_message, preview, rules_explanation
  - Logs message length
  ↓
enhance_message node
  - Attempts LLM rewrite (if available)
  - Updates final_message, llm_used
  - Falls back to template if needed
  - Logs enhancement status
  ↓
save_output node
  - Saves to SQLite
  - Updates saved_record_id
  - Logs database ID
  ↓
END
```

### 4. Flask Returns Response

```json
{
  "error": false,
  "prep_sections": {
    "appointment_summary": "...",
    "fasting_plan": "...",
    "medication_instructions": "...",
    ...
  },
  "preview": "Surgery prep for John Smith...",
  "full_message": "Complete preparation instructions...",
  "rules_explanation": [...],
  "message_id": 42,
  "llm_used": true,
  "agent_trace": [
    {"step": "validate_input", "timestamp": "...", ...},
    {"step": "apply_rules_success", "timestamp": "...", ...},
    ...
  ]
}
```

### 5. JavaScript Renders UI

```
- Hides welcome state
- Shows success state
- Populates each prep section
- Updates reasoning trace panel
- Reloads history panel
```

---

## Key Design Decisions

### Why LangGraph Instead of Simple Functions?

**Before (Pipeline)**:
```python
validated = validate(data)
rules = apply_rules(validated)
message = build_message(rules)
enhanced = enhance_llm(message)
save(enhanced)
```

**Problems**:
- No state tracking
- Hard to add conditional logic
- No explainability
- Difficult to extend

**After (LangGraph)**:
```python
graph = StateGraph(AgentState)
graph.add_node("validate", validate_tool)
graph.add_node("rules", rules_tool)
graph.add_conditional_edges("validate", check_errors)
final_state = graph.invoke(initial_state)
```

**Benefits**:
- State flows automatically
- Conditional routing built-in
- Every step logged
- Easy to visualize and extend
- True agent behavior (not just a pipeline)

### Why Deterministic Rules + Optional LLM?

**Safety**: Medical instructions must be deterministic and auditable. The LLM only rewrites tone, never invents medical facts.

**Reliability**: System works offline or without API key. LLM is enhancement, not requirement.

**Compliance**: Rules can be reviewed by medical professionals. LLM output is secondary.

### Why Single-Page Interface?

**Agent-First UX**: The system IS the agent. Users interact with one intelligent assistant, not navigate between pages.

**Focus**: All information visible at once - input, output, reasoning, history.

**Modern**: Feels like ChatGPT or Claude, not a 2010s web form.

---

## Summary

This system is a **true AI agent** built with LangGraph that:

1. **Orchestrates** a multi-step workflow using a state machine
2. **Applies** deterministic medical rules for safety
3. **Generates** comprehensive, structured preparation plans
4. **Explains** its reasoning at every step
5. **Optionally enhances** output with LLM for friendly tone
6. **Persists** results for audit and history
7. **Presents** everything in a unified agent workspace UI

The **Agent Reasoning** panel shows the agent's decision-making process, and the **Recent Plans** panel provides quick access to historical outputs. Together, they make the system transparent, trustworthy, and practical for real-world use.
