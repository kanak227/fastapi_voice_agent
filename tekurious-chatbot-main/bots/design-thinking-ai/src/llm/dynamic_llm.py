import os
from collections.abc import AsyncIterator
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from retrieval.mock_db import retrieve_documents
from utils.common import gemini_model_for_chat
from utils.state import BotState


class ScopeCheck(BaseModel):
    is_in_scope: bool


class HallucinationCheck(BaseModel):
    has_hallucination: bool


def _get_llm():
    provider = (os.getenv("LLM_PROVIDER") or "gemini").strip().lower()
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY. Set it as an environment variable.")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return ChatOpenAI(model=model, temperature=0, api_key=api_key)
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Missing GOOGLE_API_KEY. Set it as an environment variable.")
        return ChatGoogleGenerativeAI(
            model=gemini_model_for_chat(),
            temperature=0,
            google_api_key=api_key,
        )




def _format_history(history: list[dict[str, Any]]) -> str:
    if not history:
        return "No prior conversation."
    lines = []
    for msg in history[-6:]:
        role = "User" if msg.get("role") == "user" else "Design Thinking AI"
        content = msg.get("content", "").strip()
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _draft_prompt(state: BotState) -> str:
    docs = state['retrieved_docs']
    history_str = _format_history(state.get('history', []))
    _LANG_NAMES = {
        "en-US": "English", "en": "English",
        "hi": "Hindi", "hi-Latn": "Hinglish (Hindi written in Roman/Latin script, mixing Hindi and English naturally)",
        "ta": "Tamil", "te": "Telugu", "mr": "Marathi", "bn": "Bengali",
        "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam", "pa": "Punjabi",
        "fr": "French", "de": "German", "es": "Spanish",
        "ar": "Arabic", "zh": "Chinese", "ja": "Japanese",
    }
    lang_code = (state.get("response_language") or "en-US").strip()
    lang_name = _LANG_NAMES.get(lang_code, lang_code)
    is_english = lang_code in ("en-US", "en")
    lang_prefix = "" if is_english else (
        f"CRITICAL INSTRUCTION: You MUST respond ONLY in {lang_name}. "
        f"Do NOT use English in your response. Every word must be in {lang_name}. "
        f"Even if the question is asked in English, your answer must be entirely in {lang_name}.\n\n"
    )
    lang_instruction = "" if is_english else f"- CRITICAL: Respond ONLY in {lang_name}. Every word must be in {lang_name}, no English allowed.\n"
    if docs and "The core principles of" not in docs and "No matching passages" not in docs:
        return (
            f"{lang_prefix}"
            "You are a helpful assistant answering using the provided documents.\n"
            f"Documents:\n{docs}\n\n"
            f"Conversation History:\n{history_str}\n\n"
            f"Query: {state['original_query']}\n"
            "\n\nResponse Style Instructions:\n"
        f"{lang_instruction}"
        "- Use relevant emojis naturally throughout your response to make it engaging (e.g., 🌟, 💡, ✅, 📌, 🎯, 💪, 🧠, ❤️, 🌱, 📚, 🔑, ⭐, 🙌, ✨)\n- Use **bold** for key terms and important concepts\n- Use bullet points or numbered lists when listing multiple items\n- Use headings (## or ###) to organize longer responses into clear sections\n- Keep paragraphs short and scannable (2-3 sentences max)\n- Be warm, encouraging, and conversational in tone\n- Start with a brief engaging intro before diving into details\n- End with an encouraging closing thought or a follow-up question\n"
        "- Do NOT greet with 'Namaste', 'Hello', or any greeting unless the user explicitly greeted you first in this message. Jump straight into the answer.\n"
        "- IMPORTANT: If the query is unclear, misspelled, or you don't recognize a term, simply ask for clarification in 1-2 short sentences. Do NOT guess what the user meant, do NOT suggest unrelated topics, and do NOT list popular topics as filler.\n\n"
            "Answer:"
        )
    else:
        return (
            f"{lang_prefix}"
            "You are SmartE, a design thinking mentor. Answer the user's question about design thinking and innovation.\n"
            "Provide helpful, practical advice based on general design thinking and innovation knowledge.\n"
            f"Query: {state['original_query']}\n"
            "\n\nResponse Style Instructions:\n"
        f"{lang_instruction}"
        "- Use relevant emojis naturally throughout your response to make it engaging (e.g., 🌟, 💡, ✅, 📌, 🎯, 💪, 🧠, ❤️, 🌱, 📚, 🔑, ⭐, 🙌, ✨)\n- Use **bold** for key terms and important concepts\n- Use bullet points or numbered lists when listing multiple items\n- Use headings (## or ###) to organize longer responses into clear sections\n- Keep paragraphs short and scannable (2-3 sentences max)\n- Be warm, encouraging, and conversational in tone\n- Start with a brief engaging intro before diving into details\n- End with an encouraging closing thought or a follow-up question\n"
        "- Do NOT greet with 'Namaste', 'Hello', or any greeting unless the user explicitly greeted you first in this message. Jump straight into the answer.\n"
        "- IMPORTANT: If the query is unclear, misspelled, or you don't recognize a term, simply ask for clarification in 1-2 short sentences. Do NOT guess what the user meant, do NOT suggest unrelated topics, and do NOT list popular topics as filler.\n\n"
            "Answer:"
        )


