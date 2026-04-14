import re

with open('agent/state.py', 'r', encoding='utf-8') as f:
    state_content = f.read()

if 'class ConversationData(TypedDict)' not in state_content:
    new_state = """class ConversationData(TypedDict):
    \"\"\"Conversational Intake Tracking.\"\"\"
    missing_fields: List[str]
    suggested_options: Dict[str, List[str]]
    confidence_score: float
    current_transcript: Optional[str]
    is_voice: bool

"""
    state_content = state_content.replace('class IntakeData(TypedDict):', new_state + 'class IntakeData(TypedDict):')
    state_content = state_content.replace('    # Phase I: Triage & Intake\n    raw_intake: Dict[str, Any]', '    # Phase I: Triage & Intake\n    raw_intake: Dict[str, Any]\n    conversation_data: Optional[ConversationData]')
    state_content = state_content.replace('        raw_intake=raw_intake,', '        raw_intake=raw_intake,\n        conversation_data=None,')

    with open('agent/state.py', 'w', encoding='utf-8') as f:
        f.write(state_content)
    print("state.py updated!")
else:
    print("state.py already updated!")
