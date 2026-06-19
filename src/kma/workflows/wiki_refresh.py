"""Compile raw sources into wiki/ and run the linter (shared by scripts and background jobs)."""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from agno.run.base import RunStatus

from kma.agents.compiler import build_compile_file_prompt, build_compiler_agent
from kma.agents.linter import build_lint_prompt, build_linter_agent
from kma.agents.settings import get_kma_knowledge
from kma.config import (
    get_kma_studies_root,
    kma_ontology_enabled,
    kma_ontology_enrich_enabled,
)
from kma.tools.ingest import manifest_entry_compiled, mark_manifest_compiled

logger = logging.getLogger(__name__)


def _ensure_wiki_dirs(context_dir: Path) -> None:
    wiki = context_dir / "wiki"
    (wiki / "summaries").mkdir(parents=True, exist_ok=True)
    (wiki / "concepts").mkdir(parents=True, exist_ok=True)
    (context_dir / "raw").mkdir(parents=True, exist_ok=True)


def _resolve_file_id(
    file_id: str,
    raw_roots: Sequence[tuple[str, Path]],
    default_raw: Path,
) -> tuple[Path, str, str]:
    """Return (raw_dir, manifest_rel, compile_file_id)."""
    key = file_id.strip()
    if ":" in key:
        label, rel = key.split(":", 1)
        raw_home = next((r for lab, r in raw_roots if lab == label), None)
        if raw_home is None:
            raise ValueError(f"Unknown raw root label in file_id: {key}")
        return raw_home, rel, key
    return default_raw, key, key


def compile_raw_files(
    context_dir: Path,
    file_ids: list[str],
    *,
    raw_roots: Sequence[tuple[str, Path]] | None = None,
) -> list[str]:
    """Run the compiler agent once per ``file_id``; return successfully compiled ids."""
    ctx = context_dir.resolve()
    if not file_ids:
        return []

    _ensure_wiki_dirs(ctx)
    ingested_root = ctx / "raw"
    roots: list[tuple[str, Path]] = (
        [(str(lab), Path(path).resolve()) for lab, path in raw_roots]
        if raw_roots is not None
        else [("ingested", ingested_root)]
    )

    compiler_agent = build_compiler_agent(
        context_dir=ctx,
        raw_roots=roots,
        knowledge=get_kma_knowledge(),
    )

    compiled: list[str] = []
    for file_id in file_ids:
        key = file_id.strip()
        if not key:
            continue
        try:
            raw_home, rel, compile_id = _resolve_file_id(key, roots, ingested_root)
        except ValueError as e:
            logger.error("%s", e)
            continue

        if manifest_entry_compiled(raw_home, rel):
            logger.info("skip already compiled: %s", compile_id)
            compiled.append(compile_id)
            continue

        logger.info("compiling raw file: %s", compile_id)
        prompt = build_compile_file_prompt(compile_id, automated=True)
        out = compiler_agent.run(prompt)
        if out.status != RunStatus.completed:
            logger.error("compiler run failed for %s: %s %r", compile_id, out.status, out.content)
            print(f"compiler run failed for {compile_id}: {out.status}", file=sys.stderr)
            continue

        if not mark_manifest_compiled(raw_home, rel):
            logger.warning("manifest entry not found after compile: %s", compile_id)
        compiled.append(compile_id)
        logger.info("compiled: %s", compile_id)

    return compiled


def run_linter(context_dir: Path) -> bool:
    """Run the linter agent. Returns True on success."""
    ctx = context_dir.resolve()
    _ensure_wiki_dirs(ctx)
    linter_agent = build_linter_agent(context_dir=ctx, knowledge=get_kma_knowledge())
    logger.info("running wiki linter")
    lint_out = linter_agent.run(build_lint_prompt(automated=True))
    if lint_out.status != RunStatus.completed:
        logger.error("linter run failed: %s %r", lint_out.status, lint_out.content)
        print(f"linter run failed: {lint_out.status}", file=sys.stderr)
        return False
    logger.info("linter run completed")
    return True


def refresh_wiki_from_raw(
    context_dir: Path,
    file_ids: list[str],
    *,
    raw_roots: Sequence[tuple[str, Path]] | None = None,
    skip_linter: bool = False,
    studies_root: Path | None = None,
) -> None:
    """Compile listed raw files, then lint the wiki once."""
    compile_raw_files(context_dir, file_ids, raw_roots=raw_roots)
    if not skip_linter:
        run_linter(context_dir)
    _maybe_rebuild_ontology(context_dir, studies_root=studies_root)


def _maybe_rebuild_ontology(context_dir: Path, *, studies_root: Path | None = None) -> None:
    if not kma_ontology_enabled():
        return
    try:
        from kma.ontology import rebuild_ontology

        root = studies_root or get_kma_studies_root()
        studies_docs = (root / "docs") if root and (root / "docs").is_dir() else None
        result = rebuild_ontology(
            context_dir.resolve(),
            studies_root=root,
            studies_docs_dir=studies_docs,
            run_enrichment=kma_ontology_enrich_enabled(),
        )
        logger.info(
            "ontology rebuilt: ok=%s counts=%s",
            result.validation.ok,
            result.counts,
        )
    except Exception:
        logger.exception("ontology rebuild failed")
