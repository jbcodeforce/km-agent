"""Integration test: Navigator agent with sandbox context (OMLX chat by default; embeddings from ``KMA_EMBED_PROVIDER``)."""

from __future__ import annotations

from pathlib import Path

import pytest
from agno.agent import Agent
from agno.run.base import RunStatus
from agno.run.agent import RunOutput

from kma.agents.navigator import build_navigator_agent

IT_CONTEXT = Path(__file__).resolve().parent.parent / "data"

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


def _build_it_navigator(
    kma_knowledge_it,
    kma_learnings_it,
) -> Agent:
    agent = build_navigator_agent(
        knowledge=kma_knowledge_it,
        learnings=kma_learnings_it,
        context_dir=IT_CONTEXT,
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
    user_question = (
        "According to our wiki, how does Apache Flink compare to Kafka Streams? "
        "Briefly explain when you'd pick each."
    )
    final = _run_navigator_agent(agent, user_question)

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
