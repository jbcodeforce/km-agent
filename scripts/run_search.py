#!/usr/bin/env python3
"""Run research, compile, and lint from a query and optional web_site_ref.json.

Example:

  uv run python scripts/run_search.py \\
    "what are the difference between flink 2.1 and 2.2" \\
    --context ./context \\
    --src-file web_site_ref.json

Requires Postgres and configured LLM for compile/lint. Research requires
``KMA_PARALLEL_API_KEY`` or ``PARALLEL_API_KEY``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from kma.config import get_kma_context_dir  # noqa: E402
from kma.tools.site_refs import (  # noqa: E402
    load_site_refs_for_context,
    resolve_site_refs_path,
)
from kma.workflows.enrichment import (  # noqa: E402
    build_research_prompt,
    run_search_pipeline,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Research question or topic")
    parser.add_argument(
        "--context",
        type=Path,
        default=None,
        help="KMA context dir (wiki/ + raw/). Default: KMA_CONTEXT_DIR",
    )
    parser.add_argument(
        "--src-file",
        type=Path,
        default=None,
        dest="src_file",
        help="Path to web_site_ref.json (default: <context>/web_site_ref.json if present)",
    )
    parser.add_argument(
        "--skip-research",
        action="store_true",
        help="Skip research; compile+lint existing uncompiled raw files only",
    )
    parser.add_argument(
        "--skip-compile",
        action="store_true",
        help="Run research only; do not compile or lint",
    )
    parser.add_argument(
        "--skip-lint",
        action="store_true",
        help="Compile without running the linter",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved prompt and paths; do not call LLM",
    )
    args = parser.parse_args()

    ctx = (args.context or get_kma_context_dir()).resolve()
    if not ctx.is_dir():
        print(f"error: context directory not found: {ctx}", file=sys.stderr)
        return 1

    site_refs_path = resolve_site_refs_path(ctx, args.src_file)
    site_refs = load_site_refs_for_context(ctx, args.src_file)

    if args.dry_run:
        print(f"context: {ctx}")
        print(f"site_refs: {site_refs_path or '(none)'}")
        print(f"sites loaded: {len(site_refs)}")
        print("--- prompt ---")
        print(build_research_prompt(args.query, site_refs or None))
        return 0

    try:
        result = run_search_pipeline(
            args.query,
            ctx,
            site_refs_path=args.src_file,
            skip_research=args.skip_research,
            skip_compile=args.skip_compile,
            skip_lint=args.skip_lint,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"research: {result.research_status}")
    if result.ingested_file_ids:
        print(f"ingested: {', '.join(result.ingested_file_ids)}")
    if result.compiled_file_ids:
        print(f"compiled: {', '.join(result.compiled_file_ids)}")
    if result.linter_ok is not None:
        print(f"linter: {'ok' if result.linter_ok else 'failed'}")
        if not result.linter_ok:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
