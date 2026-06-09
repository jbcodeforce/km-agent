"""Construct default Agno chat models for the Compiler from environment."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from agno.models.base import Model
from agno.models.ollama import OllamaResponses
from agno.models.openai import OpenAIResponses, OpenAILike

from kma.config import (
    Env,
    get_llm_model_id,
    get_llm_provider,
    get_mlx_api_key,
    get_llm_base_url,
)
from kma.models.cursor_agent import CursorAgentModel, build_cursor_agent_options

if TYPE_CHECKING:
    from cursor_sdk import Agent, AgentOptions



def build_default_llm_model() -> Model:
    """Return the LLM chat model for ``KMA_LLM_PROVIDER``."""
    provider = get_llm_provider()
    mid = get_llm_model_id()

    if provider == "ollama":
        host = os.getenv(Env.KMA_LLM_HOST)
        if host:
            return OllamaResponses(id=mid, host=host)
        return OllamaResponses(id=mid)

    if provider == "openai":
        api_key = os.getenv(Env.OPENAI_API_KEY)
        if not api_key or not api_key.strip():
            raise ValueError(
                f"{Env.OPENAI_API_KEY} is required when {Env.KMA_LLM_PROVIDER}=openai "
                "(set the key in the environment or .env)"
            )
        base_url = os.getenv(Env.OPENAI_BASE_URL)
        base_url = base_url.strip() if base_url and base_url.strip() else None
        return OpenAIResponses(id=mid, api_key=api_key.strip(), base_url=base_url)

    if provider == "mlx":
        return OpenAILike(
            id=mid,
            base_url=get_llm_base_url(),
            api_key=get_mlx_api_key(),
        )

    # anthropic
    from agno.models.anthropic import Claude

    api_key = os.getenv(Env.ANTHROPIC_API_KEY)
    if not api_key or not api_key.strip():
        raise ValueError(
            f"{Env.ANTHROPIC_API_KEY} is required when {Env.KMA_LLM_PROVIDER}=anthropic "
            "(set the key in the environment or .env)"
        )
    return Claude(id=mid, api_key=api_key.strip())


def build_default_compiler_model() -> Model:
    """Alias for :func:`build_default_llm_model` — used by compile scripts."""
    return build_default_llm_model()
