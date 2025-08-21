from __future__ import annotations

import os
from typing import Optional, Tuple
from langchain_core.language_models.chat_models import BaseChatModel


# Curated list of text/chat-suitable models; not exhaustive.
# Excludes realtime, audio, and pure vision variants to avoid unsuitable modes for CLI text analysis.
OPENAI_MODELS = [
    # 4o family (text/chat)
    "gpt-4o",
    "gpt-4o-mini",
    # Next-gen
    "gpt-5",
    # o-series (reasoning-capable chat)
    "o4-mini",
    "o3",
    "o3-mini",
    # Legacy/compat still widely available in Chat API
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
]

GEMINI_MODELS = [
    # Recommended general chat models
    "gemini-2.5-pro",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    # Optional: fast text/chat
    "gemini-2.0-flash",
]


def infer_provider_from_model(model: str) -> Optional[str]:
    m = model.lower()
    if m.startswith("fake:"):
        return "fake"
    if m.startswith("gemini-"):
        return "google"
    if m.startswith("gpt-") or m.startswith("o3") or m.startswith("o4"):
        return "openai"
    # Try lookup in curated lists
    if model in OPENAI_MODELS:
        return "openai"
    if model in GEMINI_MODELS:
        return "google"
    return None


def get_chat_model(provider: str, model: str) -> BaseChatModel:
    prov = provider.lower()
    if prov in {"openai", "chatgpt", "gpt"}:
        from langchain_openai import ChatOpenAI

        # Lower temperature for more deterministic, conservative outputs
        return ChatOpenAI(model=model, temperature=0.2)
    if prov in {"google", "gemini"}:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, temperature=0.2)
    if prov in {"fake"}:
        from langchain_core.language_models.fake import FakeListLLM

        resp = os.environ.get("LOOPSTER_FAKE_RESPONSE", "OK")
        return FakeListLLM(responses=[resp])
    raise ValueError(f"Unsupported provider: {provider}")


def get_chat_model_for_model_name(model: str, provider: Optional[str] = None) -> Tuple[str, BaseChatModel]:
    prov = provider or infer_provider_from_model(model)
    if prov is None:
        raise ValueError(f"Could not infer provider from model: {model}")
    return prov, get_chat_model(prov, model)
