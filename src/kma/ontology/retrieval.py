"""Wiki path retrieval helpers for ontology graph, index, and eval metrics."""

from __future__ import annotations

import re
from pathlib import Path

from rdflib import Graph, URIRef

from kma.ontology.namespaces import ONTO, RDF_TYPE, RDFS_LABEL, WIKI_PATH

_TOKEN_RE = re.compile(r"\w+")
_WIKI_PATH_RE = re.compile(r"(wiki/(?:concepts|summaries)/[^\s\)]+\.md)")


def query_tokens(query: str, min_len: int = 3) -> list[str]:
    """Lowercase tokens from a natural-language query."""
    return [t.lower() for t in _TOKEN_RE.findall(query) if len(t) >= min_len]


def _label_for(g: Graph, node: URIRef) -> str:
    for label in g.objects(node, RDFS_LABEL):
        return str(label)
    return str(node).rsplit("/", 1)[-1]


def _wiki_path_for(g: Graph, node: URIRef) -> str | None:
    for path in g.objects(node, WIKI_PATH):
        return str(path)
    return None


def _score_text(text: str, tokens: list[str]) -> float:
    lower = text.lower()
    return float(sum(1 for t in tokens if t in lower))


def find_wiki_concepts_in_graph(
    g: Graph,
    query: str,
    *,
    expand_neighbors: int = 1,
    max_results: int = 10,
) -> list[dict[str, str | float]]:
    """Match concepts (and summaries) by label/tag, expand ``relatedTo``, return wiki paths."""
    tokens = query_tokens(query)
    if not tokens:
        return []

    scores: dict[URIRef, float] = {}
    labels: dict[URIRef, str] = {}
    paths: dict[URIRef, str] = {}

    for rdf_type in (ONTO.Concept, ONTO.Summary):
        for subj in g.subjects(RDF_TYPE, rdf_type):
            if not isinstance(subj, URIRef):
                continue
            label = _label_for(g, subj)
            path = _wiki_path_for(g, subj)
            if not path:
                continue
            score = _score_text(label, tokens) * 2
            for tag in g.objects(subj, ONTO.hasTag):
                tag_label = _label_for(g, tag)
                score += _score_text(tag_label, tokens)
            if score > 0:
                scores[subj] = score
                labels[subj] = label
                paths[subj] = path

    frontier = set(scores.keys())
    for _ in range(max(0, expand_neighbors)):
        next_frontier: set[URIRef] = set()
        for subj in frontier:
            base = scores.get(subj, 0.0)
            neighbors: set[URIRef] = set()
            for neighbor in g.objects(subj, ONTO.relatedTo):
                if isinstance(neighbor, URIRef):
                    neighbors.add(neighbor)
            for neighbor in g.subjects(ONTO.relatedTo, subj):
                if isinstance(neighbor, URIRef):
                    neighbors.add(neighbor)
            for neighbor in neighbors:
                path = _wiki_path_for(g, neighbor)
                if not path:
                    continue
                labels.setdefault(neighbor, _label_for(g, neighbor))
                paths[neighbor] = path
                neighbor_score = base * 0.5
                if neighbor_score > scores.get(neighbor, 0.0):
                    scores[neighbor] = neighbor_score
                if neighbor not in frontier:
                    next_frontier.add(neighbor)
        frontier = next_frontier

    ranked = sorted(scores.items(), key=lambda item: (-item[1], paths.get(item[0], "")))
    results: list[dict[str, str | float]] = []
    for subj, score in ranked[:max_results]:
        path = paths.get(subj)
        if not path:
            continue
        results.append(
            {
                "label": labels.get(subj, str(subj)),
                "wiki_path": path,
                "score": score,
            }
        )
    return results


def wiki_paths_from_graph_query(
    g: Graph,
    query: str,
    *,
    expand_neighbors: int = 1,
    max_results: int = 10,
) -> list[str]:
    """Return ordered wiki paths from ontology graph query (for eval)."""
    return [
        str(item["wiki_path"])
        for item in find_wiki_concepts_in_graph(
            g,
            query,
            expand_neighbors=expand_neighbors,
            max_results=max_results,
        )
    ]


def search_wiki_index(index_text: str, query: str, max_results: int = 10) -> list[str]:
    """Keyword match over index.md lines; return wiki relative paths."""
    tokens = query_tokens(query)
    if not tokens:
        return []

    scored: list[tuple[float, str]] = []
    for line in index_text.splitlines():
        if "wiki/" not in line:
            continue
        score = _score_text(line, tokens)
        if score <= 0:
            continue
        match = _WIKI_PATH_RE.search(line)
        if not match:
            continue
        scored.append((score, match.group(1)))

    scored.sort(key=lambda item: (-item[0], item[1]))
    seen: set[str] = set()
    paths: list[str] = []
    for _, path in scored:
        if path in seen:
            continue
        seen.add(path)
        paths.append(path)
        if len(paths) >= max_results:
            break
    return paths


def recall_at_k(retrieved: list[str], gold: list[str], k: int) -> float:
    """Fraction of gold paths present in the first k retrieved paths."""
    if not gold:
        return 1.0
    top = retrieved[:k]
    hits = sum(1 for path in gold if path in top)
    return hits / len(gold)


def mrr(retrieved: list[str], gold: list[str]) -> float:
    """Mean reciprocal rank of the first gold path in retrieved list."""
    if not gold:
        return 1.0
    for rank, path in enumerate(retrieved, start=1):
        if path in gold:
            return 1.0 / rank
    return 0.0


def hit_at_1(retrieved: list[str], gold: list[str]) -> float:
    """1.0 if any gold path is first retrieved path, else 0.0."""
    if not gold or not retrieved:
        return 0.0
    return 1.0 if retrieved[0] in gold else 0.0


def load_graph_ttl(path: Path) -> Graph:
    g = Graph()
    g.parse(path, format="turtle")
    return g
