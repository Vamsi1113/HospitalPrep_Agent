import re

with open('agent/graph.py', 'r', encoding='utf-8') as f:
    graph_content = f.read()

# Add new imports
new_imports = """
from agent.tools import (
    intake_node_tool,
    triage_node_tool,
    protocol_retrieval_tool,
    admin_prep_tool,
    clinical_briefing_tool,
    patient_message_tool,
    clinician_summary_tool,
    save_output_tool,
    conversation_intake_node,
    voice_intake_node,
    slot_completion_node,
    scheduling_orchestrator_node
)
"""
# Replace imports block
# Find the line starting with "from agent.tools import (" and its end ")"
tools_import_pattern = re.compile(r'from agent\.tools import \([^)]+\)', re.MULTILINE)
graph_content = tools_import_pattern.sub(new_imports.strip(), graph_content)

# Update the graph definition
build_graph_replacement = """
def build_graph(
    rules_engine,
    retrieval_service,
    llm_client,
    storage
) -> StateGraph:
    \"\"\"
    Build the MULTI-PHASE LangGraph agent workflow with Conversational Orchestration.
    \"\"\"
    workflow = StateGraph(AgentState)
    
    # Phase 0: Conversational Intake & Scheduling (NEW)
    workflow.add_node("voice_intake", lambda state: voice_intake_node(state, llm_client))
    workflow.add_node("conversation_intake", lambda state: conversation_intake_node(state, llm_client))
    workflow.add_node("slot_completion", lambda state: slot_completion_node(state))
    workflow.add_node("scheduling_orchestrator", lambda state: scheduling_orchestrator_node(state))
    
    # Phase I: Intake & Triage
    workflow.add_node("intake", lambda state: intake_node_tool(state, llm_client))
    workflow.add_node("triage", lambda state: triage_node_tool(state))
    
    # Phase II: Protocols & Admin Prep
    workflow.add_node("protocol_retrieval", lambda state: protocol_retrieval_tool(state, retrieval_service))
    workflow.add_node("admin_prep", lambda state: admin_prep_tool(state, rules_engine))
    
    # Phase III: Clinical Briefing & Output
    workflow.add_node("clinical_briefing", lambda state: clinical_briefing_tool(state, llm_client))
    workflow.add_node("patient_message", lambda state: patient_message_tool(state, llm_client))
    workflow.add_node("clinician_summary", lambda state: clinician_summary_tool(state))
    workflow.add_node("save", lambda state: save_output_tool(state, storage))
    
    # Setting Entry Point
    workflow.set_entry_point("voice_intake")
    
    # Edges for Conversational Intake Loop
    workflow.add_edge("voice_intake", "conversation_intake")
    workflow.add_edge("conversation_intake", "slot_completion")
    workflow.add_edge("slot_completion", "scheduling_orchestrator")
    
    # Router Node Logic
    def confidence_router(state: AgentState) -> str:
        conv = state.get("conversation_data", {})
        if conv and conv.get("missing_fields"):
            return "ask_more"
        return "proceed_intake"
        
    workflow.add_conditional_edges(
        "scheduling_orchestrator",
        confidence_router,
        {
            "ask_more": END, 
            "proceed_intake": "intake"
        }
    )
    
    # Connecting Old Linear Path
    workflow.add_edge("intake", "triage")
    workflow.add_edge("triage", "protocol_retrieval")
    workflow.add_edge("protocol_retrieval", "admin_prep")
    workflow.add_edge("admin_prep", "clinical_briefing")
    workflow.add_edge("clinical_briefing", "patient_message")
    workflow.add_edge("patient_message", "clinician_summary")
    workflow.add_edge("clinician_summary", "save")
    workflow.add_edge("save", END)
    
    return workflow.compile()
"""

# Replace the build_graph function
build_graph_pattern = re.compile(r'def build_graph\(.*?\)\s*->\s*StateGraph:[\s\S]*?(?=def run_agent\()', re.MULTILINE)
graph_content = build_graph_pattern.sub(build_graph_replacement.strip() + '\n\n\n', graph_content)

with open('agent/graph.py', 'w', encoding='utf-8') as f:
    f.write(graph_content)
    
print("agent/graph.py successfully updated!")
