"""Extract RDF triples from raw manifest files."""

from __future__ import annotations

import json
from pathlib import Path

from rdflib import Graph, Literal

from kma.ontology.namespaces import ONTO, RDF_TYPE, RDFS_LABEL, WIKI_PATH
from kma.ontology.slug import raw_iri, summary_iri, concept_slug_from_path


def _read_manifest(raw_dir: Path) -> list[dict]:
    path = raw_dir / ".manifest.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def add_manifest_triples(
    g: Graph,
    context_dir: Path,
    *,
    studies_docs_dir: Path | None = None,
    label_prefix: str = "",
) -> int:
    """Add RawDocument individuals and compiledInto edges when summaries exist."""
    edges = 0

    def process_raw_root(raw_dir: Path, prefix: str) -> None:
        nonlocal edges
        wiki_dir = context_dir / "wiki"
        for entry in _read_manifest(raw_dir):
            rel = str(entry.get("file", "")).replace("\\", "/")
            if not rel:
                continue
            file_key = f"{prefix}:{rel}" if prefix else rel
            subj = raw_iri(file_key)
            g.add((subj, RDF_TYPE, ONTO.RawDocument))
            title = entry.get("title") or rel
            g.add((subj, RDFS_LABEL, Literal(title)))
            g.add((subj, WIKI_PATH, Literal(f"raw/{file_key}" if prefix else f"raw/{rel}")))

            if entry.get("compiled"):
                summary_name = Path(rel).stem + ".md"
                summary_path = wiki_dir / "summaries" / summary_name
                if summary_path.exists():
                    s_slug = concept_slug_from_path(summary_name)
                    obj = summary_iri(s_slug)
                    g.add((subj, ONTO.compiledInto, obj))
                    edges += 1

    process_raw_root(context_dir / "raw", label_prefix or "")
    if studies_docs_dir and studies_docs_dir.is_dir():
        process_raw_root(studies_docs_dir, "studies")

    return edges
