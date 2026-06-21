"""Unit tests for ontology navigator tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from kma.tools.builder import build_navigator_tools
from kma.tools.ontology_tools import create_ontology_tools


@pytest.fixture
def wiki_context(tmp_path: Path) -> Path:
    import shutil

    from kma.ontology.builder import rebuild_ontology

    root = Path(__file__).resolve().parents[1] / "data"
    ctx = tmp_path / "context"
    shutil.copytree(root / "wiki", ctx / "wiki")
    shutil.copytree(root / "raw", ctx / "raw")
    rebuild_ontology(ctx, studies_root=root / "studies-code")
    return ctx


def test_navigator_tool_bundle_includes_ontology_tools(wiki_context: Path) -> None:
    from kma.db import create_knowledge

    knowledge = create_knowledge("test knowledge", "kma_knowledge_ut_ontology_tools")
    names = {t.name for t in build_navigator_tools(knowledge, context_dir=wiki_context)}
    assert "find_wiki_concepts" in names
    assert "read_wiki_graph" in names
    assert "query_ontology" in names


def test_find_wiki_concepts_tool_returns_paths(wiki_context: Path) -> None:
    tools = create_ontology_tools(wiki_context)
    find_tool = next(t for t in tools if t.name == "find_wiki_concepts")
    raw = find_tool.entrypoint(query="Apache Flink Kafka Streams", expand_neighbors=1, max_results=5)
    assert "wiki/concepts/apache-flink.md" in raw
    assert "wiki/concepts/kafka-streams.md" in raw
