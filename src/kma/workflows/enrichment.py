"""Research → compile → lint pipeline (CLI and programmatic entry)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from agno.run.agent import RunOutput
from agno.run.base import RunStatus

from kma.agents.researcher import build_researcher_agent
from kma.tools.ingest import _read_manifest, list_uncompiled_file_ids
from kma.tools.site_refs import (
    WebSiteRef,
    format_site_refs_for_prompt,
    load_site_refs_for_context,
)
from kma.workflows.wiki_refresh import compile_raw_files, run_linter

logger = logging.getLogger(__name__)


@dataclass
class RunSearchResult:
    """Outcome of ``run_search_pipeline``."""

    research_status: str
    ingested_file_ids: list[str] = field(default_factory=list)
    compiled_file_ids: list[str] = field(default_factory=list)
    linter_ok: bool | None = None


def build_research_prompt(query: str, site_refs: list[WebSiteRef] | None) -> str:
    """Build the user task for the Researcher agent."""
    parts = [
        query.strip(),
        "",
        "Research this topic, ingest findings to raw/ with proper YAML frontmatter and tags.",
        "List every new manifest file name you create at the end of your response.",
    ]
    site_section = format_site_refs_for_prompt(site_refs or [])
    if site_section:
        parts.extend(["", site_section])
    return "\n".join(parts)


def snapshot_manifest_files(raw_dir: Path) -> set[str]:
    """Return manifest ``file`` values currently tracked under ``raw_dir``."""
    return {str(entry.get("file", "")).strip() for entry in _read_manifest(raw_dir) if entry.get("file")}


def new_uncompiled_file_ids(raw_dir: Path, before: set[str]) -> list[str]:
    """Return newly added uncompiled manifest entries; fall back to all uncompiled."""
    added: list[str] = []
    for entry in _read_manifest(raw_dir):
        rel = str(entry.get("file", "")).strip()
        if not rel or entry.get("compiled"):
            continue
        if rel not in before:
            added.append(rel)
    if added:
        return added
    return list_uncompiled_file_ids(raw_dir)


def run_research_step(
    query: str,
    context_dir: Path,
    *,
    site_refs_path: Path | None = None,
) -> tuple[RunOutput | None, list[str]]:
    """Run the Researcher agent; return final output and new raw file ids."""
    ctx = context_dir.resolve()
    raw_dir = ctx / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    agent = build_researcher_agent(context_dir=ctx)

    site_refs = load_site_refs_for_context(ctx, site_refs_path)
    prompt = build_research_prompt(query, site_refs or None)
    before = snapshot_manifest_files(raw_dir)

    final: RunOutput | None = None
    for chunk in agent.run(prompt, stream=True, yield_run_output=True):
        if isinstance(chunk, RunOutput):
            final = chunk

    file_ids = new_uncompiled_file_ids(raw_dir, before)
    return final, file_ids


def run_search_pipeline(
    query: str,
    context_dir: Path,
    *,
    site_refs_path: Path | None = None,
    skip_research: bool = False,
    skip_compile: bool = False,
    skip_lint: bool = False,
) -> RunSearchResult:
    """Run research, then synchronously compile and lint ingested raw files."""
    ctx = context_dir.resolve()
    raw_dir = ctx / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    research_status = "skipped"
    file_ids: list[str] = []

    if not skip_research:
        final, file_ids = run_research_step(query, ctx, site_refs_path=site_refs_path)
        if final is None:
            research_status = "no_output"
        elif final.status == RunStatus.completed:
            research_status = "completed"
        else:
            research_status = f"failed:{final.status}"
            msg = (final.content or "").lower()
            if any(k in msg for k in ("memory", "not found", "requires more", "timeout")):
                logger.warning("researcher run infra issue: %s", final.content)
    else:
        file_ids = list_uncompiled_file_ids(raw_dir)

    compiled: list[str] = []
    linter_ok: bool | None = None

    if skip_compile:
        return RunSearchResult(
            research_status=research_status,
            ingested_file_ids=file_ids,
            compiled_file_ids=compiled,
            linter_ok=None,
        )

    if not file_ids:
        logger.info("no uncompiled raw files to compile")
        return RunSearchResult(
            research_status=research_status,
            ingested_file_ids=[],
            compiled_file_ids=[],
            linter_ok=None if skip_lint else True,
        )

    compiled = compile_raw_files(ctx, file_ids)
    linter_ok: bool | None = None
    if not skip_lint:
        linter_ok = run_linter(ctx)

    return RunSearchResult(
        research_status=research_status,
        ingested_file_ids=file_ids,
        compiled_file_ids=compiled,
        linter_ok=linter_ok,
    )
