"""Unit tests for OWL/RDF ontology builder."""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Graph

from kma.ontology.builder import build_deterministic_graph, rebuild_ontology
from kma.ontology.merge import merge_proposals_into_graph, write_proposed_triples
from kma.ontology.namespaces import ONTO
from kma.ontology.slug import concept_iri

ROOT = Path(__file__).resolve().parents[1]
WIKI_CONTEXT = ROOT / "data"
STUDIES_FIXTURE = ROOT / "data" / "studies-code"


@pytest.fixture
def wiki_context(tmp_path: Path) -> Path:
    """Copy wiki + raw fixture into temp context dir."""
    import shutil

    ctx = tmp_path / "context"
    shutil.copytree(WIKI_CONTEXT / "wiki", ctx / "wiki")
    shutil.copytree(WIKI_CONTEXT / "raw", ctx / "raw")
    return ctx


def test_build_wiki_related_edges(wiki_context: Path) -> None:
    g, _, dangling, counts = build_deterministic_graph(wiki_context)
    assert counts["concepts"] >= 5
    flink = concept_iri("apache-flink")
    kafka_streams = concept_iri("kafka-streams")
    assert (flink, ONTO.relatedTo, kafka_streams) in g
    assert any("Apache Kafka" in d for d in dangling)


def test_code_artifact_from_manifest(wiki_context: Path) -> None:
    g, _, _, counts = build_deterministic_graph(
        wiki_context,
        studies_root=STUDIES_FIXTURE,
    )
    assert counts["code_statements"] >= 1
    sql_nodes = list(g.subjects(ONTO.statementFile, None))
    assert len(sql_nodes) >= 1


def test_rebuild_writes_outputs(wiki_context: Path) -> None:
    result = rebuild_ontology(wiki_context, studies_root=STUDIES_FIXTURE)
    ontology_dir = wiki_context / "ontology"
    assert (ontology_dir / "graph.ttl").exists()
    assert (ontology_dir / "graph.json").exists()
    assert (ontology_dir / "tbox.ttl").exists()
    assert result.state_path is not None
    assert result.state_path.exists()


def test_merge_proposals(wiki_context: Path) -> None:
    g, _, _, _ = build_deterministic_graph(wiki_context)
    proposed_path = wiki_context / "ontology" / "proposed.ttl"
    proposed_path.parent.mkdir(parents=True, exist_ok=True)
    missing = concept_iri("apache-kafka")
    write_proposed_triples(
        proposed_path,
        [
            (missing, ONTO.relatedTo, concept_iri("apache-flink")),
        ],
    )
    merged = merge_proposals_into_graph(g, proposed_path)
    assert (missing, ONTO.relatedTo, concept_iri("apache-flink")) in merged


def test_enrichment_stub_from_gaps(wiki_context: Path) -> None:
    from kma.ontology.enrich import run_enrichment

    ontology_dir = wiki_context / "ontology"
    ontology_dir.mkdir(parents=True, exist_ok=True)
    gaps = ["Apache Flink:related:Apache Kafka"]
    path = run_enrichment(wiki_context, gaps, ontology_dir)
    g = Graph()
    g.parse(path, format="turtle")
    assert concept_iri("apache-kafka") in set(g.subjects(None, None))
