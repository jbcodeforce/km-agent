"""Integration tests against a running Ollama server (Agno + OllamaResponses).

Run explicitly (not selected by plain ``pytest tests/ut`` if you only pass that path).
Start Ollama on the host first: ``./scripts/starter.sh`` (see ``docs/DEVELOPER_PRACTICES.md``).

    uv run pytest tests/it -m integration -v

Environment:

- ``LLM_HOST`` — Ollama base URL (default ``http://127.0.0.1:11434``).
- ``KMA_IT_OLLAMA_MODEL`` — optional; force a pulled model id for this suite (e.g. a
  small model) when the compiler default is present but cannot run on this machine.
"""

from __future__ import annotations

import pytest
from agno.agent import Agent
from agno.models.ollama import OllamaResponses
from agno.run.base import RunStatus


@pytest.mark.integration
def test_ollama_agno_minimal_chat(
    ollama_model_id_for_integration: str,
    ollama_host: str,
) -> None:
    """One real model round-trip via Agno (same stack as the Compiler agent)."""
    agent = Agent(
        model=OllamaResponses(id=ollama_model_id_for_integration, host=ollama_host),
        instructions="Reply with at most one short sentence. No preamble.",
    )
    out = agent.run('Reply with exactly the single word "pong" and nothing else.')
    if out.status != RunStatus.completed:
        msg = (out.content or "").lower()
        if "memory" in msg or "not found" in msg or "requires more" in msg:
            pytest.skip(
                f"Ollama cannot run model {ollama_model_id_for_integration!r} "
                f"(set KMA_IT_OLLAMA_MODEL to a smaller pulled model): {out.content!r}"
            )
    assert out.status == RunStatus.completed, f"run failed: status={out.status!r} content={out.content!r}"
    assert isinstance(out.content, str)
    assert len(out.content.strip()) > 0
    print(out.content)
