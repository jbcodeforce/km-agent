#!/usr/bin/env python3
"""Catalog studies ``code/`` (or ``src/``) into wiki concept pages with intent summaries.

Walks top-level categories under a studies repo code tree, builds a README + file
index pack per lab, and writes ``wiki/concepts/code-<category>.md`` with short
intent blurbs (LLM by default) plus ``code:`` path refs for ontology linking.
Updates a script-owned ``## Code catalogs`` section in ``wiki/index.md``.

After a successful run, embed for chat retrieval:

  uv run python scripts/index_wiki.py --context ./context

Example:

  uv run python scripts/index_studies_code.py \\
    --studies-root /path/to/flink-studies \\
    --context ./context

  uv run python scripts/index_studies_code.py --dry-run
  uv run python scripts/index_studies_code.py --no-llm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from kma.code_catalog import write_code_catalog  # noqa: E402
from kma.config import get_kma_context_dir, get_kma_studies_root  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--studies-root",
        type=Path,
        default=None,
        help="Studies repo root (default: KMA_STUDIES_ROOT)",
    )
    parser.add_argument(
        "--context",
        type=Path,
        default=None,
        help="KMA context dir (wiki/ lives here). Default: KMA_CONTEXT_DIR",
    )
    parser.add_argument(
        "--code-subdir",
        default=None,
        help="Subdir under studies-root (default: auto code/ then src/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List categories/labs; no LLM calls and no writes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-summarize even when pack hash matches existing page",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Use README/path fallback blurbs instead of the configured LLM",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N labs across categories (smoke/dev)",
    )
    args = parser.parse_args()

    studies = args.studies_root or get_kma_studies_root()
    if studies is None:
        print(
            "error: pass --studies-root or set KMA_STUDIES_ROOT",
            file=sys.stderr,
        )
        return 1
    studies = studies.resolve()
    if not studies.is_dir():
        print(f"error: not a directory: {studies}", file=sys.stderr)
        return 1

    ctx = (args.context or get_kma_context_dir()).resolve()
    if not ctx.is_dir() and not args.dry_run:
        ctx.mkdir(parents=True, exist_ok=True)

    try:
        stats = write_code_catalog(
            ctx,
            studies,
            code_subdir=args.code_subdir,
            dry_run=args.dry_run,
            force=args.force,
            use_llm=not args.no_llm and not args.dry_run,
            limit=args.limit,
        )
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(
        f"summary: categories={stats.categories} labs={stats.labs} "
        f"written={stats.written} skipped_unchanged={stats.skipped_unchanged} "
        f"llm_calls={stats.llm_calls}"
    )
    if not args.dry_run and stats.written:
        print(
            "next: uv run python scripts/index_wiki.py "
            f"--context {ctx}  # embed for chat search"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
