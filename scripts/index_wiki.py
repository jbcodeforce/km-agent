#!/usr/bin/env python3
"""Embed compiled wiki markdown into pgvector for semantic search (offline, no LLM).

Walks ``context/wiki/**/*.md``, inserts each file into the ``kma_wiki`` Knowledge
base using the configured embedder (``KMA_EMBED_PROVIDER=fastembed`` in Docker).

Requires Postgres only.

Example:

  uv run python scripts/index_wiki.py --context ./context
  uv run python scripts/index_wiki.py --context ./context --dry-run
  uv run python scripts/index_wiki.py --context ./context --recreate
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from sqlalchemy import text  # noqa: E402

from kma.config import get_kma_context_dir  # noqa: E402
from kma.db import KMA_SCHEMA, create_knowledge, get_sql_engine  # noqa: E402

WIKI_TABLE = "kma_wiki"
WIKI_CONTENTS_TABLE = f"{WIKI_TABLE}_contents"
_SKIP_FILES = frozenset({"lint-report.md"})


def discover_wiki_markdown(wiki_dir: Path) -> list[Path]:
    """Return markdown files under wiki/, sorted, excluding skip list."""
    if not wiki_dir.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(wiki_dir.rglob("*.md")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.name in _SKIP_FILES:
            continue
        files.append(path)
    return files


def drop_wiki_tables() -> None:
    """Drop kma_wiki vector and contents tables (for --recreate)."""
    engine = get_sql_engine()
    with engine.connect() as conn:
        for table in (WIKI_TABLE, WIKI_CONTENTS_TABLE):
            conn.execute(text(f'DROP TABLE IF EXISTS "{KMA_SCHEMA}"."{table}" CASCADE'))
        conn.commit()
    engine.dispose()


def index_wiki(
    context_dir: Path,
    *,
    dry_run: bool = False,
    recreate: bool = False,
    skip_existing: bool = False,
) -> int:
    wiki_dir = context_dir / "wiki"
    files = discover_wiki_markdown(wiki_dir)
    if not files:
        print(f"warning: no wiki markdown under {wiki_dir}", file=sys.stderr)
        return 0

    print(f"found {len(files)} wiki markdown file(s) under {wiki_dir}")
    if dry_run:
        for p in files:
            print(f"  would index: {p.relative_to(wiki_dir)}")
        return 0

    if recreate:
        print(f"dropping tables {WIKI_TABLE}, {WIKI_CONTENTS_TABLE}...")
        drop_wiki_tables()

    knowledge = create_knowledge("kma Wiki", WIKI_TABLE)
    indexed = 0
    for path in files:
        rel = path.relative_to(wiki_dir).as_posix()
        name = f"Wiki: {rel}"
        print(f"indexing: {rel}")
        knowledge.insert(
            name=name,
            path=str(path),
            metadata={"wiki_path": rel, "source": "wiki"},
            upsert=True,
            skip_if_exists=skip_existing,
        )
        indexed += 1

    print(f"indexed {indexed} wiki file(s) into {WIKI_TABLE}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Embed wiki markdown into pgvector (kma_wiki).")
    parser.add_argument(
        "--context",
        type=Path,
        default=None,
        help="KMA context dir (wiki/ lives here). Default: KMA_CONTEXT_DIR",
    )
    parser.add_argument("--dry-run", action="store_true", help="List files only; no DB/embed calls")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help=f"Drop {WIKI_TABLE} tables before indexing",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Pass skip_if_exists=True to knowledge.insert",
    )
    args = parser.parse_args()
    ctx = (args.context or get_kma_context_dir()).resolve()
    if not ctx.is_dir():
        print(f"error: not a directory: {ctx}", file=sys.stderr)
        return 1
    return index_wiki(
        ctx,
        dry_run=args.dry_run,
        recreate=args.recreate,
        skip_existing=args.skip_existing,
    )


if __name__ == "__main__":
    raise SystemExit(main())
