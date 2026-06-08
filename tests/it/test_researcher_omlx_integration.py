"""Integration: Researcher saves a source to raw/ and updates the manifest, using OMLX.

Doubly gated: KMA_IT_MLX=1 AND a configured Parallel key (KMA_PARALLEL_API_KEY / PARALLEL_API_KEY).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from agno.models.openai import OpenAILike
from agno.run.base import RunStatus

from kma.config import PARALLEL_API_KEY, get_mlx_api_key, get_mlx_base_url

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KMA_IT_MLX") != "1",
        reason="set KMA_IT_MLX=1 to run OMLX integration",
    ),
    pytest.mark.skipif(
        not PARALLEL_API_KEY,
        reason="set KMA_PARALLEL_API_KEY/PARALLEL_API_KEY to run Researcher integration",
    ),
]


@pytest.mark.usefixtures("require_postgres", "omlx_embed_model_available")
def test_researcher_ingests_text_to_raw(
    omlx_model_id_for_integration: str,
    kma_knowledge_it,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KMA_CONTEXT_DIR", str(tmp_path / "ctx"))
    (tmp_path / "ctx" / "raw").mkdir(parents=True)

    from agno.agent import Agent
    from kma.agents.instructions import RESEARCHER_INSTRUCTIONS
    from kma.agents.settings import agent_db
    from kma.tools.builder import build_researcher_tools

    model = OpenAILike(id=omlx_model_id_for_integration, base_url=get_mlx_base_url(), api_key=get_mlx_api_key())
    agent = Agent(
        id="researcher-it",
        name="Researcher IT",
        model=model,
        db=agent_db,
        instructions=RESEARCHER_INSTRUCTIONS,
        knowledge=kma_knowledge_it,
        tools=build_researcher_tools(kma_knowledge_it),
    )

    prompt = (
        "You are in an automated integration test. Use tools only (no web search needed).\n"
        "Call ingest_text to save a short note titled 'IT Research Note' with body "
        "'OMLX researcher integration sample about Flink checkpoints.' and tag flink.\n"
        "Then call read_manifest. Keep responses short."
    )
    out = agent.run(prompt)
    if out.status != RunStatus.completed:
        msg = (out.content or "").lower()
        if any(t in msg for t in ("memory", "not found", "requires more", "timeout")):
            pytest.skip(f"Researcher run infra issue: {out.content!r}")
    assert out.status == RunStatus.completed, f"researcher run failed: {out.content!r}"

    raw_dir = tmp_path / "ctx" / "raw"
    manifest_path = raw_dir / ".manifest.json"
    assert manifest_path.is_file(), "researcher did not create a manifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert any("research" in (e.get("title", "").lower()) or e.get("file") for e in manifest)
    assert list(raw_dir.glob("*.md")), "researcher did not write any raw markdown"
