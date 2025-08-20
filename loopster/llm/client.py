from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .model_factory import get_chat_model, get_chat_model_for_model_name


@dataclass
class LLMConfig:
    provider: str
    model: str


class LLMClient:
    """Minimal client for sending a query to an LLM.

    - Supports supplying a ready `llm` for tests.
    - Or dynamic creation via (`provider`, `model`).
    - Accepts a `system_prompt` and an optional user `prompt` and/or list of text files.
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._llm = llm
        self._cfg: Optional[LLMConfig] = None
        if llm is None and provider and model:
            self._cfg = LLMConfig(provider=provider, model=model)

    def _build_llm(self) -> BaseChatModel:
        if self._llm is not None:
            return self._llm
        if self._cfg:
            return get_chat_model(self._cfg.provider, self._cfg.model)
        raise RuntimeError(
            "No LLM provided. Specify `llm` or (`provider`, `model`)."
        )

    def _build_llm_by_model_only(self, model: str) -> tuple[str, BaseChatModel]:
        return get_chat_model_for_model_name(model)

    @staticmethod
    def _read_files(files: Iterable[Path]) -> Sequence[tuple[str, str]]:
        out = []
        for p in files:
            text = Path(p).read_text()
            out.append((str(p), text))
        return out

    @staticmethod
    def _compose_user_content(prompt: Optional[str], files: Sequence[tuple[str, str]]):
        parts: list[str] = []
        if prompt:
            parts.append(str(prompt))
        if files:
            parts.append("FILES:")
            for name, content in files:
                parts.append(f"=== {name} ===")
                parts.append(content)
        return "\n\n".join(parts).strip()

    def _build_chain(self, system_prompt: str):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                ("human", "{user_content}"),
            ]
        )
        return prompt | self._build_llm() | StrOutputParser()

    def ask(
        self,
        *,
        system_prompt: str,
        prompt: Optional[str] = None,
        files: Optional[Iterable[Path]] = None,
        model: Optional[str] = None,
    ) -> str:
        if not system_prompt:
            raise ValueError("system_prompt is required")
        file_pairs: Sequence[tuple[str, str]] = []
        if files:
            file_pairs = self._read_files(files)
        user_content = self._compose_user_content(prompt, file_pairs)
        # If a direct llm/config wasn't provided, allow usage with model-only via provider inference
        if self._llm is None and self._cfg is None:
            if not model:
                raise RuntimeError("No model specified and no LLM configured")
            prov, llm = self._build_llm_by_model_only(model)
            prompt = ChatPromptTemplate.from_messages(
                [("system", "{system_prompt}"), ("human", "{user_content}")]
            )
            chain = prompt | llm | StrOutputParser()
            return chain.invoke({
                "system_prompt": system_prompt,
                "user_content": user_content,
            })
        chain = self._build_chain(system_prompt)
        return chain.invoke({
            "system_prompt": system_prompt,
            "user_content": user_content,
        })
