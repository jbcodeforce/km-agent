"""Validate assembled ontology graphs."""

from __future__ import annotations

from dataclasses import dataclass, field

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from kma.ontology.namespaces import ONTO


@dataclass
class ValidationReport:
    ok: bool
    issues: list[str] = field(default_factory=list)
    dangling_related: list[str] = field(default_factory=list)


def validate_graph(g: Graph, *, extra_dangling: list[str] | None = None) -> ValidationReport:
    issues: list[str] = []
    dangling = list(extra_dangling or [])

    known_concepts = set(g.subjects(RDF.type, ONTO.Concept))

    for s, _, o in g.triples((None, ONTO.relatedTo, None)):
        if isinstance(o, URIRef) and o not in known_concepts:
            msg = f"dangling relatedTo target: {o} from {s}"
            issues.append(msg)
            dangling.append(msg)

    ok = len(issues) == 0
    return ValidationReport(ok=ok, issues=issues, dangling_related=dangling)
