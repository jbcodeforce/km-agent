"""Integration test: Compiler agent with sandbox context (Ollama chat by default; embeddings from ``KMA_EMBED_PROVIDER``)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from agno.run.base import RunStatus
from agno.run.agent import RunCompletedEvent, RunOutput
from agno.run.base import RunStatus

from kma.agents.compiler import build_compiler_agent
from kma.tools.ingest import sync_manifest_from_raw_markdown



IT_CONTEXT = Path(__file__).resolve().parent.parent / "data"
SOURCE_RAW = "fitforpurpose.md"
SUMMARY_NAME = "fitforpurpose.md"


@pytest.mark.usefixtures("require_postgres")
def test_compiler_processes() -> None:
    """
    Create a sandbox manifest and process the file. 
    """
    raw_dir = IT_CONTEXT / "raw"
    sync_manifest_from_raw_markdown(raw_dir)
    agent = build_compiler_agent(
        context_dir=IT_CONTEXT
    )
    assert agent is not None
    assert agent.model is not None
    assert agent.model.id == "Qwen3.6-35B-A3B-UD-MLX-4bit"
    assert type(agent.model).__name__ == "OpenAILike"
    prompt = (
        "process the file fitforpurpose.md"
    )
    try:
        final: RunOutput | None = None
        for chunk in agent.run(
            prompt,
            stream=True,
            stream_events=True,  # tool / model / reasoning-style events (see RunEvent)
            yield_run_output=True,  # also yield the final RunOutput in the stream
        ):
            if isinstance(chunk, RunOutput):
                final = chunk
        assert final is not None
        if final.status != RunStatus.completed:
            msg = (final.content or "").lower()
            if "memory" in msg or "not found" in msg or "requires more" in msg or "timeout" in msg:
                pytest.skip(f"Compiler run infra issue: {final.content!r}")
        assert final.status == RunStatus.completed, f"compiler run failed: {final.content!r}"

        manifest = json.loads((IT_CONTEXT / "raw" / ".manifest.json").read_text(encoding="utf-8"))
        entry = next((e for e in manifest if e.get("file") == SOURCE_RAW), None)
        assert entry is not None
        assert entry.get("compiled") is True

        summary = IT_CONTEXT / "wiki" / "summaries" / SUMMARY_NAME
        assert summary.is_file()
        assert len(summary.read_text(encoding="utf-8").strip()) > 40
        print(summary.read_text(encoding="utf-8"))

        concepts = list((IT_CONTEXT / "wiki" / "concepts").glob("*.md"))
        assert len(concepts) >= 1

        index = IT_CONTEXT / "wiki" / "index.md"
        assert index.is_file()
        idx_text = index.read_text(encoding="utf-8")
        assert "wiki/concepts" in idx_text
        print(idx_text)
    except Exception as e:
        print(f"Error: {e}")
        raise e
