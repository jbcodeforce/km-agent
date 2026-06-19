"""Gap-triggered LLM enrichment (hybrid leg)."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from rdflib import Graph, Literal

from kma.ontology.merge import write_proposed_triples
from kma.ontology.namespaces import ONTO, RDF_TYPE, RDF_TYPE, RDFS_LABEL
from kma.ontology.slug import concept_iri, concept_slug_from_title

logger = logging.getLogger(__name__)


def _proposals_from_gaps(gaps: list[str]) -> list[tuple]:
    """Create stub proposals for missing related concepts (no LLM)."""
    triples: list[tuple] = []
    seen: set[str] = set()
    for gap in gaps:
        parts = gap.split(":")
        if len(parts) < 3:
            continue
        kind = parts[1]
        if kind not in ("related", "wikilink"):
            continue
        name = ":".join(parts[2:])
        slug = concept_slug_from_title(name)
        if slug in seen:
            continue
        seen.add(slug)
        subj = concept_iri(slug)
        triples.append((subj, RDF_TYPE, ONTO.Concept))
        triples.append((subj, RDFS_LABEL, Literal(name)))
    return triples


def run_agen_kg_on_text(text_path: Path, output_path: Path) -> bool:
    """Run owlapy AGen-KG when installed; return True on success."""
    try:
        from owlapy.agen_kg import AGenKG  # type: ignore[import-untyped]
    except ImportError:
        logger.info("owlapy[agentic] not installed; skipping AGen-KG")
        return False

    agent = AGenKG(enable_logging=False)
    agent.generate_ontology(
        text=str(text_path),
        ontology_type="domain",
        query="Extract concepts and relationships for a technical studies wiki.",
        generate_types=True,
        extract_spl_triples=True,
        create_class_hierarchy=False,
        save_path=str(output_path.with_suffix(".owl")),
    )
    if output_path.with_suffix(".owl").exists():
        g = Graph()
        g.parse(output_path.with_suffix(".owl"))
        g.serialize(destination=str(output_path), format="turtle")
        return True
    return False


def run_mykg_append(raw_dir: Path, session_name: str) -> bool:
    """Shell out to mykg when available."""
    if shutil.which("mykg") is None:
        logger.info("mykg CLI not found; skipping mykg append")
        return False
    try:
        subprocess.run(
            ["mykg", "extract-graph", str(raw_dir), "--append", "--session", session_name],
            check=True,
            capture_output=True,
            text=True,
            timeout=600,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.warning("mykg append failed: %s", e)
        return False


def run_enrichment(context_dir: Path, gaps: list[str], ontology_dir: Path) -> Path:
    """Produce ``proposed.ttl`` from gap list (stub or external tools)."""
    proposed_path = ontology_dir / "proposed.ttl"
    triples = _proposals_from_gaps(gaps)
    if triples:
        write_proposed_triples(proposed_path, triples)
        return proposed_path

    write_proposed_triples(proposed_path, [])
    return proposed_path
