"""Construct default Agno chat models for the Compiler from environment."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from agno.models.base import Model
from agno.models.ollama import OllamaResponses
from agno.models.openai import OpenAIResponses

from kma.config import (
    get_cursor_auto_create_pr,
    get_cursor_cwd,
    get_cursor_repo_ref,
    get_cursor_repo_url,
    get_cursor_runtime,
    get_llm_model_id,
    get_llm_provider,
)
from kma.models.cursor_agent import CursorAgentModel, build_cursor_agent_options

if TYPE_CHECKING:
    from cursor_sdk import Agent, AgentOptions


def build_cursor_agent(*, model_id: str | None = None) -> Agent:
    """Create a Cursor SDK agent handle using km-agent environment settings."""
    from cursor_sdk import Agent

    mid = model_id or get_llm_model_id()
    api_key = _cursor_api_key()
    options = build_cursor_agent_options(
        model_id=mid,
        api_key=api_key,
        cwd=get_cursor_cwd(),
        runtime=get_cursor_runtime(),
        repo_url=get_cursor_repo_url(),
        repo_ref=get_cursor_repo_ref(),
        auto_create_pr=get_cursor_auto_create_pr(),
    )
    return Agent.create(options)


def cursor_agent_options(*, model_id: str | None = None) -> AgentOptions:
    """Return Cursor SDK options without starting an agent."""
    mid = model_id or get_llm_model_id()
    return build_cursor_agent_options(
        model_id=mid,
        api_key=_cursor_api_key(),
        cwd=get_cursor_cwd(),
        runtime=get_cursor_runtime(),
        repo_url=get_cursor_repo_url(),
        repo_ref=get_cursor_repo_ref(),
        auto_create_pr=get_cursor_auto_create_pr(),
    )


def _cursor_api_key() -> str:
    api_key = (os.getenv("CURSOR_API_KEY") or os.getenv("KMA_LLM_API_KEY") or "").strip()
    if not api_key:
        raise ValueError(
            "CURSOR_API_KEY is required when KMA_LLM_PROVIDER=cursor "
            "(set the key in the environment or .env)"
        )
    return api_key


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

    if provider == "cursor":
        return CursorAgentModel(
            id=mid,
            api_key=_cursor_api_key(),
            cwd=get_cursor_cwd(),
            runtime=get_cursor_runtime(),
            repo_url=get_cursor_repo_url(),
            repo_ref=get_cursor_repo_ref(),
            auto_create_pr=get_cursor_auto_create_pr(),
        )

    # anthropic
    from agno.models.anthropic import Claude

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "ANTHROPIC_API_KEY is required when KMA_LLM_PROVIDER=anthropic "
            "(set the key in the environment or .env)"
        )
    return Claude(id=mid, api_key=api_key.strip())


def build_default_compiler_model() -> Model:
    """Alias for :func:`build_default_llm_model` — used by compile scripts."""
    return build_default_llm_model()
