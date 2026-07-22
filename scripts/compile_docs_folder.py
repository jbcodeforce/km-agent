#!/usr/bin/env python3
"""Run the Compiler and Linter over a studies ``docs/`` tree.

Crawls ``**/*.md`` under the given docs directory and compiles files that
already have km-agent raw YAML frontmatter. Files without frontmatter are
skipped with a warning — run ``scripts/add_raw_frontmatter.py`` first.

Tracking lives in the shared ``<context>/.manifest.json`` (keyed by
``file_id`` such as ``studies:path.md`` / ``ingested:name.md``).

Runs the Compiler once per eligible markdown file whose content SHA-256 does
not match the ``sha256`` stored for that ``file_id`` (use ``--recompile`` to
force every file), then the Linter once, with:

- ``raw_roots``: your docs folder (e.g. ``--label studies``) plus ``ingested``
  pointing at ``<context>/raw`` (researcher output), so both coexist.
- ``context_dir``: wiki output under ``<context>/wiki/``.

Requires Postgres and configured LLM/embeddings (see docs/DEVELOPER_PRACTICES.md).

Example:

  uv run python scripts/add_raw_frontmatter.py /path/to/flink-studies/docs \\
    --source flink-studies --context ./context --label studies

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
    ensure_manifest_exists,
    has_km_raw_frontmatter,
    has_yaml_frontmatter,
    iter_markdown_files,
    make_file_id,
    manifest_content_unchanged,
    manifest_entry_compiled,
    set_manifest_compiled,
    set_manifest_sha256,
    sha256_file,
)
from kma.workflows.wiki_refresh import compile_raw_files, run_linter  # noqa: E402


def _compile_skip_reason(text: str) -> str | None:
    """Return a user-facing reason when a file must not be compiled, else None."""
    if not has_yaml_frontmatter(text):
        return "no YAML frontmatter — run scripts/add_raw_frontmatter.py first"
    if not has_km_raw_frontmatter(text):
        return "missing km-agent raw frontmatter — run scripts/add_raw_frontmatter.py first"
    return None


def _should_skip_unchanged(
    context_dir: Path, file_id: str, path: Path, *, recompile: bool
) -> bool:
    """Skip when stored sha256 matches current file bytes (unless ``recompile``)."""
    if recompile:
        return False
    return manifest_content_unchanged(context_dir, file_id, path)


def _prepare_file_for_compile(context_dir: Path, file_id: str) -> None:
    """Clear ``compiled`` so ``compile_raw_files`` will not skip a stale entry."""
    if manifest_entry_compiled(context_dir, file_id):
        set_manifest_compiled(context_dir, file_id, False)


def _record_sha256_for_compiled(
    context_dir: Path,
    docs: Path,
    label: str,
    compiled_ids: list[str],
) -> None:
    """Write sha256 into the context manifest for successfully compiled studies files."""
    prefix = f"{label}:"
    for file_id in compiled_ids:
        if not file_id.startswith(prefix):
            continue
        rel = file_id[len(prefix) :]
        path = docs / rel
        if not path.is_file():
            continue
        set_manifest_sha256(context_dir, file_id, sha256_file(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docs", type=Path, help="Studies docs directory root to crawl")
    parser.add_argument(
        "--context",
        type=Path,
        default=None,
        help="KMA context dir (wiki/ + raw/ + .manifest.json). Default: KMA_CONTEXT_DIR",
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
        help="Re-run the Compiler even when the file sha256 matches the manifest",
    )
    args = parser.parse_args()

    docs = args.docs.resolve()
    if not docs.is_dir():
        print(f"error: not a directory: {docs}", file=sys.stderr)
        return 1

    ctx = (args.context or get_kma_context_dir()).resolve()
    if not args.dry_run:
        path = ensure_manifest_exists(ctx)
        print(f"manifest: {path}")

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
            file_id = make_file_id(args.label, rel)
            if _should_skip_unchanged(ctx, file_id, path, recompile=args.recompile):
                print(f"would skip unchanged: {file_id}")
                skipped += 1
                continue
            print(f"would compile: {file_id}")
            file_ids.append(file_id)
        if args.dry_run:
            print("skip compiler and linter (--dry-run)")
        else:
            print("skip compiler (--skip-compiler)")
        if skipped:
            print(f"unchanged (sha256 match): {skipped} file(s)")
        print(f"ready to compile: {len(file_ids)} file(s)")
        return 0

    ingested_root = ctx / "raw"
    raw_roots = [(args.label, docs), ("ingested", ingested_root)]
    file_ids = []
    skipped = 0
    for path in compile_candidates:
        rel = path.relative_to(docs).as_posix()
        file_id = make_file_id(args.label, rel)
        if _should_skip_unchanged(ctx, file_id, path, recompile=args.recompile):
            print(f"skip unchanged: {file_id}")
            skipped += 1
            continue
        _prepare_file_for_compile(ctx, file_id)
        file_ids.append(file_id)
    compiled_ids: list[str] = []
    if file_ids:
        compiled_ids = compile_raw_files(ctx, file_ids, raw_roots=raw_roots)
        _record_sha256_for_compiled(ctx, docs, args.label, compiled_ids)
    if skipped:
        print(f"skipped {skipped} unchanged file(s)")
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
