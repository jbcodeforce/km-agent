#!/usr/bin/env python3
"""Prepare a studies ``docs/`` tree for the compiler and run the Compiler agent.

Crawls ``**/*.md`` under the given docs directory, ensures km-agent raw YAML
frontmatter and ``.manifest.json`` entries (paths relative to that docs root).
If ``docs/.manifest.json`` is missing, an empty manifest is created before
preparing files or invoking the compiler so that raw root always has manifest I/O.

Then runs the Compiler with:

- ``raw_roots``: your docs folder (e.g. ``--label studies``) plus ``ingested``
  pointing at ``<context>/raw`` (researcher output), so both coexist.
- ``context_dir``: wiki output under ``<context>/wiki/``.

Requires Postgres and configured LLM/embeddings (see docs/DEVELOPER_PRACTICES.md).

Example:

  uv run python scripts/compile_docs_folder.py /path/to/flink-studies/docs \\
    --context ./context --source flink-studies --label studies
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from agno.run.base import RunStatus  # noqa: E402

from kma.agents.compiler import build_compiler_agent  # noqa: E402
from kma.agents.settings import kma_knowledge  # noqa: E402
from kma.config import get_kma_context_dir  # noqa: E402
from kma.llm_factory import build_default_compiler_model  # noqa: E402
from kma.tools.ingest import (  # noqa: E402
    _build_frontmatter,
    _read_manifest,
    _write_manifest,
)

_EXCLUDE_DIR_NAMES = frozenset(
    {".git", "node_modules", ".venv", ".venvs", "__pycache__", ".tox", "dist", "build"}
)


def _has_yaml_frontmatter(text: str) -> bool:
    if not text.startswith("---\n"):
        return False
    close = text.find("\n---\n", 4)
    return close != -1


def _has_km_raw_frontmatter(text: str) -> bool:
    if not _has_yaml_frontmatter(text):
        return False
    close = text.find("\n---\n", 4)
    block = text[:close] if close != -1 else ""
    return "compiled:" in block and "title:" in block and "source:" in block


def _first_h1_title(body: str) -> str | None:
    for line in body.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return None


def _should_skip_path(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    return any(p in _EXCLUDE_DIR_NAMES for p in rel.parts)


def _ensure_manifest_exists(raw_dir: Path, *, dry_run: bool) -> None:
    """Create ``.manifest.json`` with ``[]`` if missing so the compiler root is valid."""
    if dry_run:
        return
    manifest_path = raw_dir / ".manifest.json"
    if not manifest_path.exists():
        _write_manifest(raw_dir, [])
        print(f"created empty manifest: {manifest_path}")


def _append_manifest_entry(raw_dir: Path, file_rel: str, title: str, source: str) -> None:
    manifest = _read_manifest(raw_dir)
    ingested = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for entry in manifest:
        if entry.get("file") == file_rel:
            entry["title"] = title
            entry["source"] = source
            entry["ingested"] = ingested
            entry["compiled"] = False
            _write_manifest(raw_dir, manifest)
            return
    manifest.append(
        {
            "file": file_rel,
            "title": title,
            "source": source,
            "ingested": ingested,
            "compiled": False,
        }
    )
    _write_manifest(raw_dir, manifest)


def _iter_markdown_docs(docs_root: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(docs_root.rglob("*.md")):
        if p.name.startswith("."):
            continue
        if _should_skip_path(p, docs_root):
            continue
        out.append(p)
    return out


def _prepare_file(
    path: Path,
    docs_root: Path,
    source: str,
    tags: list[str],
    doc_type: str,
    *,
    force: bool,
    dry_run: bool,
) -> tuple[str, str | None]:
    """Returns (status, error) for the file to process. status one of [updated, skipped, dry_run]"""
    print(f"processing: {path}")
    rel = path.relative_to(docs_root).as_posix()
    text = path.read_text(encoding="utf-8")
    if _has_km_raw_frontmatter(text):
        title = _first_h1_title(text) or Path(rel).stem.replace("-", " ").title()
        if dry_run:
            return ("dry_run", None)
        _append_manifest_entry(docs_root, rel, title, source)
        return ("updated", None)

    if _has_yaml_frontmatter(text) and not force:
        return ("skipped", f"has YAML but not km-agent raw block; use --force: {path}")

    body = text
    if force and _has_yaml_frontmatter(text) and not _has_km_raw_frontmatter(text):
        end = text.find("\n---\n", 4)
        body = text[end + len("\n---\n") :].lstrip("\n")

    title = _first_h1_title(body) or Path(rel).stem.replace("-", " ").title()
    front = _build_frontmatter(title, source, tags, doc_type)
    new_text = front + body.lstrip("\n")
    if not new_text.endswith("\n"):
        new_text += "\n"
    if dry_run:
        print(f"[dry-run] would update {rel}")
        return ("dry_run", None)
    path.write_text(new_text, encoding="utf-8")
    _append_manifest_entry(docs_root, rel, title, source)

    return ("updated", None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docs", type=Path, help="Studies docs directory root to crawl")
    parser.add_argument(
        "--context",
        type=Path,
        default=None,
        help="KMA context dir (wiki/ + raw/ for ingested). Default: KMA_CONTEXT_DIR",
    )
    parser.add_argument(
        "--label",
        default="studies",
        help="Raw root label for this docs tree (default: studies)",
    )
    parser.add_argument(
        "--source",
        default="studies-docs",
        help="Frontmatter/manifest source string (default: studies-docs)",
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags for new frontmatter",
    )
    parser.add_argument(
        "--type",
        default="article",
        dest="doc_type",
        help="Frontmatter type (default: article)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Prepare only; do not run compiler")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace non-km YAML frontmatter when prepending km block",
    )
    parser.add_argument(
        "--skip-compiler",
        action="store_true",
        help="Only prepare docs/manifest; do not call the LLM",
    )
    args = parser.parse_args()

    docs = args.docs.resolve()
    if not docs.is_dir():
        print(f"error: not a directory: {docs}", file=sys.stderr)
        return 1

    ctx = (args.context or get_kma_context_dir()).resolve()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    md_files = _iter_markdown_docs(docs)
    if not md_files:
        print(f"warning: no markdown files under {docs}", file=sys.stderr)

    _ensure_manifest_exists(docs, dry_run=args.dry_run)

    errors = 0
    for p in md_files:
        status, err = _prepare_file(
            p,
            docs,
            args.source,
            tags,
            args.doc_type,
            force=args.force,
            dry_run=args.dry_run,
        )
        if err:
            print(err, file=sys.stderr)
            errors += 1
        elif status == "updated":
            print(f"prepared: {p.relative_to(docs)}")

    if errors:
        return 1

    wiki = ctx / "wiki"
    (wiki / "summaries").mkdir(parents=True, exist_ok=True)
    (wiki / "concepts").mkdir(parents=True, exist_ok=True)
    (ctx / "raw").mkdir(parents=True, exist_ok=True)

    if args.dry_run or args.skip_compiler:
        print("skip compiler (--dry-run or --skip-compiler)")
        return 0

    model = build_default_compiler_model()
    ingested_root = ctx / "raw"
    agent = build_compiler_agent(
        context_dir=ctx,
        raw_roots=[(args.label, docs), ("ingested", ingested_root)],
        knowledge=kma_knowledge,
        model=model,
    )
    prompt = (
        "You are running an automated batch compile. Use tools only; do not ask the user questions.\n"
        "1) Call read_manifest and process every entry where compiled is false.\n"
        "2) For each: read the raw file using the path from read_manifest "
        "(use raw/<label>/... as returned by your file tools for multi-root layouts).\n"
        "3) Write wiki/summaries and wiki/concepts as in your system instructions, "
        "then update_manifest_compiled with the exact file_id from the manifest.\n"
        "4) When all uncompiled sources are done, update_wiki_index and update_wiki_state (mark_compiled true).\n"
        "Keep tool calls efficient; complete the workflow."
    )
    out = agent.run(prompt)
    if out.status != RunStatus.completed:
        print(f"compiler run failed: {out.status} {out.content!r}", file=sys.stderr)
        return 1
    print("compiler run completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
