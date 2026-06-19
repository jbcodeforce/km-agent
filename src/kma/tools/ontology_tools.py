"""Navigator/Linter tools for the OWL wiki graph."""

from __future__ import annotations

import json
from pathlib import Path

from agno.tools import tool
from rdflib import Graph


def create_ontology_tools(context_dir: Path) -> list:
    """Tools to read graph.json and run simple SPARQL."""
    base = context_dir.resolve()
    ontology_dir = base / "ontology"

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
    def query_ontology(sparql: str) -> str:
        """Run a read-only SPARQL query against context/ontology/graph.ttl.

        Example: SELECT ?c ?label WHERE { ?c a <http://km-agent.local/ontology#Concept> ; rdfs:label ?label } LIMIT 10
        """
        ttl = ontology_dir / "graph.ttl"
        if not ttl.exists():
            return "Ontology graph not built yet."
        g = Graph()
        g.parse(ttl, format="turtle")
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

    return [read_wiki_graph, query_ontology, read_ontology_validation]
