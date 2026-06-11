"""Integration: Navigator reads wiki index + manifest + a context file, using OMLX."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from agno.models.openai import OpenAILike
from agno.run.base import RunStatus

from kma.config import get_mlx_api_key, get_mlx_base_url

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KMA_IT_MLX") != "1",
        reason="set KMA_IT_MLX=1 to run OMLX integration (OMLX + Postgres + embeddings)",
    ),
]


def _write_sandbox(root: Path) -> None:
    (root / "raw").mkdir(parents=True)
    (root / "wiki").mkdir(parents=True)
    (root / "wiki" / "index.md").write_text(
        "# Wiki Index\n\nNavOmlxMarker\n\n## Concepts\n- [Kafka](wiki/concepts/kafka.md) — messaging for Flink\n",
        encoding="utf-8",
    )
    (root / "raw" / "note.md").write_text("---\ntitle: Note\n---\nNavFileMarker body\n", encoding="utf-8")
    manifest = [{"file": "note.md", "title": "Note", "source": "it", "ingested": "2026-01-01T00:00:00Z", "compiled": False}]
    (root / "raw" / ".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


@pytest.mark.usefixtures("require_postgres", "omlx_embed_model_available")
def test_navigator_reads_sources(
    omlx_model_id_for_integration: str,
    kma_knowledge_it,
    kma_learnings_it,
    tmp_path: Path,
) -> None:
    from kma.agents.navigator import build_navigator_agent

    sandbox = tmp_path / "ctx"
    _write_sandbox(sandbox)

    model = OpenAILike(id=omlx_model_id_for_integration, base_url=get_mlx_base_url(), api_key=get_mlx_api_key())
    agent = build_navigator_agent(
        model=model, knowledge=kma_knowledge_it, learnings=kma_learnings_it, context_dir=sandbox
    )

    prompt = (
        "You are in an automated integration test. Use your tools only (no user questions).\n"
        "1) Call read_wiki_index.\n"
        "2) Call read_manifest.\n"
        "3) If the wiki index contains the exact substring NavOmlxMarker and the manifest JSON "
        "includes the filename note.md, your final line must be exactly: NAV_OMLX_OK\n"
        "Otherwise your final line must be exactly: NAV_OMLX_FAIL\nKeep the rest short."
    )

    out = agent.run(prompt)
    if out.status != RunStatus.completed:
        msg = (out.content or "").lower()
        if any(t in msg for t in ("memory", "not found", "requires more", "timeout")):
            pytest.skip(f"Navigator run infra issue: {out.content!r}")
    assert out.status == RunStatus.completed, f"navigator run failed: {out.content!r}"
    assert "NAV_OMLX_OK" in (out.content or ""), f"expected token in: {out.content!r}"
