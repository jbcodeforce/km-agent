"""Extract code artifacts and doc↔code links from studies repos."""

from __future__ import annotations

import json
from pathlib import Path

from rdflib import Graph, Literal

from kma.ontology.frontmatter import extract_code_path_refs, read_wiki_frontmatter
from kma.ontology.namespaces import ONTO, RDF_TYPE, RDFS_LABEL, WIKI_PATH
from kma.ontology.slug import code_iri, concept_iri, concept_slug_from_path, statement_iri, summary_iri


def _add_code_file(g: Graph, rel: str) -> None:
    subj = code_iri(rel)
    g.add((subj, RDF_TYPE, ONTO.CodeArtifact))
    g.add((subj, RDFS_LABEL, Literal(Path(rel).name)))
    g.add((subj, WIKI_PATH, Literal(rel)))


def scan_deploy_manifests(g: Graph, studies_root: Path) -> int:
    """Parse ``code/**/deploy_manifest.json`` statement groups."""
    code_root = studies_root / "code"
    if not code_root.is_dir():
        return 0
    count = 0
    for manifest_path in sorted(code_root.rglob("deploy_manifest.json")):
        rel_manifest = manifest_path.relative_to(studies_root).as_posix()
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        groups = data.get("groups") or {}
        cc_dir = manifest_path.parent
        for group_name, entries in groups.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get("name", ""))
                file_name = str(entry.get("file", ""))
                if not file_name:
                    continue
                sql_path = (cc_dir / file_name).resolve()
                if not sql_path.is_file():
                    continue
                sql_rel = sql_path.relative_to(studies_root).as_posix()
                _add_code_file(g, sql_rel)
                stmt = statement_iri(rel_manifest, group_name, name or file_name)
                g.add((stmt, RDF_TYPE, ONTO.Statement))
                g.add((stmt, RDFS_LABEL, Literal(name or file_name)))
                artifact = code_iri(sql_rel)
                g.add((artifact, ONTO.hasStatement, stmt))
                g.add((stmt, ONTO.statementFile, artifact))
                count += 1
    return count


def link_docs_to_code(
    g: Graph,
    context_dir: Path,
    studies_root: Path | None,
) -> int:
    """Link summaries/concepts to code paths from frontmatter and markdown refs."""
    edges = 0
    wiki_dir = context_dir / "wiki"
    search_roots: list[Path] = []
    if studies_root:
        search_roots.append(studies_root / "docs")
    search_roots.append(context_dir / "raw")

    def link_paths(from_iri, paths: list[str], pred) -> None:
        nonlocal edges
        for p in paths:
            norm = p.replace("\\", "/").strip()
            if studies_root and not norm.startswith("code/"):
                candidate = (studies_root / norm).resolve()
                if candidate.exists():
                    rel = candidate.relative_to(studies_root).as_posix()
                    _add_code_file(g, rel)
                    g.add((from_iri, pred, code_iri(rel)))
                    edges += 1
                    continue
            if norm.startswith("code/") and studies_root:
                full = studies_root / norm
                if full.is_dir():
                    for sql in full.rglob("*.sql"):
                        rel = sql.relative_to(studies_root).as_posix()
                        _add_code_file(g, rel)
                        g.add((from_iri, pred, code_iri(rel)))
                        edges += 1
                elif full.is_file():
                    _add_code_file(g, norm)
                    g.add((from_iri, pred, code_iri(norm)))
                    edges += 1

    for subdir, pred in (
        ("summaries", ONTO.documents),
        ("concepts", ONTO.implements),
    ):
        d = wiki_dir / subdir
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.md")):
            fm, body = read_wiki_frontmatter(path)
            slug = concept_slug_from_path(path.name)
            if subdir == "summaries":
                from_iri = summary_iri(slug)
            else:
                from_iri = concept_iri(slug)
            refs = list(fm.code) + extract_code_path_refs(body)
            link_paths(from_iri, refs, pred)

    return edges
