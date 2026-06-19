"""OWL reasoning via owlapy (optional)."""

from __future__ import annotations

import logging
from pathlib import Path

from rdflib import Graph

logger = logging.getLogger(__name__)


def infer_closure(ontology_dir: Path, g: Graph) -> Path | None:
    """Run StructuralReasoner when owlapy is available; write graph-inferred.ttl."""
    out_path = ontology_dir / "graph-inferred.ttl"
    try:
        from owlapy.owl_reasoner import StructuralReasoner  # type: ignore[import-untyped]
        from owlapy.owl_ontology import Ontology  # type: ignore[import-untyped]
    except ImportError:
        logger.info("owlapy not installed; skipping reasoning")
        g.serialize(destination=str(out_path), format="turtle")
        return out_path

    tmp = ontology_dir / "_reason_input.ttl"
    g.serialize(destination=str(tmp), format="turtle")
    try:
        onto = Ontology(str(tmp))
        reasoner = StructuralReasoner(onto)
        enriched = Graph()
        enriched += g
        for cls in onto.classes_in_signature():
            try:
                instances = reasoner.instances(cls, direct=False)
            except Exception:
                continue
            for ind in instances:
                enriched.add((ind.iri, Graph().namespace_manager.expand_curie("rdf:type"), cls.iri))
        enriched.serialize(destination=str(out_path), format="turtle")
    except Exception as e:
        logger.warning("StructuralReasoner failed: %s", e)
        g.serialize(destination=str(out_path), format="turtle")
    finally:
        tmp.unlink(missing_ok=True)
    return out_path
