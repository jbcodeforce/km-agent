"""Extract RDF triples from wiki markdown."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Literal, URIRef

from kma.ontology.frontmatter import extract_body_wikilinks, read_wiki_frontmatter
from kma.ontology.namespaces import ONTO, RDF_TYPE, RDFS_LABEL, WIKI_PATH
from kma.ontology.slug import (
    concept_iri,
    concept_slug_from_path,
    concept_slug_from_title,
    raw_iri,
    summary_iri,
)


class ConceptRegistry:
    """Maps display names and slugs to concept IRIs while building the graph."""

    def __init__(self) -> None:
        self.by_slug: dict[str, URIRef] = {}
        self.by_title: dict[str, URIRef] = {}

    def register(self, slug: str, title: str) -> URIRef:
        iri = concept_iri(slug)
        self.by_slug[slug] = iri
        self.by_title[title.lower()] = iri
        return iri

    def resolve(self, name: str, link_target: str | None = None) -> URIRef | None:
        if link_target:
            slug = concept_slug_from_path(link_target)
            if slug in self.by_slug:
                return self.by_slug[slug]
        slug = concept_slug_from_title(name)
        if slug in self.by_slug:
            return self.by_slug[slug]
        if name.lower() in self.by_title:
            return self.by_title[name.lower()]
        return None


def _index_concepts(wiki_dir: Path, registry: ConceptRegistry) -> None:
    concepts_dir = wiki_dir / "concepts"
    if not concepts_dir.is_dir():
        return
    for path in sorted(concepts_dir.glob("*.md")):
        fm, _ = read_wiki_frontmatter(path)
        slug = concept_slug_from_path(f"wiki/concepts/{path.name}")
        registry.register(slug, fm.title or path.stem)


def add_wiki_triples(
    g: Graph,
    context_dir: Path,
    registry: ConceptRegistry,
    *,
    dangling_related: list[str],
) -> dict[str, int]:
    wiki_dir = context_dir / "wiki"
    counts = {"concepts": 0, "summaries": 0, "edges": 0}

    _index_concepts(wiki_dir, registry)

    concepts_dir = wiki_dir / "concepts"
    if concepts_dir.is_dir():
        for path in sorted(concepts_dir.glob("*.md")):
            rel = f"wiki/concepts/{path.name}"
            fm, body = read_wiki_frontmatter(path)
            slug = concept_slug_from_path(rel)
            subj = registry.register(slug, fm.title or path.stem)
            g.add((subj, RDF_TYPE, ONTO.Concept))
            g.add((subj, RDFS_LABEL, Literal(fm.title or path.stem)))
            g.add((subj, WIKI_PATH, Literal(rel)))
            counts["concepts"] += 1

            for src in fm.sources:
                src_norm = src.replace("\\", "/").lstrip("/")
                if src_norm.startswith("raw/"):
                    src_norm = src_norm[4:]
                g.add((subj, ONTO.derivedFrom, raw_iri(src_norm)))
                counts["edges"] += 1

            for tag in fm.tags:
                tag_iri = URIRef(f"http://km-agent.local/id/tag/{tag}")
                g.add((tag_iri, RDF_TYPE, ONTO.Tag))
                g.add((tag_iri, RDFS_LABEL, Literal(tag)))
                g.add((subj, ONTO.hasTag, tag_iri))
                counts["edges"] += 1

            for rel_name in fm.related:
                obj = registry.resolve(rel_name)
                if obj is None:
                    dangling_related.append(f"{fm.title}:related:{rel_name}")
                    continue
                g.add((subj, ONTO.relatedTo, obj))
                counts["edges"] += 1

            for label, target in extract_body_wikilinks(body):
                if "concepts/" not in target and not target.endswith(".md"):
                    continue
                obj = registry.resolve(label, target)
                if obj is None:
                    dangling_related.append(f"{fm.title}:wikilink:{label}")
                    continue
                if (subj, ONTO.relatedTo, obj) not in g:
                    g.add((subj, ONTO.relatedTo, obj))
                    counts["edges"] += 1

    summaries_dir = wiki_dir / "summaries"
    if summaries_dir.is_dir():
        for path in sorted(summaries_dir.glob("*.md")):
            rel = f"wiki/summaries/{path.name}"
            fm, _ = read_wiki_frontmatter(path)
            slug = concept_slug_from_path(path.name)
            subj = summary_iri(slug)
            g.add((subj, RDF_TYPE, ONTO.Summary))
            g.add((subj, RDFS_LABEL, Literal(fm.title or path.stem)))
            g.add((subj, WIKI_PATH, Literal(rel)))
            counts["summaries"] += 1

    index_path = wiki_dir / "index.md"
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if "wiki/concepts/" not in line:
                continue
            start = line.find("wiki/concepts/")
            if start == -1:
                continue
            rest = line[start:]
            end = rest.find(")")
            wiki_rel = rest[: end if end != -1 else len(rest)].strip()
            slug = concept_slug_from_path(wiki_rel)
            if slug in registry.by_slug:
                subj = registry.by_slug[slug]
                g.add((subj, ONTO.indexedIn, URIRef("http://km-agent.local/id/wiki-index")))
                counts["edges"] += 1

    return counts
