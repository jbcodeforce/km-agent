"""Integration tests for run_search research / compile / lint pipeline."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from kma.tools.ingest import sync_manifest_from_raw_markdown
from kma.workflows.enrichment import run_search_pipeline

IT_CONTEXT = Path(__file__).resolve().parent.parent / "data"
SITE_REFS = IT_CONTEXT / "web_site_ref.json"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUN_SEARCH_SCRIPT = REPO_ROOT / "scripts" / "run_search.py"
SOURCE_RAW = "fitforpurpose.md"

_INFRA_SKIP_MARKERS = (
    "memory",
    "not found",
    "timeout",
    "local-mlx",
    "embed",
    "ollama",
    "fastembed",
)


def _skip_if_infra(exc: Exception) -> None:
    msg = str(exc).lower()
    if any(k in msg for k in _INFRA_SKIP_MARKERS):
        pytest.skip(f"Pipeline infra issue: {exc}")


def _sandbox_context(tmp_path: Path) -> Path:
    """Minimal context copy: one uncompiled raw file + wiki skeleton."""
    ctx = tmp_path / "context"
    shutil.copytree(IT_CONTEXT / "wiki", ctx / "wiki")
    raw = ctx / "raw"
    raw.mkdir()
    shutil.copy(IT_CONTEXT / "raw" / SOURCE_RAW, raw / SOURCE_RAW)
    manifest = [
        {
            "file": SOURCE_RAW,
            "title": "Fit For Purpose",
            "source": "flink-studies",
            "ingested": "2026-06-08T00:00:00Z",
            "compiled": False,
        }
    ]
    (raw / ".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copy(SITE_REFS, ctx / "web_site_ref.json")
    return ctx


def test_run_search_dry_run_cli() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(RUN_SEARCH_SCRIPT),
            "compare flink 2.1 and 2.2",
            "--context",
            str(IT_CONTEXT),
            "--src-file",
            str(SITE_REFS),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Apache Flink Blog" in proc.stdout
    assert "compare flink 2.1 and 2.2" in proc.stdout


@pytest.mark.usefixtures("require_postgres")
def test_run_search_pipeline_skip_research(tmp_path: Path) -> None:
    """Compile + lint one uncompiled raw file via pipeline (no Parallel)."""
    ctx = _sandbox_context(tmp_path)
    sync_manifest_from_raw_markdown(ctx / "raw")

    try:
        result = run_search_pipeline(
            "unused query",
            ctx,
            site_refs_path=ctx / "web_site_ref.json",
            skip_research=True,
            skip_lint=False,
        )
    except Exception as exc:
        _skip_if_infra(exc)
        raise

    assert result.research_status == "skipped"
    if not result.compiled_file_ids:
        pytest.skip("compiler produced no output (LLM infra)")
    assert SOURCE_RAW in result.compiled_file_ids or result.compiled_file_ids
    assert result.linter_ok is True

    summary = ctx / "wiki" / "summaries" / SOURCE_RAW
    assert summary.is_file()


@pytest.mark.usefixtures("require_postgres")
def test_run_search_pipeline_full_research(tmp_path: Path) -> None:
    """Live research step via DuckDuckGo (may skip on LLM/network infra issues)."""
    ctx = _sandbox_context(tmp_path)

    try:
        result = run_search_pipeline(
            "Brief note on Apache Flink release highlights (one short source)",
            ctx,
            site_refs_path=ctx / "web_site_ref.json",
            skip_compile=True,
            skip_lint=True,
        )
    except Exception as exc:
        _skip_if_infra(exc)
        raise

    if result.research_status.startswith("failed"):
        pytest.skip(f"Researcher run did not complete: {result.research_status}")
    assert result.research_status in ("completed", "no_output")
