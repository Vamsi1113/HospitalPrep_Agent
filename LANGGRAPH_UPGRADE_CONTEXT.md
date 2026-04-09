# LangGraph Agent Architecture - Complete System Documentation

## Overview

The Appointment Prep AI Agent is a TRUE AI AGENT system powered by LangGraph. It features node-based workflow execution, explicit state management, and full agent reasoning traceability.

**Status:** ✅ Fully operational and production-ready

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure (optional OpenAI API key)
cp .env.example .env

# Run
python app.py

# Access
http://localhost:5000
```

## Architecture Transformation

### Before (Pipeline-based)
```
Flask → orchestrator.py → Sequential function calls → Response
```

### After (LangGraph Agent)
```
Flask → LangGraph StateGraph → Node-based tools → Agent State → Response
                                      ↓
                              Reasoning Trace
```

## Key Components

### 1. Agent State (agent/state.py)
- **TypedDict** defining the complete agent state
- Flows through all nodes in the graph
- Tracks:
  - Input data
  - Validated data
  - Rules output
  - Draft and final messages
  - Errors
  - Metadata with reasoning trace
  - LLM usage flag
  - Message ID

### 2. Agent Tools (agent/tools.py)
Services wrapped as LangGraph tools:

| Tool | Service | Purpose |
|------|---------|---------|
| `validate_input_tool` | validation.py | Validate appointment data |
| `apply_rules_tool` | rules_engine.py | Apply deterministic medical rules |
| `build_message_tool` | message_builder.py | Generate template message |
| `enhance_message_tool` | llm_client.py | Optional LLM enhancement |
| `save_output_tool` | storage.py | Persist to database |

Each tool:
- Takes agent state as input
- Performs its operation
- Updates state with results
- Logs step to reasoning trace
- Returns updated state

### 3. Agent Graph (agent/graph.py)
LangGraph StateGraph with node-based workflow:

```
START
  ↓
validate_input
  ↓
[Conditional: errors?]
  ↓ (no errors)
apply_rules
  ↓
build_message
  ↓
enhance_message (conditional: LLM available)
  ↓
save_output
  ↓
END
```

**Conditional Logic:**
- If validation fails → Skip to END with errors
- If LLM unavailable → enhance_message uses template fallback
- All nodes log to reasoning trace

### 4. System Prompts (agent/prompts.py)
Centralized prompt management:
- `ENHANCE_MESSAGE_PROMPT` - Safety-enforced LLM rewriting
- `REASONING_AGENT_PROMPT` - Advanced reasoning mode (future)
- `REFLECTION_PROMPT` - Agent self-reflection (future)

## Agent Execution Flow

### 1. Request Initiation
```python
# app.py
result = run_agent(
    appointment_data,
    rules_engine,
    message_builder,
    llm_client,
    storage
)
```

### 2. State Initialization
```python
# agent/graph.py
initial_state = create_initial_state(input_data)
initial_state["metadata"]["start_time"] = datetime.now().isoformat()
```

### 3. Graph Execution
```python
graph = build_graph(rules_engine, message_builder, llm_client, storage)
final_state = graph.invoke(initial_state)
```

### 4. Node Execution
Each node:
1. Receives current state
2. Performs operation
3. Logs to `state["metadata"]["steps"]`
4. Updates state fields
5. Returns updated state

### 5. Response Generation
```python
return {
    "error": False,
    "preview": final_state["preview"],
    "full_message": final_state["final_message"],
    "rules_explanation": final_state["rules_explanation"],
    "message_id": final_state["message_id"],
    "llm_used": final_state["llm_used"],
    "agent_trace": final_state["metadata"]["steps"]  # NEW
}
```

## Agent Reasoning Trace

### Structure
Each step in the trace contains:
```python
{
    "step": "validate_input",
    "timestamp": "2024-01-15T10:30:00",
    "description": "Validating appointment data",
    # Additional step-specific fields
}
```

### Example Trace
```json
[
  {
    "step": "validate_input",
    "timestamp": "2024-01-15T10:30:00.123",
    "description": "Validating appointment data"
  },
  {
    "step": "validate_input_success",
    "timestamp": "2024-01-15T10:30:00.456",
    "description": "All fields validated successfully"
  },
  {
    "step": "apply_rules",
    "timestamp": "2024-01-15T10:30:00.789",
    "description": "Applying deterministic preparation rules"
  },
  {
    "step": "apply_rules_success",
    "timestamp": "2024-01-15T10:30:01.012",
    "category": "surgery",
    "fasting_required": true,
    "fasting_hours": 12,
    "arrival_minutes": 30
  },
  {
    "step": "build_message",
    "timestamp": "2024-01-15T10:30:01.234",
    "description": "Generating template-based message"
  },
  {
    "step": "build_message_success",
    "timestamp": "2024-01-15T10:30:01.567",
    "message_length": 847,
    "preview_length": 156
  },
  {
    "step": "enhance_message",
    "timestamp": "2024-01-15T10:30:01.890",
    "description": "Attempting LLM enhancement",
    "llm_available": true
  },
  {
    "step": "enhance_message_success",
    "timestamp": "2024-01-15T10:30:03.123",
    "description": "LLM enhancement successful",
    "enhanced_length": 892
  },
  {
    "step": "save_output",
    "timestamp": "2024-01-15T10:30:03.456",
    "description": "Saving message to database"
  },
  {
    "step": "save_output_success",
    "timestamp": "2024-01-15T10:30:03.789",
    "message_id": 42
  }
]
```

## UI Integration

### Dashboard Updates
New card added to display agent reasoning:

```html
<!-- Agent Reasoning Trace Card -->
<div id="agent-trace-card" class="card">
    <div class="card-header">
        <h2 class="card-title">🤖 Agent Reasoning Trace</h2>
    </div>
    <div class="card-body">
        <div id="agent-trace-list" class="agent-trace-list"></div>
    </div>
