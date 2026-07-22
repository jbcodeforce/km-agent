"""Unit tests for enrichment workflow helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from agno.run.base import RunStatus
from agno.run.agent import RunOutput

from kma.tools.site_refs import WebSiteRef
from kma.workflows.enrichment import (
    build_research_prompt,
    new_uncompiled_file_ids,
    run_search_pipeline,
    snapshot_manifest_files,
)


def test_build_research_prompt_includes_query_and_sites() -> None:
    refs = [WebSiteRef("Site", "https://site.test", "Notes")]
    prompt = build_research_prompt("compare flink versions", refs)
    assert "compare flink versions" in prompt
    assert "Site" in prompt
    assert "https://site.test" in prompt


def test_snapshot_and_new_uncompiled_file_ids(tmp_path: Path) -> None:
    ctx = tmp_path
    (ctx / "raw").mkdir()
    manifest = [
        {"file_id": "ingested:old.md", "file": "old.md", "compiled": True},
        {"file_id": "ingested:pending.md", "file": "pending.md", "compiled": False},
    ]
    (ctx / ".manifest.json").write_text(json.dumps(manifest))
    before = snapshot_manifest_files(ctx)
    assert before == {"ingested:old.md", "ingested:pending.md"}

    manifest.append({"file_id": "ingested:new.md", "file": "new.md", "compiled": False})
    (ctx / ".manifest.json").write_text(json.dumps(manifest))
    added = new_uncompiled_file_ids(ctx, before)
    assert added == ["ingested:new.md"]


def test_new_uncompiled_falls_back_to_all_uncompiled(tmp_path: Path) -> None:
    ctx = tmp_path
    (ctx / "raw").mkdir()
    manifest = [{"file_id": "ingested:a.md", "file": "a.md", "compiled": False}]
    (ctx / ".manifest.json").write_text(json.dumps(manifest))
    before = snapshot_manifest_files(ctx)
    assert new_uncompiled_file_ids(ctx, before) == ["ingested:a.md"]


def test_run_search_pipeline_skip_research_calls_compile(monkeypatch, tmp_path: Path) -> None:
    ctx = tmp_path
    (ctx / "raw").mkdir()
    (ctx / ".manifest.json").write_text(
        json.dumps([{"file_id": "ingested:topic.md", "file": "topic.md", "compiled": False}])
    )
    compile_calls: list[list[str]] = []

    monkeypatch.setattr(
        "kma.workflows.enrichment.compile_raw_files",
        lambda c, ids: compile_calls.append(list(ids)) or ids,
    )
    monkeypatch.setattr("kma.workflows.enrichment.run_linter", lambda c: True)

    result = run_search_pipeline(
        "ignored",
        ctx,
        skip_research=True,
        skip_lint=False,
    )
    assert result.research_status == "skipped"
    assert result.ingested_file_ids == ["ingested:topic.md"]
    assert compile_calls == [["ingested:topic.md"]]
    assert result.linter_ok is True


def test_run_search_pipeline_research_only(monkeypatch, tmp_path: Path) -> None:
    ctx = tmp_path
    (ctx / "raw").mkdir()
    (ctx / ".manifest.json").write_text("[]")

    mock_out = RunOutput(status=RunStatus.completed, content="done")

    def fake_research_step(query, c, **kwargs):
        manifest = [{"file_id": "ingested:fresh.md", "file": "fresh.md", "compiled": False}]
        (ctx / ".manifest.json").write_text(json.dumps(manifest))
        return mock_out, ["ingested:fresh.md"]

    monkeypatch.setattr("kma.workflows.enrichment.run_research_step", fake_research_step)

    result = run_search_pipeline("topic", ctx, skip_compile=True)
    assert result.research_status == "completed"
    assert result.ingested_file_ids == ["ingested:fresh.md"]
    assert result.compiled_file_ids == []
    assert result.linter_ok is None
