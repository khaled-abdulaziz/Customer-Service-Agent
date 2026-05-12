# ==============================================================
# state.py — LangGraph Agent State
# ==============================================================

from typing import TypedDict, List, Optional


class AgentState(TypedDict):
    """
    Shared state passed between all LangGraph nodes.

    Each field is set by a specific node and read by others.
    """

    # ----------------------------------------------------------
    # INPUT — set by the customer before the graph starts
    # ----------------------------------------------------------

    message: str
    # The raw customer message in Arabic or English
    

    customer_id: Optional[int]
    
    

    # ----------------------------------------------------------
    # LANGUAGE — set by router_node, kept for the whole session
    # ----------------------------------------------------------

    language: str
    # Detected language of the conversation — "en" or "ar"

    # ----------------------------------------------------------
    # MULTI-TURN CONVERSATION CONTEXT
    # ----------------------------------------------------------

    pending_action: Optional[str]
    
    

    conversation_context: Optional[dict]
    
    

    # ----------------------------------------------------------
    # ROUTING — set by router_node
    # ----------------------------------------------------------

    intent: str
    
    

    extracted_data: dict
    

    # ----------------------------------------------------------
    # RESULTS — set by action nodes
    # ----------------------------------------------------------

    sql_result: Optional[List[dict]]
    
    

    action_taken: str
    
    
    

    # ----------------------------------------------------------
    # OUTPUT — set by the final answering node
    # ----------------------------------------------------------

    answer: str
   
    

    llm_used: str
    