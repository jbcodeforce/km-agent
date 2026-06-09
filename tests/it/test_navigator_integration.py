"""Integration test: Navigator agent with sandbox context (Ollama + Postgres + isolated knowledge tables).

Run explicitly:

    KMA_IT_NAVIGATOR=1 uv run pytest tests/it/test_navigator_integration.py -m integration -v

Requires Postgres (same as other IT), Ollama with a chat model, and embeddings per ``KMA_EMBED_PROVIDER``.

Environment:

- ``KMA_IT_NAVIGATOR`` — set to ``1`` to enable this module (otherwise skipped).
- ``LLM_HOST`` — Ollama base URL (default ``http://127.0.0.1:11434``).
- ``KMA_IT_OLLAMA_MODEL`` — optional; force a pulled model id for this suite.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from agno.models.ollama import OllamaResponses
from agno.run.base import RunStatus

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KMA_IT_NAVIGATOR") != "1",
        reason="set KMA_IT_NAVIGATOR=1 to run Navigator integration (Postgres + Ollama + embeddings)",
    ),
]


def _write_navigator_sandbox(root: Path) -> None:
    raw = root / "raw"
    wiki = root / "wiki"
    raw.mkdir(parents=True)
    wiki.mkdir(parents=True)
    index = """# Wiki Index

NavigatorIntegrationMarker

## Concepts
- (none — integration sandbox)
"""
    (wiki / "index.md").write_text(index, encoding="utf-8")
    manifest = [
        {
            "file": "nav-it-note.md",
            "title": "Nav IT Note",
            "source": "integration-test",
            "ingested": "2026-01-01T00:00:00Z",
            "compiled": False,
        }
    ]
    (raw / ".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


@pytest.mark.usefixtures("require_postgres", "ollama_embed_model_available")
def test_navigator_reads_wiki_and_manifest(
    ollama_model_id_for_integration: str,
    ollama_host: str,
    kma_knowledge_it,
    kma_learnings_it,
    tmp_path: Path,
) -> None:
    from kma.agents.navigator import build_navigator_agent

    sandbox = tmp_path / "ctx"
    _write_navigator_sandbox(sandbox)

    model = OllamaResponses(id=ollama_model_id_for_integration, host=ollama_host)
    agent = build_navigator_agent(
        model=model,
        knowledge=kma_knowledge_it,
        learnings=kma_learnings_it,
        context_dir=sandbox,
    )

    prompt = (
        "You are in an automated integration test. Use your tools only (no user questions).\n"
        "1) Call read_wiki_index.\n"
        "2) Call read_manifest.\n"
        "3) If the wiki index text contains the exact substring NavigatorIntegrationMarker "
        "and the manifest JSON includes the filename nav-it-note.md, your final line must be "
        "exactly: NAV_IT_OK\n"
        "Otherwise your final line must be exactly: NAV_IT_FAIL\n"
        "Keep the rest of the response short."
    )

    out = agent.run(prompt)
    if out.status != RunStatus.completed:
        msg = (out.content or "").lower()
        if "memory" in msg or "not found" in msg or "requires more" in msg or "timeout" in msg:
            pytest.skip(f"Navigator run infra issue: {out.content!r}")
    assert out.status == RunStatus.completed, f"navigator run failed: {out.content!r}"
    assert "NAV_IT_OK" in (out.content or ""), f"expected success token in: {out.content!r}"
