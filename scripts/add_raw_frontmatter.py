#!/usr/bin/env python3
"""Prepend km-agent raw YAML frontmatter to markdown file(s).

Raw documents expected by the compiler pipeline need YAML frontmatter
(title, source, ingested date, tags, type, compiled) per docs/SPEC.md.
Use this for legacy or imported .md files that only have a body (e.g. no --- block).

Examples:
  uv run python scripts/add_raw_frontmatter.py tests/external_raw/flink-sql-1.md \\
    --title \"Flink SQL: CREATE TABLE\" --source flink-studies --tags flink,sql

  uv run python scripts/add_raw_frontmatter.py /path/to/docs --source flink-studies

  uv run python scripts/add_raw_frontmatter.py /path/to/docs --check
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo root: scripts/ -> parent
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from kma.config import get_kma_context_dir  # noqa: E402  # pyright: ignore[reportMissingImports]
from kma.tools.ingest import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    apply_raw_frontmatter_to_text,
    append_manifest_entry,
    ensure_manifest_exists,
    has_km_raw_frontmatter,
    has_yaml_frontmatter,
    iter_markdown_files,
    make_file_id,
    title_from_markdown,
)


def _manifest_rel(path: Path, docs_root: Path) -> str:
    if path.parent.resolve() == docs_root.resolve():
        return path.name
    return path.relative_to(docs_root).as_posix()


def _fallback_title(path: Path, docs_root: Path) -> str:
    rel = _manifest_rel(path, docs_root)
    stem = Path(rel).stem
    return title_from_markdown("", fallback_stem=stem)


def _check_paths(paths: list[Path], docs_root: Path) -> int:
    with_fm: list[str] = []
    without_fm: list[str] = []
    print(f"inspected: {len(paths)} markdown file(s)")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        rel = _manifest_rel(path, docs_root)
        print(f"  inspected: {path}")
        if has_yaml_frontmatter(text):
            with_fm.append(rel)
            print(f"  status:    with frontmatter ({rel})")
        else:
            without_fm.append(rel)
            print(f"  status:    without frontmatter ({rel})")

    total = len(paths)
    print(
        f"summary: {total} inspected; "
        f"{len(with_fm)} with frontmatter, {len(without_fm)} without; "
        f"0 modified (--check)"
    )
    return 1 if without_fm else 0


def _process_file(
    path: Path,
    docs_root: Path,
    *,
    context_dir: Path,
    label: str,
    title: str | None,
    source: str,
    tags: list[str],
    doc_type: str,
    force: bool,
    dry_run: bool,
) -> tuple[str, str | None]:
    """Return (status, error). status is modified, skipped, unchanged, or dry_run."""
    text = path.read_text(encoding="utf-8")
    rel = _manifest_rel(path, docs_root)
    file_id = make_file_id(label, rel)
    fallback = _fallback_title(path, docs_root)
    print(f"inspected: {path}")

    if has_km_raw_frontmatter(text) and not force:
        if dry_run:
            print(f"  dry-run:   would leave unchanged ({file_id})")
            return "dry_run", None
        append_manifest_entry(context_dir, file_id, title or fallback, source)
        print(f"  unchanged: already has km-agent frontmatter ({file_id})")
        return "unchanged", None

    new_text, resolved_title, skip_reason = apply_raw_frontmatter_to_text(
        text,
        source=source,
        tags=tags,
        doc_type=doc_type,
        title=title,
        fallback_title=fallback,
        force=force,
    )
    if skip_reason:
        print(f"  skipped:   {skip_reason} ({file_id})")
        return "skipped", f"{skip_reason}: {path}"

    if dry_run:
        print(f"  dry-run:   would modify ({file_id})")
        print(f"  preview:   {new_text.splitlines()[0]}")
        print("  ...")
        return "dry_run", None

    path.write_text(new_text, encoding="utf-8")
    append_manifest_entry(context_dir, file_id, resolved_title, source)
    print(f"modified:  {path}")
    return "modified", None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        help="Path to a .md file or a directory to crawl for *.md files",
    )
    parser.add_argument(
        "--title",
        help="Document title (default: first # heading, else filename stem)",
    )
    parser.add_argument(
        "--source",
        default="local-import",
        help="Provenance string for frontmatter source: (default: local-import)",
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags for frontmatter",
    )
    parser.add_argument(
        "--type",
        default="article",
        dest="doc_type",
        help="Frontmatter type: paper, article, repo, notes, ... (default: article)",
    )
    parser.add_argument(
        "--context",
        type=Path,
        default=None,
        help="KMA context dir for the shared .manifest.json (default: KMA_CONTEXT_DIR)",
    )
    parser.add_argument(
        "--label",
        default="studies",
        help="Manifest file_id label for this docs tree (default: studies)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report which markdown files have frontmatter; do not modify files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned updates; do not write files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing YAML frontmatter if present",
    )
    args = parser.parse_args()

    target = args.path.resolve()
    if target.is_file():
        if target.suffix.lower() != ".md":
            print(f"error: not a markdown file: {target}", file=sys.stderr)
            return 1
        paths = [target]
        docs_root = target.parent
    elif target.is_dir():
        paths = iter_markdown_files(target)
        docs_root = target
        if not paths:
            print(f"error: no markdown files under {target}", file=sys.stderr)
            return 1
    else:
        print(f"error: not a file or directory: {target}", file=sys.stderr)
        return 1

    if args.check:
        return _check_paths(paths, docs_root)

    context_dir = (args.context or get_kma_context_dir()).resolve()
    if not args.dry_run:
        ensure_manifest_exists(context_dir)

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    inspected: list[Path] = []
    modified: list[Path] = []
    unchanged: list[Path] = []
    skipped: list[Path] = []
    dry_run_paths: list[Path] = []
    errors = 0

    print(f"scanning: {target} ({len(paths)} markdown file(s))")
    print(f"manifest context: {context_dir} (label={args.label})")
    for path in paths:
        inspected.append(path)
        status, err = _process_file(
            path,
            docs_root,
            context_dir=context_dir,
            label=args.label,
            title=args.title,
            source=args.source,
            tags=tags,
            doc_type=args.doc_type,
            force=args.force,
            dry_run=args.dry_run,
        )
        if status == "modified":
            modified.append(path)
        elif status == "dry_run":
            dry_run_paths.append(path)
        elif status == "unchanged":
            unchanged.append(path)
        elif status == "skipped":
            skipped.append(path)
            if err:
                print(f"error: {err}", file=sys.stderr)
                errors += 1

    print("")
    print("── result ──")
    print(f"inspected ({len(inspected)}):")
    for path in inspected:
        print(f"  · {path}")
    print(f"modified ({len(modified)}):")
    if modified:
        for path in modified:
            print(f"  · {path}")
    else:
        print("  · (none)")
    if unchanged:
        print(f"unchanged ({len(unchanged)}):")
        for path in unchanged:
            print(f"  · {path}")
    if dry_run_paths:
        print(f"dry-run ({len(dry_run_paths)}):")
        for path in dry_run_paths:
            print(f"  · {path}")
    if skipped:
        print(f"skipped ({len(skipped)}):")
        for path in skipped:
            print(f"  · {path}")

    if (modified or unchanged) and not args.dry_run:
        from kma.tools.ingest import context_manifest_path

        print(f"manifest: {context_manifest_path(context_dir)}")

    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
