"""Tests for ontology reason module (no owlapy required)."""

from pathlib import Path

from rdflib import Graph

from kma.ontology.reason import infer_closure


def test_infer_closure_without_owlapy(tmp_path: Path) -> None:
    ontology_dir = tmp_path / "ontology"
    ontology_dir.mkdir()
    g = Graph()
    g.parse(
        data="@prefix kma: <http://km-agent.local/ontology#> .\nkma:Concept a <http://www.w3.org/2000/01/rdf-schema#Class> .",
        format="turtle",
    )
    out = infer_closure(ontology_dir, g)
    print(out)
    assert out is not None
    assert out.exists()
