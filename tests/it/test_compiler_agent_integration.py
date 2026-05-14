"""Integration test: Compiler agent with sandbox context (Ollama chat by default; embeddings from ``KMA_EMBED_PROVIDER``)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from agno.models.ollama import OllamaResponses
from agno.run.base import RunStatus

from kma.agents.compiler import build_compiler_agent

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KMA_IT_COMPILER") != "1",
        reason="set KMA_IT_COMPILER=1 to run compiler integration (Postgres + configured LLM/embeddings)",
    ),
]


def _write_compiler_sandbox(root: Path) -> None:
    raw = root / "raw"
    wiki = root / "wiki"
    raw.mkdir(parents=True)
    wiki.mkdir(parents=True)
    (wiki / "summaries").mkdir(parents=True)
    (wiki / "concepts").mkdir(parents=True)
    body = """---
title: "IT Note"
source: integration-test
ingested: 2026-01-01
tags: [it]
type: notes
compiled: false
---

# IT Note

This note states that cats nap often and dogs enjoy walks. It exists only to exercise the compiler pipeline.
"""
    (raw / "it-note.md").write_text(body, encoding="utf-8")
    manifest = [
        {
            "file": "it-note.md",
            "title": "IT Note",
            "source": "integration-test",
            "ingested": "2026-01-01T00:00:00Z",
            "compiled": False,
        }
    ]
    (raw / ".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


@pytest.mark.usefixtures("require_postgres", "ollama_embed_model_available")
def test_compiler_processes_sandbox_raw(
    ollama_model_id_for_integration: str,
    ollama_host: str,
    kma_knowledge_it,
    tmp_path: Path,
) -> None:
    sandbox = tmp_path / "ctx"
    _write_compiler_sandbox(sandbox)

    model = OllamaResponses(id=ollama_model_id_for_integration, host=ollama_host)
    agent = build_compiler_agent(
        context_dir=sandbox,
        knowledge=kma_knowledge_it,
        model=model,
    )

    prompt = (
        "You are in an automated integration test. Use your tools only (no user questions).\n"
        "1) Call read_manifest.\n"
        "2) Read raw/it-note.md via read_file.\n"
        "3) Write wiki/summaries/it-note.md with a short markdown summary (heading + at least two sentences).\n"
        "4) Create one file under wiki/concepts/ with a short slug name (e.g. pets-note.md) describing the topic briefly.\n"
        "5) Call update_manifest_compiled with filename it-note.md.\n"
        "6) Call update_wiki_index with a minimal markdown index that lists the new concept under ## Concepts using paths starting with wiki/.\n"
        "7) Call update_wiki_state with mark_compiled true and article_count at least 1.\n"
        "Keep responses short; complete the workflow."
    )

    out = agent.run(prompt)
    if out.status != RunStatus.completed:
        msg = (out.content or "").lower()
        if "memory" in msg or "not found" in msg or "requires more" in msg or "timeout" in msg:
            pytest.skip(f"Compiler run infra issue: {out.content!r}")
    assert out.status == RunStatus.completed, f"compiler run failed: {out.content!r}"

    manifest = json.loads((sandbox / "raw" / ".manifest.json").read_text(encoding="utf-8"))
    entry = next((e for e in manifest if e.get("file") == "it-note.md"), None)
    assert entry is not None
    assert entry.get("compiled") is True

    summary = sandbox / "wiki" / "summaries" / "it-note.md"
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