</div>
```

### JavaScript Updates
```javascript
// Display agent trace
if (result.agent_trace && result.agent_trace.length > 0) {
    agentTraceList.innerHTML = result.agent_trace.map(step => `
        <div class="trace-item">
            <div class="trace-step">${escapeHtml(step.step)}</div>
            <div class="trace-description">${escapeHtml(step.description || '')}</div>
            <div class="trace-timestamp">${escapeHtml(step.timestamp || '')}</div>
        </div>
    `).join('');
    agentTraceCard.style.display = 'block';
}
```

### CSS Styling
```css
.agent-trace-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
}

.trace-item {
    padding: var(--spacing-sm) var(--spacing-md);
    background-color: var(--color-neutral-50);
    border-radius: var(--border-radius-md);
    border-left: 3px solid var(--color-secondary-light);
}
```

## Safety Guarantees

### Medical Instruction Safety
1. **Rules engine ALWAYS runs before LLM**
   - Enforced by graph structure
   - `apply_rules` node comes before `enhance_message`

2. **LLM NEVER adds medical instructions**
   - System prompt explicitly forbids invention
   - LLM only rewrites tone/wording
   - Template fallback if LLM fails

3. **Deterministic rules are source of truth**
   - All medical requirements from rules_engine.py
   - No AI involvement in medical decisions

### Error Handling
- Validation errors stop workflow early
- Each tool has try-catch error handling
- Errors logged to reasoning trace
- Graceful fallback at every step

## Dependencies

### New Dependencies
```
langgraph>=0.0.20       # LangGraph for agent orchestration
langchain>=0.1.0        # LangChain core framework
langchain-core>=0.1.0   # LangChain core components
langchain-openai>=0.0.5 # LangChain OpenAI integration
```

### Existing Dependencies (Unchanged)
- Flask (web framework)
- python-dotenv (configuration)
- openai (LLM client)
- pytest, hypothesis (testing)

## File Structure

### New Files
```
agent/
├── graph.py      # LangGraph StateGraph definition
├── state.py      # Agent state TypedDict
├── tools.py      # Service wrappers as tools
└── prompts.py    # System prompts
```

### Modified Files
```
app.py                    # Updated to use run_agent()
requirements.txt          # Added LangGraph dependencies
README.md                 # Updated architecture docs
templates/dashboard.html  # Added agent trace card
static/js/app.js         # Added trace display logic
static/css/styles.css    # Added trace styling
```

### Unchanged Files
```
services/               # All services unchanged
  ├── rules_engine.py
  ├── message_builder.py
  ├── llm_client.py
  ├── storage.py
  ├── validation.py
  └── models.py

templates/
  ├── base.html
  └── index.html

data/                   # All data files unchanged
tests/                  # All tests unchanged (still pass)
```

## Running the System

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
```bash
cp .env.example .env
# Add OPENAI_API_KEY (optional)
```

### Execution
```bash
python app.py
```

### Access
```
http://localhost:5000
```

## Success Criteria ✅

- [x] LangGraph is actively used
- [x] Flow is node-based (not sequential function calls)
- [x] State is passed across nodes
- [x] Tools are modular
- [x] Agent trace is visible in UI
- [x] App still runs locally
- [x] No UI rebuild required
- [x] All services preserved
- [x] Safety guarantees maintained

## Future Enhancements

### 1. Reasoning Agent Mode
Implement advanced mode where LLM decides:
- Which tools to call
- In what order
- Based on user request

### 2. Agent Reflection
Add self-reflection capability:
- Agent reviews its own trace
- Identifies improvements
- Learns from mistakes

### 3. Multi-Agent Collaboration
Add specialized agents:
- Validation agent
- Rules agent
- Message generation agent
- Quality assurance agent

### 4. Graph Visualization
Add visual graph display:
- Show node execution in real-time
- Highlight current node
- Display state at each step

## Recent Fixes (April 8, 2026)

### Initial Integration Bugs (Fixed)
Three critical bugs were identified and fixed in the initial LangGraph integration:

1. **Validation tuple unpacking** - Fixed handling of `(is_valid, errors)` return value
2. **Rules engine arguments** - Fixed to pass `appointment_type` and `procedure` separately  
3. **Storage method signature** - Fixed to pass `appointment_data` as dictionary

### Cache Cleanup (Fixed)
4. **Module import error** - Fixed `agent/__init__.py` to import LangGraph modules instead of old orchestrator
5. **Python cache** - Cleared `__pycache__` directories to remove stale bytecode

**Status:** All bugs resolved. System fully operational.

**Note:** If you encounter `ModuleNotFoundError: No module named 'agent.orchestrator'`, clear Python cache:
```bash
Remove-Item -Recurse -Force agent/__pycache__
Remove-Item -Recurse -Force __pycache__
```

---

## Conclusion

The system has been successfully transformed from a pipeline-based application into a TRUE AI AGENT system using LangGraph. The architecture now features:

- **Node-based workflow** with explicit state management
- **Agent reasoning trace** for full explainability
- **Modular tools** wrapping existing services
- **Conditional routing** based on state
- **Safety guarantees** maintained throughout
- **Local execution** with no cloud dependencies

The application is production-ready and maintains all existing functionality while adding powerful agent capabilities.
