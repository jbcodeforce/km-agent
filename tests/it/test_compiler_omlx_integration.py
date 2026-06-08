"""Integration: Compiler compiles real flink-studies raw docs into the wiki, using OMLX.

Run:
    KMA_IT_MLX=1 KMA_LLM_PROVIDER=mlx KMA_EMBED_PROVIDER=mlx \
    KMA_EMBED_MODEL=<id> KMA_EMBED_DIMENSIONS=<n> \
    uv run pytest tests/it/test_compiler_omlx_integration.py -m integration -v
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from agno.models.openai import OpenAILike
from agno.run.base import RunStatus
from agno.run.agent import RunOutput

from kma.config import get_mlx_api_key, get_mlx_base_url
from kma.tools.ingest import sync_manifest_from_raw_markdown

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KMA_IT_MLX") != "1",
        reason="set KMA_IT_MLX=1 to run OMLX integration (OMLX + Postgres + embeddings)",
    ),
]

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


@pytest.mark.usefixtures("require_postgres", "omlx_embed_model_available")
def test_compiler_compiles_flink_studies_doc(
    omlx_model_id_for_integration: str,
    omlx_base_url: str,
    kma_knowledge_it,
    tmp_path: Path,
) -> None:
    from kma.agents.compiler import build_compiler_agent

    sandbox = tmp_path / "ctx"
    (sandbox / "raw").mkdir(parents=True)
    (sandbox / "wiki").mkdir(parents=True)
    target = "kafka.md"
    shutil.copy(DATA_RAW / target, sandbox / "raw" / target)
    sync_manifest_from_raw_markdown(sandbox / "raw")

    model = OpenAILike(
        id=omlx_model_id_for_integration,
        base_url=get_mlx_base_url(),
        api_key=get_mlx_api_key(),
    )
    agent = build_compiler_agent(context_dir=sandbox, knowledge=kma_knowledge_it, model=model)

    prompt = (
        "You are in an automated integration test. Use your tools only (no user questions).\n"
        "1) Call read_manifest.\n"
        f"2) Read raw/{target} via read_file.\n"
        f"3) Write wiki/summaries/{target} with a short markdown summary (heading + >=2 sentences).\n"
        "4) Create one file under wiki/concepts/ with a short slug name describing a key topic.\n"
        f"5) Call update_manifest_compiled with filename {target}.\n"
        "6) Call update_wiki_index listing the new concept under ## Concepts with paths starting wiki/.\n"
        "7) Call update_wiki_state with mark_compiled true and article_count at least 1.\n"
        "Keep responses short; complete the workflow."
    )

    final: RunOutput | None = None
    for chunk in agent.run(prompt, stream=True, stream_events=True, yield_run_output=True):
        if isinstance(chunk, RunOutput):
            final = chunk
    assert final is not None
    if final.status != RunStatus.completed:
        msg = (final.content or "").lower()
        if any(t in msg for t in ("memory", "not found", "requires more", "timeout")):
            pytest.skip(f"Compiler run infra issue: {final.content!r}")
    assert final.status == RunStatus.completed, f"compiler run failed: {final.content!r}"

    manifest = json.loads((sandbox / "raw" / ".manifest.json").read_text(encoding="utf-8"))
    entry = next((e for e in manifest if e.get("file") == target), None)
    assert entry is not None and entry.get("compiled") is True

    assert (sandbox / "wiki" / "summaries" / target).is_file()
    assert list((sandbox / "wiki" / "concepts").glob("*.md"))
    idx = (sandbox / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "wiki/concepts" in idx