def _extract_text_content(message: Any) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
            else:
                text = getattr(block, "text", None)
                if text:
                    parts.append(str(text))
        return "".join(parts)
    if content is None:
        return ""
    return str(content)


def check_input_scope(state: BotState) -> BotState:
    scope_llm = _get_llm().with_structured_output(ScopeCheck)
    history_str = _format_history(state.get('history', []))
    prompt = (
        "You are a multilingual domain classifier. The query may be in ANY language (Hindi, Tamil, Telugu, English, etc.). Evaluate the MEANING of the query, not the language it is written in.\nIMPORTANT: If the query is in a non-English language and you are unsure of its meaning, return is_in_scope=true (be permissive for non-English queries).\nGreetings and short follow-ups in any language are always IN SCOPE.\n\nYou are a domain classifier for design thinking and innovation topics.\n"
        "A query is IN SCOPE if it relates to:\n"
        "- Problem solving and user-centered design\n- Ideation, brainstorming, prototyping\n- Empathy mapping, user research, feedback loops\n- Design methodology (Double Diamond, Lean Startup, HCD)\n- Social innovation and creative problem solving\n"
        "\nA query is OUT OF SCOPE if it relates to:\n"
        "- Legal advice on patents, trademarks, or copyrights\n- Medical device design\n- Academic dishonesty (writing full projects)\n- Dangerous prototyping without supervision\n"
        "\n"
        f"Domain: {state['domain']}\n"
        f"Conversation History:\n{history_str}\n\n"
        f"Query: {state['original_query']}\n"
        "Return is_in_scope true if the query is IN SCOPE, false if OUT OF SCOPE."
    )
    result = scope_llm.invoke(prompt)
    state["is_in_scope"] = bool(result.is_in_scope)
    return state


def retrieve_context(state: BotState) -> BotState:
    tenant = (state.get("tenant_id") or "").strip() or None
    state["retrieved_docs"] = retrieve_documents(
        state["domain"], state["original_query"], tenant_id=tenant
    )
    return state


def generate_draft(state: BotState) -> BotState:
    llm = _get_llm()
    result = llm.invoke(_draft_prompt(state))
    state["draft_response"] = _extract_text_content(result).strip()
    return state


def verify_output(state: BotState) -> BotState:
    # Skip hallucination check when no documents are available
    docs = state['retrieved_docs']
    if not docs or "The core principles of" in docs or "No matching passages" in docs:
        state["hallucination_detected"] = False
        state["final_output"] = state["draft_response"]
        return state
    
    verify_llm = _get_llm().with_structured_output(HallucinationCheck)
    prompt = (
        "Check whether the answer includes claims that are not supported by the documents. "
        "Return has_hallucination true if unsupported content exists.\n"
        f"Documents:\n{state['retrieved_docs']}\n\n"
        f"Answer:\n{state['draft_response']}"
    )
    result = verify_llm.invoke(prompt)
    state["hallucination_detected"] = bool(result.has_hallucination)
    if state["hallucination_detected"]:
        state["loop_count"] += 1
    else:
        state["final_output"] = state["draft_response"]
    return state


