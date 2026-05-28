from typing import TypedDict, List, Dict, Any


class BotState(TypedDict):
    original_query: str
    history: List[Dict[str, Any]]
    domain: str
    is_in_scope: bool
    retrieved_docs: str
    draft_response: str
    hallucination_detected: bool
    loop_count: int
    final_output: str
    request_id: str
    tenant_id: str
    is_voice: bool
    response_language: str
