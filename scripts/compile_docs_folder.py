#!/usr/bin/env python3
"""Run the Compiler and Linter over a studies ``docs/`` tree.

Crawls ``**/*.md`` under the given docs directory and compiles files that
already have km-agent raw YAML frontmatter. Files without frontmatter are
skipped with a warning — run ``scripts/add_raw_frontmatter.py`` first.

If ``docs/.manifest.json`` is missing, an empty manifest is created before
invoking the compiler so the raw root always has manifest I/O.

Runs the Compiler once per eligible markdown file (skipping entries already
marked ``compiled: true`` in ``.manifest.json``), then the Linter once, with:

- ``raw_roots``: your docs folder (e.g. ``--label studies``) plus ``ingested``
  pointing at ``<context>/raw`` (researcher output), so both coexist.
- ``context_dir``: wiki output under ``<context>/wiki/``.

Requires Postgres and configured LLM/embeddings (see docs/DEVELOPER_PRACTICES.md).

Example:

  uv run python scripts/add_raw_frontmatter.py /path/to/flink-studies/docs \\
    --source flink-studies

  uv run python scripts/compile_docs_folder.py /path/to/flink-studies/docs \\
    --context ./context --label studies
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from kma.config import get_kma_context_dir  # noqa: E402
from kma.tools.ingest import (  # noqa: E402
    _write_manifest,
    has_km_raw_frontmatter,
    has_yaml_frontmatter,
    iter_markdown_files,
    manifest_entry_compiled,
)
from kma.workflows.wiki_refresh import compile_raw_files, run_linter  # noqa: E402


def _ensure_manifest_exists(raw_dir: Path, *, dry_run: bool) -> None:
    """Create ``.manifest.json`` with ``[]`` if missing so the compiler root is valid."""
    if dry_run:
        return
    manifest_path = raw_dir / ".manifest.json"
    if not manifest_path.exists():
        _write_manifest(raw_dir, [])
        print(f"created empty manifest: {manifest_path}")


def _compile_skip_reason(text: str) -> str | None:
    """Return a user-facing reason when a file must not be compiled, else None."""
    if not has_yaml_frontmatter(text):
        return "no YAML frontmatter — run scripts/add_raw_frontmatter.py first"
    if not has_km_raw_frontmatter(text):
        return "missing km-agent raw frontmatter — run scripts/add_raw_frontmatter.py first"
    return None


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
        "--dry-run",
        action="store_true",
        help="List files that would be compiled; do not call the compiler or linter",
    )
    parser.add_argument(
        "--skip-compiler",
        action="store_true",
        help="Validate docs only; do not call the LLM",
    )
    parser.add_argument(
        "--skip-linter",
        action="store_true",
        help="Skip the post-compile Linter agent run",
    )
    parser.add_argument(
        "--recompile",
        action="store_true",
        help="Re-run the Compiler for files already marked compiled in the manifest",
    )
    args = parser.parse_args()

    docs = args.docs.resolve()
    if not docs.is_dir():
        print(f"error: not a directory: {docs}", file=sys.stderr)
        return 1

    _ensure_manifest_exists(docs, dry_run=args.dry_run)

    ctx = (args.context or get_kma_context_dir()).resolve()
    md_files = iter_markdown_files(docs)
    if not md_files:
        print(f"warning: no markdown files under {docs}", file=sys.stderr)

    skipped_no_frontmatter = 0
    compile_candidates: list[Path] = []
    for path in md_files:
        rel = path.relative_to(docs).as_posix()
        reason = _compile_skip_reason(path.read_text(encoding="utf-8"))
        if reason:
            print(f"warning: skipping {rel} — {reason}", file=sys.stderr)
            skipped_no_frontmatter += 1
            continue
        compile_candidates.append(path)

    if skipped_no_frontmatter:
        print(
            f"summary: skipped {skipped_no_frontmatter} file(s) without km-agent raw frontmatter",
            file=sys.stderr,
        )

    if not compile_candidates:
        print("error: no markdown files ready to compile", file=sys.stderr)
        return 1

    wiki = ctx / "wiki"
    (wiki / "summaries").mkdir(parents=True, exist_ok=True)
    (wiki / "concepts").mkdir(parents=True, exist_ok=True)
    (ctx / "raw").mkdir(parents=True, exist_ok=True)

    if args.dry_run or args.skip_compiler:
        file_ids: list[str] = []
        skipped = 0
        for path in compile_candidates:
            rel = path.relative_to(docs).as_posix()
            file_id = f"{args.label}:{rel}"
            if not args.recompile and manifest_entry_compiled(docs, rel):
                print(f"would skip already compiled: {file_id}")
                skipped += 1
                continue
            print(f"would compile: {file_id}")
            file_ids.append(file_id)
        if args.dry_run:
            print("skip compiler and linter (--dry-run)")
        else:
            print("skip compiler (--skip-compiler)")
        if skipped:
            print(f"already compiled: {skipped} file(s)")
        print(f"ready to compile: {len(file_ids)} file(s)")
        return 0

    ingested_root = ctx / "raw"
    raw_roots = [(args.label, docs), ("ingested", ingested_root)]
    file_ids: list[str] = []
    skipped = 0
    for path in compile_candidates:
        rel = path.relative_to(docs).as_posix()
        file_id = f"{args.label}:{rel}"
        if not args.recompile and manifest_entry_compiled(docs, rel):
            print(f"skip already compiled: {file_id}")
            skipped += 1
            continue
        file_ids.append(file_id)
    if file_ids:
        compile_raw_files(ctx, file_ids, raw_roots=raw_roots)
    if skipped:
        print(f"skipped {skipped} already-compiled file(s)")
    print("compiler run completed")

    if args.skip_linter:
        print("skip linter (--skip-linter)")
        return 0

    print("running linter")
    if not run_linter(ctx):
        return 1
    print("linter run completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
