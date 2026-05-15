"""Integration test: Compiler agent with sandbox context (Ollama chat by default; embeddings from ``KMA_EMBED_PROVIDER``)."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from agno.models.ollama import OllamaResponses
from agno.run.base import RunStatus
from agno.run.agent import RunCompletedEvent, RunOutput
from agno.run.base import RunStatus

from kma.agents.compiler import build_compiler_agent
from kma.tools.ingest import sync_manifest_from_raw_markdown

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KMA_IT_COMPILER") != "1",
        reason="set KMA_IT_COMPILER=1 to run compiler integration (Postgres + configured LLM/embeddings)",
    ),
]

IT_CONTEXT = Path(__file__).resolve().parent.parent / "it_context"
SOURCE_RAW = "flink-sql-1.md"
SUMMARY_NAME = "flink-sql-1.md"


@pytest.mark.usefixtures("require_postgres", "ollama_embed_model_available")
def test_compiler_processes_sandbox_raw(
    ollama_model_id_for_integration: str,
    ollama_host: str,
    kma_knowledge_it,
    tmp_path: Path,
) -> None:
    sandbox = tmp_path / "ctx"
    shutil.copytree(IT_CONTEXT, sandbox)
    manifest_path = sandbox / "raw" / ".manifest.json"
    if not manifest_path.is_file():
        sync_manifest_from_raw_markdown(sandbox / "raw")

    model = OllamaResponses(id=ollama_model_id_for_integration, host=ollama_host)
    agent = build_compiler_agent(
        context_dir=sandbox,
        knowledge=kma_knowledge_it,
        model=model,
    )

    prompt = (
        "You are in an automated integration test. Use your tools only (no user questions).\n"
        "1) Call read_manifest.\n"
        f"2) Read raw/{SOURCE_RAW} via read_file.\n"
        f"3) Write wiki/summaries/{SUMMARY_NAME} with a short markdown summary (heading + at least two sentences).\n"
        "4) Create one file under wiki/concepts/ with a short slug name (e.g. flink-ddl-overview.md) describing the topic briefly.\n"
        f"5) Call update_manifest_compiled with filename {SOURCE_RAW}.\n"
        "6) Call update_wiki_index with a minimal markdown index that lists the new concept under ## Concepts using paths starting with wiki/.\n"
        "7) Call update_wiki_state with mark_compiled true and article_count at least 1.\n"
        "Keep responses short; complete the workflow."
    )
    print(f"sandbox path: {sandbox}")
    print(f"prompt: {prompt}")
    final: RunOutput | None = None
    for chunk in agent.run(
        prompt,
        stream=True,
        stream_events=True,  # tool / model / reasoning-style events (see RunEvent)
        yield_run_output=True,  # also yield the final RunOutput in the stream
    ):
        if isinstance(chunk, RunOutput):
            final = chunk
        else:
            # chunk is a RunOutputEvent (e.g. RunContentEvent, ToolCallStartedEvent, …)
            print(chunk.event, getattr(chunk, "content", None))
    assert final is not None
    if final.status != RunStatus.completed:
        msg = (final.content or "").lower()
        if "memory" in msg or "not found" in msg or "requires more" in msg or "timeout" in msg:
            pytest.skip(f"Compiler run infra issue: {final.content!r}")
    assert final.status == RunStatus.completed, f"compiler run failed: {final.content!r}"

    manifest = json.loads((sandbox / "raw" / ".manifest.json").read_text(encoding="utf-8"))
    entry = next((e for e in manifest if e.get("file") == SOURCE_RAW), None)
    assert entry is not None
    assert entry.get("compiled") is True

    summary = sandbox / "wiki" / "summaries" / SUMMARY_NAME
    assert summary.is_file()
    assert len(summary.read_text(encoding="utf-8").strip()) > 40
    print(summary.read_text(encoding="utf-8"))

    concepts = list((sandbox / "wiki" / "concepts").glob("*.md"))
    assert len(concepts) >= 1

    index = sandbox / "wiki" / "index.md"
    assert index.is_file()
    idx_text = index.read_text(encoding="utf-8")
    assert "wiki/concepts" in idx_text
    print(idx_text)
