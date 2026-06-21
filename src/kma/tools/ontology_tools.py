"""Navigator/Linter tools for the OWL wiki graph."""

from __future__ import annotations

import json
from pathlib import Path

from agno.tools import tool
from rdflib import Graph

from kma.ontology.retrieval import find_wiki_concepts_in_graph, load_graph_ttl


def create_ontology_tools(context_dir: Path) -> list:
    """Tools to read graph.json and run simple SPARQL."""
    base = context_dir.resolve()
    ontology_dir = base / "ontology"

    def _load_graph_ttl() -> Graph | None:
        ttl = ontology_dir / "graph.ttl"
        if not ttl.exists():
            return None
        return load_graph_ttl(ttl)

    @tool
    def read_wiki_graph(concept_slug: str = "", max_neighbors: int = 20) -> str:
        """Load the derived wiki knowledge graph (nodes and edges).

        Args:
            concept_slug: Optional concept slug (e.g. ``apache-flink``) to filter neighbors.
            max_neighbors: Max edges to return when filtering by concept.

        Returns:
            JSON summary of nodes and edges from context/ontology/graph.json.
        """
        path = ontology_dir / "graph.json"
        if not path.exists():
            return "Ontology graph not built yet. Run scripts/build_ontology.py or enable KMA_ONTOLOGY_ENABLED."
        data = json.loads(path.read_text(encoding="utf-8"))
        if not concept_slug:
            return json.dumps(
                {
                    "node_count": len(data.get("nodes", [])),
                    "edge_count": len(data.get("edges", [])),
                    "sample_edges": data.get("edges", [])[:max_neighbors],
                },
                indent=2,
            )
        needle = f"/concept/{concept_slug}"
        edges = [
            e
            for e in data.get("edges", [])
            if needle in e.get("from", "") or needle in e.get("to", "")
        ][:max_neighbors]
        nodes = {
            n["id"]: n
            for n in data.get("nodes", [])
            if needle in n.get("id", "")
            or any(needle in e.get("from", "") or needle in e.get("to", "") for e in edges)
        }
        return json.dumps({"concept_slug": concept_slug, "nodes": list(nodes.values()), "edges": edges}, indent=2)

    @tool
    def find_wiki_concepts(query: str, expand_neighbors: int = 1, max_results: int = 10) -> str:
        """Find wiki article paths by matching the ontology graph (labels, tags, neighbors).

        Prefer this over writing SPARQL for routing. Returns ``wiki_path`` values for
        ``read_file`` (e.g. ``wiki/concepts/apache-flink.md``).

        Args:
            query: Natural language question or topic keywords.
            expand_neighbors: How many ``relatedTo`` hops to include (default 1).
            max_results: Max paths to return (default 10).
        """
        g = _load_graph_ttl()
        if g is None:
            return "Ontology graph not built yet. Run scripts/build_ontology.py or enable KMA_ONTOLOGY_ENABLED."
        results = find_wiki_concepts_in_graph(
            g,
            query,
            expand_neighbors=expand_neighbors,
            max_results=max_results,
        )
        if not results:
            return "[]"
        return json.dumps(results, indent=2)

    @tool
    def query_ontology(sparql: str) -> str:
        """Run a read-only SPARQL query against context/ontology/graph.ttl.

        Example: SELECT ?c ?label WHERE { ?c a <http://km-agent.local/ontology#Concept> ; rdfs:label ?label } LIMIT 10
        """
        g = _load_graph_ttl()
        if g is None:
            return "Ontology graph not built yet."
        try:
            rows = list(g.query(sparql))
        except Exception as e:
            return f"SPARQL error: {e}"
        out = [str(row) for row in rows[:50]]
        return json.dumps(out, indent=2) if out else "[]"

    @tool
    def read_ontology_validation() -> str:
        """Return ontology build validation state from context/ontology/.state.json."""
        state_path = ontology_dir / ".state.json"
        if not state_path.exists():
            return "No ontology state yet."
        return state_path.read_text(encoding="utf-8")

    return [read_wiki_graph, find_wiki_concepts, query_ontology, read_ontology_validation]
