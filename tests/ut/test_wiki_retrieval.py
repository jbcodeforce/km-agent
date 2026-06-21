"""Unit tests for wiki retrieval helpers and gold question set."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kma.ontology.builder import rebuild_ontology
from kma.ontology.retrieval import (
    find_wiki_concepts_in_graph,
    hit_at_1,
    load_graph_ttl,
    mrr,
    query_tokens,
    recall_at_k,
    search_wiki_index,
    wiki_paths_from_graph_query,
)

ROOT = Path(__file__).resolve().parents[1]
WIKI_CONTEXT = ROOT / "data"
QUESTIONS_PATH = WIKI_CONTEXT / "wiki_eval" / "questions.jsonl"
STUDIES_FIXTURE = WIKI_CONTEXT / "studies-code"


@pytest.fixture
def wiki_context(tmp_path: Path) -> Path:
    import shutil

    ctx = tmp_path / "context"
    shutil.copytree(WIKI_CONTEXT / "wiki", ctx / "wiki")
    shutil.copytree(WIKI_CONTEXT / "raw", ctx / "raw")
    rebuild_ontology(ctx, studies_root=STUDIES_FIXTURE)
    return ctx


def test_query_tokens_filters_short_words() -> None:
    tokens = query_tokens("How do Flink SQL joins work?")
    assert "flink" in tokens
    assert "sql" in tokens
    assert "do" not in tokens


def test_search_wiki_index_matches_concepts() -> None:
    index_text = (WIKI_CONTEXT / "wiki" / "index.md").read_text(encoding="utf-8")
    paths = search_wiki_index(index_text, "Apache Flink compare Kafka Streams", max_results=5)
    assert "wiki/concepts/apache-flink.md" in paths
    assert "wiki/concepts/kafka-streams.md" in paths


def test_ontology_find_expands_neighbors(wiki_context: Path) -> None:
    graph = load_graph_ttl(wiki_context / "ontology" / "graph.ttl")
    results = find_wiki_concepts_in_graph(
        graph,
        "Flink complex event processing patterns",
        expand_neighbors=1,
        max_results=8,
    )
    paths = [str(r["wiki_path"]) for r in results]
    assert "wiki/concepts/apache-flink.md" in paths
    assert "wiki/concepts/complex-event-processing.md" in paths


def test_recall_metrics() -> None:
    gold = ["wiki/concepts/a.md", "wiki/concepts/b.md"]
    retrieved = ["wiki/concepts/b.md", "wiki/concepts/c.md"]
    assert recall_at_k(retrieved, gold, k=2) == 0.5
    assert mrr(retrieved, gold) == 1.0
    assert hit_at_1(retrieved, gold) == 1.0


def test_gold_questions_file_loads() -> None:
    rows = [json.loads(line) for line in QUESTIONS_PATH.read_text().splitlines() if line.strip()]
    assert len(rows) >= 5
    for row in rows:
        assert row["id"]
        assert row["question"]
        assert row["gold_paths"]


def test_gold_questions_ontology_recall(wiki_context: Path) -> None:
    graph = load_graph_ttl(wiki_context / "ontology" / "graph.ttl")
    rows = [json.loads(line) for line in QUESTIONS_PATH.read_text().splitlines() if line.strip()]
    recalls: list[float] = []
    for row in rows:
        paths = wiki_paths_from_graph_query(graph, row["question"], expand_neighbors=1, max_results=5)
        recalls.append(recall_at_k(paths, row["gold_paths"], k=5))
    assert sum(recalls) / len(recalls) >= 0.5
