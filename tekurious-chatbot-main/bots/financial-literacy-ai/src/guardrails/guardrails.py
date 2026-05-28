import os
from pathlib import Path
import yaml
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from llm.output_parser import GuardrailsOutput
from utils.common import gemini_model_for_chat


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


def _load_prompt() -> PromptTemplate:
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "input_guardrails.yaml"
    with open(prompt_path, "r", encoding="utf-8") as file:
        prompt_data = yaml.safe_load(file)
    return PromptTemplate(
        input_variables=prompt_data.get("input_variables", ["query"]),
        template=prompt_data.get("template", ""),
    )


class Guardrails:
    def get_llm_response(self, query: str, history: list = None) -> GuardrailsOutput:
        parser = PydanticOutputParser(pydantic_object=GuardrailsOutput)
        prompt = _load_prompt()
        
        history_str = "No prior conversation."
        if history:
            lines = []
            for msg in history[-6:]:
                role = "User" if msg.get("role") == "user" else "Bot"
                content = msg.get("content", "").strip()
                lines.append(f"{role}: {content}")
            history_str = "\n".join(lines)

        fmt: dict = {"query": query}
        if "history" in prompt.input_variables:
            fmt["history"] = history_str
        if "format_instructions" in prompt.input_variables:
            fmt["format_instructions"] = parser.get_format_instructions()
        formatted_prompt = prompt.format(**fmt)
        
        if "history" not in prompt.input_variables and history:
            formatted_prompt = f"Conversation History:\n{history_str}\n\n{formatted_prompt}"
        
        llm = _get_llm().with_structured_output(GuardrailsOutput)
        return llm.invoke(formatted_prompt)

    def apply_input_guardrails(self, query: str, history: list = None):
        result = self.get_llm_response(query, history)
        return result.output, result.reason
