#!/usr/bin/env python3
"""Rebuild context/ontology from wiki, manifest, and optional studies code tree."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kma.config import (  # noqa: E402
    get_kma_context_dir,
    get_kma_studies_root,
    kma_ontology_enrich_enabled,
)
from kma.ontology import rebuild_ontology  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build OWL/RDF graph from wiki markdown.")
    parser.add_argument(
        "--context",
        type=Path,
        default=None,
        help="Context directory (default: KMA_CONTEXT_DIR or ./context)",
    )
    parser.add_argument(
        "--studies-root",
        type=Path,
        default=None,
        help="Studies repo root for code/ scanning (default: KMA_STUDIES_ROOT)",
    )
    parser.add_argument(
        "--studies-docs",
        type=Path,
        default=None,
        help="Studies docs/ dir for manifest (default: studies-root/docs)",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Run gap-triggered enrichment into proposed.ttl",
    )
    parser.add_argument(
        "--reason",
        action="store_true",
        help="Run owlapy StructuralReasoner (requires uv sync --extra ontology)",
    )
    parser.add_argument(
        "--merge-proposals",
        action="store_true",
        default=True,
        help="Merge approved proposed.ttl into graph (default: true)",
    )
    args = parser.parse_args()

    context_dir = (args.context or get_kma_context_dir()).resolve()
    studies_root = args.studies_root or get_kma_studies_root()
    studies_docs = args.studies_docs or studies_root / "docs"
    result = rebuild_ontology(
        context_dir,
        studies_root=studies_root,
        studies_docs_dir=studies_docs,
        merge_proposals=args.merge_proposals,
        run_enrichment=args.enrich or kma_ontology_enrich_enabled(),
        run_reasoning=args.reason,
    )
    print(f"Built ontology: {result.state_path}")
    print(f"Validation ok: {result.validation.ok}")
    print(f"Counts: {result.counts}")
    if result.validation.issues:
        print("Issues:")
        for issue in result.validation.issues[:20]:
            print(f"  - {issue}")
    return 0 if result.validation.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
