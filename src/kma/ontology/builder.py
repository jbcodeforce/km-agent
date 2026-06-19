"""Assemble ontology graphs and write outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from kma.ontology.extract_code import link_docs_to_code, scan_deploy_manifests
from kma.ontology.extract_manifest import add_manifest_triples
from kma.ontology.extract_wiki import ConceptRegistry, add_wiki_triples
from kma.ontology.merge import merge_proposals_into_graph
from kma.ontology.namespaces import ONTO
from kma.ontology.tbox import ensure_context_tbox, load_tbox
from kma.ontology.validate import ValidationReport, validate_graph


@dataclass
class BuildResult:
    graph: Graph
    validation: ValidationReport
    counts: dict[str, int] = field(default_factory=dict)
    state_path: Path | None = None


def graph_to_json(g: Graph) -> dict:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for s, p, o in g:
        if isinstance(s, URIRef):
            sid = str(s)
            if sid not in nodes:
                nodes[sid] = {"id": sid, "types": [], "label": sid.rsplit("/", 1)[-1]}
            if p == RDF.type and isinstance(o, URIRef):
                nodes[sid]["types"].append(str(o))
            if str(p).endswith("label") and hasattr(o, "value"):
                nodes[sid]["label"] = str(o)

        if isinstance(s, URIRef) and isinstance(o, URIRef) and p != RDF.type:
            edges.append({"from": str(s), "predicate": str(p), "to": str(o)})

    return {"nodes": list(nodes.values()), "edges": edges}


def build_deterministic_graph(
    context_dir: Path,
    *,
    studies_root: Path | None = None,
    studies_docs_dir: Path | None = None,
    tbox_path: Path | None = None,
) -> tuple[Graph, ConceptRegistry, list[str], dict[str, int]]:
    context_dir = context_dir.resolve()
    g = load_tbox(tbox_path)
    registry = ConceptRegistry()
    dangling: list[str] = []

    wiki_counts = add_wiki_triples(g, context_dir, registry, dangling_related=dangling)
    manifest_edges = add_manifest_triples(
        g,
        context_dir,
        studies_docs_dir=studies_docs_dir,
        label_prefix="studies",
    )
    code_count = 0
    doc_code_edges = 0
    if studies_root:
        code_count = scan_deploy_manifests(g, studies_root.resolve())
        doc_code_edges = link_docs_to_code(g, context_dir, studies_root.resolve())

    counts = {
        **wiki_counts,
        "manifest_edges": manifest_edges,
        "code_statements": code_count,
        "doc_code_edges": doc_code_edges,
    }
    return g, registry, dangling, counts


def write_ontology_outputs(
    ontology_dir: Path,
    g: Graph,
    *,
    validation: ValidationReport,
    counts: dict[str, int],
    gaps: list[str] | None = None,
) -> Path:
    ontology_dir.mkdir(parents=True, exist_ok=True)
    graph_ttl = ontology_dir / "graph.ttl"
    g.serialize(destination=str(graph_ttl), format="turtle")
    graph_json = ontology_dir / "graph.json"
    graph_json.write_text(json.dumps(graph_to_json(g), indent=2) + "\n", encoding="utf-8")

    proposed = ontology_dir / "proposed.ttl"
    if not proposed.exists():
        Graph().serialize(destination=str(proposed), format="turtle")

    state = {
        "last_built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": counts,
        "validation_ok": validation.ok,
        "validation_issues": validation.issues,
        "dangling_related": validation.dangling_related,
        "gap_queue": gaps or [],
    }
    state_path = ontology_dir / ".state.json"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state_path


def rebuild_ontology(
    context_dir: Path,
    *,
    studies_root: Path | None = None,
    studies_docs_dir: Path | None = None,
    merge_proposals: bool = True,
    run_enrichment: bool = False,
    run_reasoning: bool = False,
) -> BuildResult:
    """Full deterministic rebuild; optionally merge proposals, enrich, reason."""
    context_dir = context_dir.resolve()
    ontology_dir = context_dir / "ontology"
    tbox_dest = ensure_context_tbox(ontology_dir)

    g, _registry, dangling, counts = build_deterministic_graph(
        context_dir,
        studies_root=studies_root,
        studies_docs_dir=studies_docs_dir,
        tbox_path=tbox_dest,
    )

    if merge_proposals:
        proposed_path = ontology_dir / "proposed.ttl"
        if proposed_path.exists() and proposed_path.stat().st_size > 10:
            g = merge_proposals_into_graph(g, proposed_path)

    validation = validate_graph(g, extra_dangling=dangling)
    gaps = list(validation.dangling_related)

    if run_enrichment and gaps:
        from kma.ontology.enrich import run_enrichment as do_enrich

        do_enrich(context_dir, gaps, ontology_dir)

    state_path = write_ontology_outputs(
        ontology_dir, g, validation=validation, counts=counts, gaps=gaps
    )

    if run_reasoning:
        from kma.ontology.reason import infer_closure

        infer_closure(ontology_dir, g)

    return BuildResult(graph=g, validation=validation, counts=counts, state_path=state_path)
