# Project Structure

## Core Application Files

```
appointment-prep-ai-agent/
├── app.py                          # Flask application entry point
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment configuration template
├── .gitignore                      # Git ignore rules
├── README.md                       # User documentation
└── LANGGRAPH_UPGRADE_CONTEXT.md   # Complete system documentation
```

## Agent Architecture (LangGraph)

```
agent/
├── graph.py                        # LangGraph StateGraph definition
├── state.py                        # Agent state TypedDict
├── tools.py                        # Service wrappers as LangGraph tools
├── prompts.py                      # System prompts for LLM
└── __init__.py                     # Package initialization
```

## Core Services (Business Logic)

```
services/
├── rules_engine.py                 # Deterministic medical rules
├── message_builder.py              # Message generation
├── llm_client.py                   # OpenAI API integration
├── storage.py                      # SQLite persistence
├── validation.py                   # Input validation
├── models.py                       # Data models (dataclasses)
└── __init__.py                     # Package initialization
```

## Frontend (UI)

```
templates/
├── base.html                       # Base template with navigation
├── index.html                      # Landing page
└── dashboard.html                  # Main dashboard with form

static/
├── css/
│   └── styles.css                  # Application styles
└── js/
    └── app.js                      # Frontend JavaScript (AJAX, validation)
```

## Data Files

```
data/
├── design_tokens.json              # UI design system tokens
├── page_content.json               # Page content configuration
├── sample_appointments.json        # Sample appointment data
└── appointments.db                 # SQLite database (auto-created)
```

## Tests

```
tests/
├── test_rules_engine.py            # Rules engine unit tests
├── test_validation.py              # Validation unit tests
├── test_validation_integration.py  # Validation integration tests
├── test_message_builder.py         # Message builder unit tests
├── test_message_builder_integration.py
├── test_llm_client.py              # LLM client tests
├── test_storage.py                 # Storage unit tests
├── test_storage_integration.py     # Storage integration tests
└── test_error_handling.py          # Error handling tests
```

## Configuration

```
.kiro/
└── specs/
    └── appointment-prep-ai-agent/  # Original spec files
        ├── design.md
        ├── requirements.md
        └── tasks.md
```

## Generated/Cache Directories (Git Ignored)

```
__pycache__/                        # Python bytecode cache
.pytest_cache/                      # Pytest cache
.hypothesis/                        # Hypothesis test data
htmlcov/                            # Coverage reports
.vscode/                            # VS Code settings
```

## Key Files Explained

### Application Layer
- **app.py** - Flask routes, service initialization, calls LangGraph agent
- **requirements.txt** - All dependencies including LangGraph, LangChain

### Agent Layer (NEW - LangGraph)
- **agent/graph.py** - Defines the agent workflow as a StateGraph
- **agent/state.py** - TypedDict defining state structure
- **agent/tools.py** - Wraps services as tools with state management
- **agent/prompts.py** - System prompts for LLM interactions

### Service Layer (Unchanged)
- **services/rules_engine.py** - Deterministic medical rules (safety-critical)
- **services/message_builder.py** - Template and LLM message generation
- **services/llm_client.py** - OpenAI API with graceful fallback
- **services/storage.py** - SQLite CRUD operations
- **services/validation.py** - Input validation logic
- **services/models.py** - Data models (PrepRules, etc.)

### Frontend Layer (Enhanced)
- **templates/dashboard.html** - Added agent reasoning trace card
- **static/js/app.js** - Added trace display logic
- **static/css/styles.css** - Added trace styling

## Documentation

- **README.md** - User-facing documentation (installation, usage, troubleshooting)
- **LANGGRAPH_UPGRADE_CONTEXT.md** - Complete system architecture and technical documentation
- **PROJECT_STRUCTURE.md** - This file

## Total Line Count (Approximate)

- Python code: ~3,500 lines
- Tests: ~2,000 lines
- Frontend (HTML/CSS/JS): ~1,500 lines
- Documentation: ~1,000 lines

**Total: ~8,000 lines of code**