def polite_refusal(state: BotState) -> BotState:
    state["final_output"] = f"Sorry, I can only help with {state['domain']} topics."
    return state


def _scope_router(state: BotState) -> str:
    # For voice input, skip the secondary scope check since Guardrails already approved
    if state.get("is_voice", False):
        return "retrieve_context"
    return "retrieve_context" if state["is_in_scope"] else "polite_refusal"


def _verify_router(state: BotState) -> str:
    if state["hallucination_detected"]:
        return "generate_draft" if state["loop_count"] < 3 else "polite_refusal"
    return "accept"


_graph = StateGraph(BotState)
_graph.add_node("check_input_scope", check_input_scope)
_graph.add_node("retrieve_context", retrieve_context)
_graph.add_node("generate_draft", generate_draft)
_graph.add_node("verify_output", verify_output)
_graph.add_node("polite_refusal", polite_refusal)
_graph.add_edge(START, "check_input_scope")
_graph.add_conditional_edges(
    "check_input_scope",
    _scope_router,
    {"retrieve_context": "retrieve_context", "polite_refusal": "polite_refusal"},
)
_graph.add_edge("retrieve_context", "generate_draft")
_graph.add_edge("generate_draft", "verify_output")
_graph.add_conditional_edges(
    "verify_output",
    _verify_router,
    {"generate_draft": "generate_draft", "polite_refusal": "polite_refusal", "accept": END},
)
_compiled_graph = _graph.compile()


def run_bot(
    query: str,
    domain: str,
    *,
    request_id: str = "",
    tenant_id: str = "",
    history: list[dict[str, Any]] = None,
    is_voice: bool = False,
    response_language: str = "en-US",
) -> str:
    state: BotState = {
        "original_query": query,
        "history": history or [],
        "domain": domain,
        "is_in_scope": False,
        "retrieved_docs": "",
        "draft_response": "",
        "hallucination_detected": False,
        "loop_count": 0,
        "final_output": "",
        "request_id": request_id or "",
        "tenant_id": tenant_id or "",
        "is_voice": is_voice,
        "response_language": response_language or "en-US",
    }
    result = _compiled_graph.invoke(state)
    return result.get("final_output") or "Sorry, I cannot answer that right now."


async def run_bot_stream(
    query: str,
    domain: str,
    *,
    request_id: str = "",
    tenant_id: str = "",
    history: list[dict[str, Any]] = None,
    is_voice: bool = False,
    response_language: str = "en-US",
) -> AsyncIterator[str]:
    """
    LangGraph-equivalent path with token streaming for the draft generator (Gemini astream).
    Scope check, retrieval, and verification stay synchronous; draft generation streams chunks.
    """
    state: BotState = {
        "original_query": query,
        "history": history or [],
        "domain": domain,
        "is_in_scope": False,
        "retrieved_docs": "",
        "draft_response": "",
        "hallucination_detected": False,
        "loop_count": 0,
        "final_output": "",
        "request_id": request_id or "",
        "tenant_id": tenant_id or "",
        "is_voice": is_voice,
        "response_language": response_language or "en-US",
    }
    state = check_input_scope(state)
    if not state["is_in_scope"]:
        if not state.get("is_voice", False):
            state = polite_refusal(state)
            msg = state.get("final_output") or ""
            if msg:
                yield msg
            return

    state = retrieve_context(state)
    llm = _get_llm()

    pieces: list[str] = []
    async for chunk in llm.astream(_draft_prompt(state)):
        text = _extract_text_content(chunk)
        if text:
            pieces.append(text)
            yield text
    state["draft_response"] = "".join(pieces).strip()
    state = verify_output(state)

    while state["hallucination_detected"]:
        if state["loop_count"] >= 3:
            state = polite_refusal(state)
            out = state.get("final_output") or ""
            if out:
                yield out
            return
        pieces = []
        async for chunk in llm.astream(_draft_prompt(state)):
            text = _extract_text_content(chunk)
            if text:
                pieces.append(text)
                yield text
        state["draft_response"] = "".join(pieces).strip()
        state = verify_output(state)
