#!/usr/bin/env python3
"""Prepend km-agent raw YAML frontmatter to an existing markdown file.

Raw documents expected by the compiler pipeline need YAML frontmatter
(title, source, ingested date, tags, type, compiled) per docs/SPEC.md.
Use this for legacy or imported .md files that only have a body (e.g. no --- block).

Example:
  uv run python scripts/add_raw_frontmatter.py tests/external_raw/flink-sql-1.md \\
    --title \"Flink SQL: CREATE TABLE\" --source flink-studies --tags flink,sql
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Repo root: scripts/ -> parent
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from kma.tools.ingest import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    _build_frontmatter,
    _read_manifest,
    _write_manifest,
)


def _has_yaml_frontmatter(text: str) -> bool:
    if not text.startswith("---\n"):
        return False
    close = text.find("\n---\n", 4)
    return close != -1


def _first_h1_title(body: str) -> str | None:
    for line in body.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return None


def _append_manifest_entry(raw_dir: Path, filename: str, title: str, source: str) -> None:
    manifest = _read_manifest(raw_dir)
    ingested = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for entry in manifest:
        if entry.get("file") == filename:
            entry["title"] = title
            entry["source"] = source
            entry["ingested"] = ingested
            entry["compiled"] = False
            _write_manifest(raw_dir, manifest)
            return
    manifest.append(
        {
            "file": filename,
            "title": title,
            "source": source,
            "ingested": ingested,
            "compiled": False,
        }
    )
    _write_manifest(raw_dir, manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown", type=Path, help="Path to .md file to update")
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
        "--dry-run",
        action="store_true",
        help="Print frontmatter and new first lines; do not write files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing YAML frontmatter if present",
    )
    args = parser.parse_args()

    path = args.markdown.resolve()
    if not path.is_file():
        print(f"error: not a file: {path}", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")
    if _has_yaml_frontmatter(text) and not args.force:
        print(f"error: file already has YAML frontmatter: {path}", file=sys.stderr)
        print("  use --force to strip old frontmatter and prepend new", file=sys.stderr)
        return 1

    body = text
    if args.force and _has_yaml_frontmatter(text):
        end = text.find("\n---\n", 4)
        body = text[end + len("\n---\n") :].lstrip("\n")

    title = args.title or _first_h1_title(body) or path.stem.replace("-", " ").title()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    front = _build_frontmatter(title, args.source, tags, args.doc_type)
    new_text = front + body.lstrip("\n")
    if not new_text.endswith("\n"):
        new_text += "\n"

    raw_dir = path.parent
    if args.dry_run:
        print(front)
        print("--- body preview ---")
        print("\n".join(new_text.splitlines()[:8]))
        return 0

    path.write_text(new_text, encoding="utf-8")
    _append_manifest_entry(raw_dir, path.name, title, args.source)
    print(f"updated: {path}")
    manifest_path = raw_dir / ".manifest.json"
    print(f"manifest: {manifest_path} (entry for {path.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
