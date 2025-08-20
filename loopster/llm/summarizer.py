from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


@dataclass
class LLMSelection:
    provider: str
    model: str


class Summarizer:
    """Session log summarizer using a LangChain chat model.

    This class can be constructed with a ready LLM (for tests), or it can
    dynamically instantiate a provider model based on `provider` and `model`.
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._llm = llm
        self._selection = None
        if llm is None and provider and model:
            self._selection = LLMSelection(provider=provider, model=model)

    def _build_llm(self) -> BaseChatModel:
        if self._llm is not None:
            return self._llm
        if not self._selection:
            raise RuntimeError(
                "No LLM provided. Specify `llm` or (`provider`, `model`)."
            )
        provider = self._selection.provider.lower()
        model = self._selection.model
        if provider in {"openai", "chatgpt", "gpt"}:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(model=model)
        if provider in {"google", "gemini"}:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(model=model)
        raise ValueError(f"Unsupported provider: {self._selection.provider}")

    def _build_chain(self, output_format: str):
        instructions = (
            "You are Loopster, a CLI session summarizer.\n"
            "Summarize the session log succinctly. Focus on:\n"
            "- Commands executed and their intent\n"
            "- Notable outputs, errors, and retries\n"
            "- Configuration changes or suggestions\n"
            "Write the summary in {output_format} format."
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", instructions),
                (
                    "human",
                    "Session log follows. Provide a concise summary.\n\n{log}",
                ),
            ]
        )
        llm = self._build_llm()
        return prompt | llm | StrOutputParser()

    def summarize_text(self, log_text: str, *, output_format: str = "text") -> str:
        chain = self._build_chain(output_format)
        return chain.invoke({"log": log_text, "output_format": output_format})

