"""Merge approved LLM proposals into the main graph."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Literal

from kma.ontology.namespaces import EXTRACTION_METHOD


def merge_proposals_into_graph(base: Graph, proposed_path: Path) -> Graph:
    """Add triples from ``proposed.ttl`` and annotate with extraction method."""
    if not proposed_path.exists():
        return base
    proposed = Graph()
    try:
        proposed.parse(proposed_path, format="turtle")
    except Exception:
        return base
    if len(proposed) == 0:
        return base

    for s, p, o in proposed:
        base.add((s, p, o))
        if p != EXTRACTION_METHOD:
            base.add((s, EXTRACTION_METHOD, Literal("mykg_append_or_agen_kg")))

    for s, _, _ in proposed.triples((None, None, None)):
        if (s, EXTRACTION_METHOD, None) not in base:
            base.add((s, EXTRACTION_METHOD, Literal("mykg_append_or_agen_kg")))

    return base


def write_proposed_triples(proposed_path: Path, triples: list[tuple]) -> None:
    """Write gap-fill proposals for human review."""
    g = Graph()
    for s, p, o in triples:
        g.add((s, p, o))
        g.add((s, EXTRACTION_METHOD, Literal("proposed")))
    proposed_path.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(proposed_path), format="turtle")
