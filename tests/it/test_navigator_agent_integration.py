"""Integration test: Navigator agent with sandbox context (OMLX chat by default; embeddings from ``KMA_EMBED_PROVIDER``)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from agno.agent import Agent
from agno.run.base import RunStatus
from agno.run.agent import RunOutput

from kma.agents.instructions import BASE_INSTRUCTIONS, EXA_INSTRUCTIONS, WIKI_INSTRUCTIONS, WIKI_INSTRUCTIONS_BASELINE
from kma.agents.navigator import build_navigator_agent
from kma.ontology.builder import rebuild_ontology
from kma.ontology.retrieval import recall_at_k

IT_CONTEXT = Path(__file__).resolve().parent.parent / "data"
IT_QUESTIONS = IT_CONTEXT / "wiki_eval" / "questions.jsonl"
STUDIES_FIXTURE = IT_CONTEXT / "studies-code"

_FLINK_KAFKA_QUESTION = (
    "According to our wiki, how does Apache Flink compare to Kafka Streams? "
    "Briefly explain when you'd pick each."
)
_FLINK_KAFKA_GOLD = ["wiki/concepts/apache-flink.md", "wiki/concepts/kafka-streams.md"]

_INFRA_SKIP_TOKENS = ("memory", "not found", "requires more", "timeout", "connection error")

# Distinctive facts from tests/data/wiki (concepts + fitforpurpose summary).
_WIKI_COMPARISON_SIGNALS = (
    "java",
    "library",
    "platform",
    "cluster",
    "fault tolerance",
    "embedded",
    "batch",
)


@pytest.fixture(scope="session")
def it_context_with_ontology() -> Path:
    """Ensure tests/data has a built ontology graph for Navigator ontology tools."""
    studies = STUDIES_FIXTURE if STUDIES_FIXTURE.is_dir() else None
    rebuild_ontology(IT_CONTEXT, studies_root=studies)
    return IT_CONTEXT


def _build_it_navigator(
    kma_knowledge_it,
    kma_learnings_it,
    *,
    context_dir: Path = IT_CONTEXT,
    instructions: str | None = None,
) -> Agent:
    agent = build_navigator_agent(
        knowledge=kma_knowledge_it,
        learnings=kma_learnings_it,
        context_dir=context_dir,
        instructions=instructions,
        enable_wiki_search=False,
    )
    assert agent is not None
    assert agent.model is not None
    assert agent.model.id == "Qwen3.6-27B-PARO"
    assert type(agent.model).__name__ == "OpenAILike"
    assert agent.instructions
    return agent


def _run_navigator_agent(agent: Agent, prompt: str) -> RunOutput:
    """Stream a navigator run; skip cleanly when LLM or memory infra is unavailable."""
    final: RunOutput | None = None
    for chunk in agent.run(
        prompt,
        stream=True,
        stream_events=True,
        yield_run_output=True,
    ):
        if isinstance(chunk, RunOutput):
            final = chunk
    if final is None:
        pytest.skip("Navigator run produced no RunOutput (LLM not reachable?)")
    if final.status != RunStatus.completed:
        msg = (final.content or "").lower()
        if any(token in msg for token in _INFRA_SKIP_TOKENS):
            pytest.skip(f"Navigator run infra issue: {final.content!r}")
    assert final.status == RunStatus.completed, f"navigator run failed: {final.content!r}"
    return final


def _tool_names(final: RunOutput) -> set[str]:
    return {name for t in (final.tools or []) if (name := t.tool_name)}


def _read_file_paths(final: RunOutput) -> list[str]:
    paths: list[str] = []
    for tool in final.tools or []:
        if tool.tool_name != "read_file":
            continue
        args = tool.tool_args or {}
        file_name = args.get("file_name") or args.get("path")
        if file_name:
            paths.append(str(file_name).replace("\\", "/").lstrip("/"))
    return paths


def _wiki_paths_from_tool_results(final: RunOutput) -> list[str]:
    """Collect wiki paths from read_file args and find_wiki_concepts JSON results."""
    paths = _read_file_paths(final)
    for tool in final.tools or []:
        if tool.tool_name != "find_wiki_concepts" or not tool.result:
            continue
        try:
            rows = json.loads(tool.result)
        except json.JSONDecodeError:
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and row.get("wiki_path"):
                paths.append(str(row["wiki_path"]))
    return paths


@pytest.mark.usefixtures("require_postgres")
def test_navigator_reads_wiki_index(
    kma_knowledge_it,
    kma_learnings_it,
) -> None:
    agent = _build_it_navigator(kma_knowledge_it, kma_learnings_it)
    prompt = (
        "You are in an automated integration test. Use your tools only (no user questions).\n"
        "1) Call read_wiki_index.\n"
        "2) If the wiki index lists Apache Flink in the Concepts section, your final line must be "
        "exactly: NAV_IT_OK\n"
        "Otherwise your final line must be exactly: NAV_IT_FAIL\n"
        "Keep the rest of the response short."
    )
    final = _run_navigator_agent(agent, prompt)
    assert "NAV_IT_OK" in (final.content or ""), f"expected success token in: {final.content!r}"


@pytest.mark.usefixtures("require_postgres")
def test_navigator_answers_wiki_comparison_for_user(
    kma_knowledge_it,
    kma_learnings_it,
) -> None:
    """End-user flow: natural wiki Q&A — read index/articles, then answer in plain language."""
    agent = _build_it_navigator(kma_knowledge_it, kma_learnings_it)
    final = _run_navigator_agent(agent, _FLINK_KAFKA_QUESTION)

    tools = _tool_names(final)
    assert tools & {"read_wiki_index", "read_file"}, (
        f"expected wiki read tools, got: {sorted(tools)}"
    )

    answer = (final.content or "").lower()
    assert "flink" in answer
    assert "kafka" in answer

    matched = [signal for signal in _WIKI_COMPARISON_SIGNALS if signal in answer]
    assert len(matched) >= 2, (
        f"expected wiki-grounded comparison details, got: {final.content!r}"
    )


@pytest.mark.usefixtures("require_postgres")
def test_navigator_ontology_tool_find_wiki_concepts(
    kma_knowledge_it,
    kma_learnings_it,
    it_context_with_ontology: Path,
) -> None:
    """Navigator can route via find_wiki_concepts when prompted (ontology graph present)."""
    agent = _build_it_navigator(
        kma_knowledge_it,
        kma_learnings_it,
        context_dir=it_context_with_ontology,
    )
    prompt = (
        "Automated test: call find_wiki_concepts with query "
        "'Apache Flink vs Kafka Streams comparison'. "
        "If results include wiki paths for both Flink and Kafka Streams concepts, "
        "reply with final line exactly: ONTOLOGY_TOOL_OK. Otherwise ONTOLOGY_TOOL_FAIL."
    )
    final = _run_navigator_agent(agent, prompt)
    tools = _tool_names(final)
    assert "find_wiki_concepts" in tools, f"expected find_wiki_concepts, got: {sorted(tools)}"
    assert "ONTOLOGY_TOOL_OK" in (final.content or ""), final.content


@pytest.mark.usefixtures("require_postgres")
def test_navigator_baseline_vs_ontology_path_recall(
    kma_knowledge_it,
    kma_learnings_it,
    it_context_with_ontology: Path,
) -> None:
    """A/B: baseline wiki instructions vs ontology-augmented path recall on gold question."""
    baseline_instr = BASE_INSTRUCTIONS + EXA_INSTRUCTIONS + WIKI_INSTRUCTIONS_BASELINE
    ontology_instr = BASE_INSTRUCTIONS + EXA_INSTRUCTIONS + WIKI_INSTRUCTIONS

    baseline_agent = _build_it_navigator(
        kma_knowledge_it,
        kma_learnings_it,
        context_dir=it_context_with_ontology,
        instructions=baseline_instr,
    )
    ontology_agent = _build_it_navigator(
        kma_knowledge_it,
        kma_learnings_it,
        context_dir=it_context_with_ontology,
        instructions=ontology_instr,
    )

    baseline_final = _run_navigator_agent(baseline_agent, _FLINK_KAFKA_QUESTION)
    ontology_final = _run_navigator_agent(ontology_agent, _FLINK_KAFKA_QUESTION)

    baseline_paths = _wiki_paths_from_tool_results(baseline_final)
    ontology_paths = _wiki_paths_from_tool_results(ontology_final)
    baseline_recall = recall_at_k(baseline_paths, _FLINK_KAFKA_GOLD, k=max(len(baseline_paths), 1))
    ontology_recall = recall_at_k(ontology_paths, _FLINK_KAFKA_GOLD, k=max(len(ontology_paths), 1))

    ontology_tools = _tool_names(ontology_final)
    assert ontology_tools & {"find_wiki_concepts", "read_wiki_graph", "query_ontology"}, (
        f"expected an ontology tool in treatment run, got: {sorted(ontology_tools)}"
    )
    assert ontology_recall >= baseline_recall, (
        f"ontology path recall {ontology_recall} < baseline {baseline_recall}; "
        f"baseline_paths={baseline_paths}, ontology_paths={ontology_paths}"
    )


@pytest.mark.usefixtures("require_postgres")
def test_gold_questions_file_present() -> None:
    assert IT_QUESTIONS.is_file()
    rows = [json.loads(line) for line in IT_QUESTIONS.read_text().splitlines() if line.strip()]
    assert len(rows) >= 5
