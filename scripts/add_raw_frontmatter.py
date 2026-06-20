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

from kma.tools.ingest import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    apply_raw_frontmatter_to_text,
    append_manifest_entry,
    has_km_raw_frontmatter,
    has_yaml_frontmatter,
    iter_markdown_files,
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
    for path in paths:
        text = path.read_text(encoding="utf-8")
        rel = _manifest_rel(path, docs_root)
        if has_yaml_frontmatter(text):
            with_fm.append(rel)
        else:
            without_fm.append(rel)

    for rel in sorted(with_fm):
        print(f"with frontmatter: {rel}")
    for rel in sorted(without_fm):
        print(f"without frontmatter: {rel}")

    total = len(paths)
    print(
        f"summary: {total} markdown file(s); "
        f"{len(with_fm)} with frontmatter, {len(without_fm)} without"
    )
    return 1 if without_fm else 0


def _process_file(
    path: Path,
    docs_root: Path,
    *,
    title: str | None,
    source: str,
    tags: list[str],
    doc_type: str,
    force: bool,
    dry_run: bool,
) -> tuple[str, str | None]:
    """Return (status, error). status is updated, skipped, or dry_run."""
    text = path.read_text(encoding="utf-8")
    rel = _manifest_rel(path, docs_root)
    fallback = _fallback_title(path, docs_root)

    if has_km_raw_frontmatter(text) and not force:
        if dry_run:
            return "dry_run", None
        append_manifest_entry(docs_root, rel, title or fallback, source)
        return "updated", None

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
        return "skipped", f"{skip_reason}: {path}"

    if dry_run:
        print(f"[dry-run] would update {rel}")
        print(new_text.splitlines()[0])
        print("...")
        return "dry_run", None

    path.write_text(new_text, encoding="utf-8")
    append_manifest_entry(docs_root, rel, resolved_title, source)
    print(f"updated: {path}")
    return "updated", None


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

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    updated = skipped = dry_run = errors = 0
    for path in paths:
        status, err = _process_file(
            path,
            docs_root,
            title=args.title,
            source=args.source,
            tags=tags,
            doc_type=args.doc_type,
            force=args.force,
            dry_run=args.dry_run,
        )
        if status == "updated":
            updated += 1
        elif status == "dry_run":
            dry_run += 1
        elif status == "skipped":
            skipped += 1
            if err:
                print(f"error: {err}", file=sys.stderr)
                errors += 1

    if len(paths) > 1:
        print(
            f"summary: {len(paths)} file(s); "
            f"{updated} updated, {skipped} skipped, {dry_run} dry-run, {errors} error(s)"
        )

    if errors:
        return 1

    if len(paths) == 1 and updated == 1 and not args.dry_run:
        manifest_path = docs_root / ".manifest.json"
        rel = _manifest_rel(paths[0], docs_root)
        print(f"manifest: {manifest_path} (entry for {rel})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
