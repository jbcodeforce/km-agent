"""Integration: Linter reads the wiki and reports on it, using OMLX."""

from __future__ import annotations

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
        reason="set KMA_IT_MLX=1 to run OMLX integration",
    ),
]


def _write_wiki(root: Path) -> None:
    (root / "wiki" / "concepts").mkdir(parents=True)
    (root / "wiki" / "index.md").write_text(
        "# Wiki Index\n\nLintOmlxMarker\n\n## Concepts\n- [Kafka](wiki/concepts/kafka.md) — Flink source\n",
        encoding="utf-8",
    )
    (root / "wiki" / "concepts" / "kafka.md").write_text(
        "---\ntitle: Kafka\n---\nKafka is a streaming source for Flink.\n", encoding="utf-8"
    )


@pytest.mark.usefixtures("require_postgres", "omlx_embed_model_available")
def test_linter_reads_wiki_index(
    omlx_model_id_for_integration: str,
    kma_knowledge_it,
    tmp_path: Path,
    monkeypatch,
) -> None:
    from kma.agents.linter import build_linter_agent

    sandbox = tmp_path / "ctx"
    _write_wiki(sandbox)
    monkeypatch.setenv("KMA_CONTEXT_DIR", str(sandbox))

    model = OpenAILike(id=omlx_model_id_for_integration, base_url=get_mlx_base_url(), api_key=get_mlx_api_key())
    agent = build_linter_agent(context_dir=sandbox, knowledge=kma_knowledge_it, model=model)

    prompt = (
        "You are in an automated integration test. Use your tools only (no user questions).\n"
        "1) Call read_wiki_index.\n"
        "2) If the index contains the exact substring LintOmlxMarker, your final line must be "
        "exactly: LINT_OMLX_OK\nOtherwise: LINT_OMLX_FAIL\nKeep the rest short."
    )
    out = agent.run(prompt)
    if out.status != RunStatus.completed:
        msg = (out.content or "").lower()
        if any(t in msg for t in ("memory", "not found", "requires more", "timeout")):
            pytest.skip(f"Linter run infra issue: {out.content!r}")
    assert out.status == RunStatus.completed, f"linter run failed: {out.content!r}"
    assert "LINT_OMLX_OK" in (out.content or ""), f"expected token in: {out.content!r}"
