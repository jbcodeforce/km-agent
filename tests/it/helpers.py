"""Shared helpers for integration tests."""

from __future__ import annotations

import os

from kma.config import get_llm_model_id, get_llm_provider

_PROVIDER_MODEL_TYPE = {
    "ollama": "OllamaResponses",
    "openai": "OpenAIResponses",
    "mlx": "OpenAILike",
    "anthropic": "Claude",
    "cursor": "CursorAgentModel",
}


def assert_uses_configured_llm(agent) -> None:
    """Assert agent chat model matches ``KMA_LLM_*`` from the loaded IT env."""
    provider = get_llm_provider()
    expected_type = _PROVIDER_MODEL_TYPE[provider]
    assert agent.model is not None
    assert agent.model.id == get_llm_model_id(), (
        f"model id {agent.model.id!r} != configured {get_llm_model_id()!r} "
        f"(KMA_ENV_FILE={os.environ.get('KMA_ENV_FILE')})"
    )
    assert type(agent.model).__name__ == expected_type, (
        f"expected {expected_type} for KMA_LLM_PROVIDER={provider!r}, "
        f"got {type(agent.model).__name__}"
    )
