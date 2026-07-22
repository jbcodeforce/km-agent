"""Extract RDF triples from the shared context manifest."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Literal

from kma.ontology.namespaces import ONTO, RDF_TYPE, RDFS_LABEL, WIKI_PATH
from kma.ontology.slug import raw_iri, summary_iri, concept_slug_from_path
from kma.tools.ingest import _entry_file_id, _read_manifest, split_file_id


def add_manifest_triples(
    g: Graph,
    context_dir: Path,
    *,
    studies_docs_dir: Path | None = None,
    label_prefix: str = "",
) -> int:
    """Add RawDocument individuals and compiledInto edges when summaries exist.

    Reads the single ``context/.manifest.json``. ``studies_docs_dir`` and
    ``label_prefix`` are retained for call-site compatibility but unused for I/O.
    """
    _ = studies_docs_dir, label_prefix
    edges = 0
    wiki_dir = context_dir / "wiki"
    for entry in _read_manifest(context_dir):
        file_id = _entry_file_id(entry)
        if not file_id:
            continue
        label, rel = split_file_id(file_id)
        subj = raw_iri(file_id)
        g.add((subj, RDF_TYPE, ONTO.RawDocument))
        title = entry.get("title") or rel
        g.add((subj, RDFS_LABEL, Literal(title)))
        g.add((subj, WIKI_PATH, Literal(f"raw/{label}/{rel}")))

        if entry.get("compiled"):
            summary_name = Path(rel).stem + ".md"
            summary_path = wiki_dir / "summaries" / summary_name
            if summary_path.exists():
                s_slug = concept_slug_from_path(summary_name)
                obj = summary_iri(s_slug)
                g.add((subj, ONTO.compiledInto, obj))
                edges += 1

    return edges
