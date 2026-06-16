"""Unit tests for enrichment workflow helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
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
    raw = tmp_path / "raw"
    raw.mkdir()
    manifest = [
        {"file": "old.md", "compiled": True},
        {"file": "pending.md", "compiled": False},
    ]
    (raw / ".manifest.json").write_text(json.dumps(manifest))
    before = snapshot_manifest_files(raw)
    assert before == {"old.md", "pending.md"}

    manifest.append({"file": "new.md", "compiled": False})
    (raw / ".manifest.json").write_text(json.dumps(manifest))
    added = new_uncompiled_file_ids(raw, before)
    assert added == ["new.md"]


def test_new_uncompiled_falls_back_to_all_uncompiled(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    manifest = [{"file": "a.md", "compiled": False}]
    (raw / ".manifest.json").write_text(json.dumps(manifest))
    before = snapshot_manifest_files(raw)
    assert new_uncompiled_file_ids(raw, before) == ["a.md"]


def test_run_search_pipeline_skip_research_calls_compile(monkeypatch, tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / ".manifest.json").write_text(
        json.dumps([{"file": "topic.md", "compiled": False}])
    )
    compile_calls: list[list[str]] = []

    monkeypatch.setattr(
        "kma.workflows.enrichment.compile_raw_files",
        lambda ctx, ids: compile_calls.append(list(ids)) or ids,
    )
    monkeypatch.setattr("kma.workflows.enrichment.run_linter", lambda ctx: True)

    result = run_search_pipeline(
        "ignored",
        tmp_path,
        skip_research=True,
        skip_lint=False,
    )
    assert result.research_status == "skipped"
    assert result.ingested_file_ids == ["topic.md"]
    assert compile_calls == [["topic.md"]]
    assert result.linter_ok is True


def test_run_search_pipeline_research_only(monkeypatch, tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / ".manifest.json").write_text("[]")

    mock_agent = MagicMock()
    mock_out = RunOutput(status=RunStatus.completed, content="done")
    mock_agent.run.return_value = iter([mock_out])

    def fake_research_step(query, ctx, **kwargs):
        manifest = [{"file": "fresh.md", "compiled": False}]
        (raw / ".manifest.json").write_text(json.dumps(manifest))
        return mock_out, ["fresh.md"]

    monkeypatch.setattr("kma.workflows.enrichment.get_parallel_api_key", lambda: "test-key")
    monkeypatch.setattr("kma.workflows.enrichment.run_research_step", fake_research_step)

    result = run_search_pipeline("topic", tmp_path, skip_compile=True)
    assert result.research_status == "completed"
    assert result.ingested_file_ids == ["fresh.md"]
    assert result.compiled_file_ids == []
    assert result.linter_ok is None


def test_run_search_pipeline_requires_parallel_when_researching(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("kma.workflows.enrichment.get_parallel_api_key", lambda: None)
    with pytest.raises(RuntimeError, match="Parallel"):
        run_search_pipeline("topic", tmp_path)
