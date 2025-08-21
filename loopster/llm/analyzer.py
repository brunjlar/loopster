from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .model_factory import get_chat_model


@dataclass
class LLMSelection:
    provider: str
    model: str


def build_analyzer_instructions() -> str:
    return (
        "You are Loopster, a CLI assistant configuration analyst.\n"
        "Goal: Improve the assistant's GLOBAL, project-agnostic config (system prompt).\n"
        "Given a session log and the current config, identify general lessons that\n"
        "apply across arbitrary projects.\n\n"
        "Constraints:\n"
        "- Focus on durable, project-agnostic guidance (policies, reasoning steps,\n"
        "  safety, clarification strategies, retry policy, uncertainty handling).\n"
        "- Avoid project-specific details (paths, filenames, API schemas, repo structure,\n"
        "  proper nouns, domain-only facts).\n"
        "- Do not include secrets or any content copied from the session.\n"
        "- Use placeholders where needed (e.g., <PROJECT>, <API_KEY>).\n"
        "- Prefer concise, high-signal directives.\n\n"
        "Output format: Return a single JSON object with exactly these keys:\n"
        "{{\"rationale\": string, \"updated_config\": string}}.\n"
        "Do not include code fences. Do not include extra text."
    )


class Analyzer:
    """Analyze a session log against a config and propose improvements.

    Mirrors the Summarizer structure but accepts both a log and a config
    input and returns an updated config (and optionally rationale) based on
    lessons learned from the session.
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._llm = llm
        self._selection: Optional[LLMSelection] = None
        if llm is None and provider and model:
            self._selection = LLMSelection(provider=provider, model=model)

    def _build_llm(self) -> BaseChatModel:
        if self._llm is not None:
            return self._llm
        if not self._selection:
            raise RuntimeError(
                "No LLM provided. Specify `llm` or (`provider`, `model`)."
            )
        return get_chat_model(self._selection.provider, self._selection.model)

    def _build_chain(self):
        instructions = build_analyzer_instructions()
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", instructions),
                (
                    "human",
                    "Session log and current config follow.\n"
                    "Return a JSON object with keys 'rationale' and 'updated_config'.\n\n"
                    "=== SESSION LOG ===\n{log}\n\n=== CONFIG ===\n{config}",
                ),
            ]
        )
        llm = self._build_llm()
        return prompt | llm | StrOutputParser()

    def analyze_text(
        self,
        *,
        log_text: str,
        config_text: str,
        output_format: str = "json",
    ) -> str:
        chain = self._build_chain()
        return chain.invoke(
            {
                "log": log_text,
                "config": config_text,
            }
        )
