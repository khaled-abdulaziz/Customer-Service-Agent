# ==============================================================
# workflow.py — LangGraph Workflow
# ==============================================================

from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    router_node,
    order_status_node,
    availability_node,
    return_node,
    complaint_node,
    faq_node,
)


# ==============================================================
# Graph Builder
# ==============================================================

def build_graph():
    """
    Builds and compiles the LangGraph customer service workflow.

    Flow:
        [START]
           ↓
        router_node  ← detects intent + locks in language
           ↓
        ┌──────────────────────────────────────┐
        │ order_status  → order_status_node    │
        │ availability  → availability_node    │
        │ return        → return_node          │
        │ complaint     → complaint_node       │
        │ faq / unknown → faq_node             │
        └──────────────────────────────────────┘
           ↓
         [END]

    Returns:
        Compiled LangGraph app ready to invoke.
    """
    graph = StateGraph(AgentState)

    # Register all nodes
    graph.add_node("router",        router_node)
    graph.add_node("order_status",  order_status_node)
    graph.add_node("availability",  availability_node)
    graph.add_node("return",        return_node)
    graph.add_node("complaint",     complaint_node)
    graph.add_node("faq",           faq_node)

    
    graph.set_entry_point("router")

    def route_by_intent(state: AgentState) -> str:
        intent = state.get("intent", "faq")

        routing_map = {
            "order_status": "order_status",
            "availability": "availability",
            "return":       "return",
            "complaint":    "complaint",
            "faq":          "faq",
            "unknown":      "faq",   
        }

        return routing_map.get(intent, "faq")

    
    graph.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "order_status": "order_status",
            "availability": "availability",
            "return":       "return",
            "complaint":    "complaint",
            "faq":          "faq",
        }
    )

    
    graph.add_edge("order_status", END)
    graph.add_edge("availability", END)
    graph.add_edge("return",       END)
    graph.add_edge("complaint",    END)
    graph.add_edge("faq",          END)

    return graph.compile()


# ==============================================================
# run_agent — main entry point
# ==============================================================

def run_agent(
    message:              str,
    customer_id:          int  = None,
    pending_action:       str  = None,
    conversation_context: dict = None,
    language:             str  = "",
) -> dict:
    """
    Runs the full customer service agent pipeline.

    Args:
        message              (str) : Customer message in Arabic or English.
        customer_id          (int) : Customer ID if known (from session).
        pending_action       (str) : Multi-turn action in progress.
        conversation_context (dict): Saved conversation memory.
        language             (str) : Language locked in from previous turns.
                                     Pass "" on first message — router will detect it.
                                     Pass "en" or "ar" on follow-up messages so the
                                     language does not reset when customer replies with "3".

    Returns:
        dict with keys:
            - answer
            - intent
            - action_taken
            - llm_used
            - pending_action
            - conversation_context
            - language             ← always return this back to Streamlit to save
    """
    app = build_graph()

    initial_state: AgentState = {
        "message":              message,
        "customer_id":          customer_id,

        
        
        "language":             language,

        
        "pending_action":       pending_action,
        "conversation_context": conversation_context or {},

        
        "intent":               "",
        "extracted_data":       {},

        
        "sql_result":           [],
        "action_taken":         "",

        
        "answer":               "",
        "llm_used":             "",
    }

    result = app.invoke(initial_state)

    return {
        "answer":               result.get("answer", "❌ No response generated."),
        "intent":               result.get("intent", "unknown"),
        "action_taken":         result.get("action_taken", ""),
        "llm_used":             result.get("llm_used", "gpt-4o"),

        
        "pending_action":       result.get("pending_action"),
        "conversation_context": result.get("conversation_context", {}),

        
        "language":             result.get("language", "en"),
    }