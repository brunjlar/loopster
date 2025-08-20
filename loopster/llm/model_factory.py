from __future__ import annotations

import os
from typing import Optional, Tuple
from langchain_core.language_models.chat_models import BaseChatModel


# Curated list of commonly used models; not exhaustive.
OPENAI_MODELS = [
    # GPT-4o family
    "gpt-4o", "gpt-4o-mini", "gpt-4o-realtime-preview", "gpt-4o-audio-preview",
    # Legacy/compat
    "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
    # o-series (reasoning)
    "o3", "o3-mini", "o4-mini",
    # Next-gen
    "gpt-5",
]

GEMINI_MODELS = [
    "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b",
    "gemini-1.0-pro", "gemini-1.0-pro-vision",
    # Next-gen
    "gemini-2.5-pro",
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

        return ChatOpenAI(model=model)
    if prov in {"google", "gemini"}:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model)
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
