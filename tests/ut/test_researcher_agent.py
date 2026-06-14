"""Researcher agent wiring — stateless worker per SPEC."""

from kma.agents.researcher import build_researcher_agent
from kma.config import Env
from kma.llm_factory import build_default_llm_model


def test_build_researcher_agent_stateless(monkeypatch, mock_knowledge) -> None:
    monkeypatch.setenv(Env.KMA_PARALLEL_API_KEY, "test-key")
    monkeypatch.setenv(Env.KMA_LLM_PROVIDER, "mlx")
    monkeypatch.setenv(Env.KMA_LLM_MODEL_ID, "test-model")
    monkeypatch.setenv(Env.KMA_LLM_BASE_URL, "http://localhost:7999/v1")
    monkeypatch.setenv(Env.KMA_LLM_API_KEY, "not-needed")
    agent = build_researcher_agent(
        knowledge=mock_knowledge,
        model=build_default_llm_model(),
    )
    assert agent is not None
    assert agent.search_knowledge is not True
    assert agent.learning is None
    assert agent.reasoning is False
    assert "one URL at a time" in agent.instructions
    assert agent is not None
    assert agent.search_knowledge is not True
    assert agent.learning is None
    assert agent.reasoning is False
    assert "one URL at a time" in agent.instructions


def test_build_researcher_agent_none_without_parallel_key(monkeypatch, mock_knowledge) -> None:
    monkeypatch.delenv(Env.KMA_PARALLEL_API_KEY, raising=False)
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    assert build_researcher_agent(knowledge=mock_knowledge) is None
