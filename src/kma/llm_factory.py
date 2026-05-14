"""Construct default Agno chat models for the Compiler from environment."""

from __future__ import annotations

import os

from agno.models.base import Model
from agno.models.ollama import OllamaResponses
from agno.models.openai import OpenAIResponses

from kma.config import get_llm_provider, get_llm_model_id


def build_default_llm_model() -> Model:
    """Return the LLM chat model for ``KMA_LLM_PROVIDER``."""
    provider = get_llm_provider()
    mid = get_llm_model_id()

    if provider == "ollama":
        host = os.getenv("OLLAMA_HOST")
        if host:
            return OllamaResponses(id=mid, host=host)
        return OllamaResponses(id=mid)

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.strip():
            raise ValueError(
                "OPENAI_API_KEY is required when KMA_LLM_PROVIDER=openai "
                "(set the key in the environment or .env)"
            )
        base_url = os.getenv("OPENAI_BASE_URL")
        base_url = base_url.strip() if base_url and base_url.strip() else None
        return OpenAIResponses(id=mid, api_key=api_key.strip(), base_url=base_url)

    # anthropic
    from agno.models.anthropic import Claude

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "ANTHROPIC_API_KEY is required when KMA_LLM_PROVIDER=anthropic "
            "(set the key in the environment or .env)"
        )
    return Claude(id=mid, api_key=api_key.strip())
