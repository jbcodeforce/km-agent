# Ontology (OWL/RDF) layer

Formal knowledge graph derived from the markdown wiki, raw manifest, and optional studies-repo code tree. Markdown remains the source of truth; Turtle RDF is a rebuildable view.

See also [`ARCHITECTURE_WIKI_RAG.md`](./ARCHITECTURE_WIKI_RAG.md) for how ontology relates to Knowledge, Learnings, and Wiki.

## Layout

```
context/ontology/
  tbox.ttl       # Locked schema (classes and properties)
  graph.ttl      # Merged ABox (deterministic + approved proposals)
  graph.json     # Node/edge export for Navigator tools
  proposed.ttl   # Pending LLM gap-fill triples (review before merge)
  .state.json    # Last build, validation, gap queue
  graph-inferred.ttl   # Optional: owlapy StructuralReasoner output
```

Bundled TBox source: [`src/kma/ontology/data/tbox.ttl`](../src/kma/ontology/data/tbox.ttl).

## Build

```bash
# Install optional owlapy for reasoning / AGen-KG
uv sync --extra ontology

# Rebuild from wiki + raw (+ studies code when KMA_STUDIES_ROOT is set)
uv run python scripts/build_ontology.py \
  --context ./context \
  --studies-root /path/to/flink-studies

# Approve proposed.ttl after review
uv run python scripts/approve_ontology_proposals.py --context ./context
```

## Environment

| Variable | Purpose |
|----------|---------|
| `KMA_STUDIES_ROOT` | Studies repo root; scans `code/**/deploy_manifest.json` and resolves `code/…` links |
| `KMA_ONTOLOGY_ENABLED=1` | Auto-rebuild after `refresh_wiki_from_raw` (compile + lint) |
| `KMA_ONTOLOGY_ENRICH=1` | Write gap proposals to `proposed.ttl` after build |

## Hybrid enrichment

1. Deterministic builder extracts concepts, `relatedTo`, manifest `compiledInto`, and code artifacts.
2. Validator records dangling `related` refs (e.g. missing concept articles).
3. When `KMA_ONTOLOGY_ENRICH=1`, stub proposals (or owlapy AGen-KG / mykg append when installed) land in `proposed.ttl`.
4. Human or script approval merges into `graph.ttl` without changing wiki markdown.

## Agent tools

| Tool | Agent | Role |
|------|-------|------|
| `find_wiki_concepts` | Navigator | Label/tag match + `relatedTo` neighbors → `wiki_path` list |
| `read_wiki_graph` | Navigator | Neighbors / graph summary from `graph.json` |
| `query_ontology` | Navigator | SPARQL over `graph.ttl` |
| `read_ontology_validation` | Navigator, Linter | Validation state from `.state.json` |

## SPARQL example

```sparql
PREFIX kma: <http://km-agent.local/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?code ?label WHERE {
  ?concept kma:implements ?code .
  ?code rdfs:label ?label .
  FILTER(CONTAINS(STR(?concept), "flink-sql-joins"))
}
LIMIT 20
```

## Relation to mykg and owlapy

- **mykg**: inspiration for schema-guided TTL and validation; km-agent does not run full two-pass mykg extraction on the corpus. Optional `mykg extract-graph --append` can feed `proposed.ttl`.
- **owlapy**: optional `uv sync --extra ontology` for StructuralReasoner (`--reason`) and AGen-KG enrichment.
