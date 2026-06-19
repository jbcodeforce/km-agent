#!/usr/bin/env python3
"""Merge proposed.ttl into graph.ttl after human review."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kma.config import get_kma_context_dir  # noqa: E402
from kma.ontology.builder import (  # noqa: E402
    build_deterministic_graph,
    write_ontology_outputs,
)
from kma.ontology.merge import merge_proposals_into_graph  # noqa: E402
from kma.ontology.tbox import ensure_context_tbox  # noqa: E402
from kma.ontology.validate import validate_graph  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Approve and merge ontology proposals.")
    parser.add_argument("--context", type=Path, default=None)
    args = parser.parse_args()

    context_dir = (args.context or get_kma_context_dir()).resolve()
    ontology_dir = context_dir / "ontology"
    proposed = ontology_dir / "proposed.ttl"
    if not proposed.exists():
        print("No proposed.ttl to merge", file=sys.stderr)
        return 1

    tbox = ensure_context_tbox(ontology_dir)
    g, _, dangling, counts = build_deterministic_graph(context_dir, tbox_path=tbox)
    g = merge_proposals_into_graph(g, proposed)
    validation = validate_graph(g, extra_dangling=dangling)
    write_ontology_outputs(ontology_dir, g, validation=validation, counts=counts)
    proposed.write_text("# merged — clear or regenerate via enrichment\n", encoding="utf-8")
    print(f"Merged proposals into {ontology_dir / 'graph.ttl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
