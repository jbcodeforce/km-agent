"""Linter agent and tool wiring; no LLM runs or external services."""

from unittest.mock import MagicMock

from kma.agents.linter import build_lint_prompt, build_linter_agent
from kma.config import Env
from kma.llm_factory import build_default_llm_model
from kma.tools.builder import build_linter_tools


def test_build_linter_tools() -> None:
    km = MagicMock()
    tools = build_linter_tools(knowledge=km)
    assert len(tools) > 0


def test_build_lint_prompt_automated() -> None:
    prompt = build_lint_prompt(automated=True)
    assert "automated lint" in prompt
    assert "read_wiki_index" in prompt
    assert "wiki/lint-report.md" in prompt
    assert "mark_linted" in prompt


def test_build_linter_agent_wiring(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_LLM_PROVIDER, "mlx")
    monkeypatch.setenv(Env.KMA_LLM_MODEL_ID, "test-model")
    monkeypatch.setenv(Env.KMA_LLM_BASE_URL, "http://localhost:7999/v1")
    monkeypatch.setenv(Env.KMA_LLM_API_KEY, "not-needed")
    km = MagicMock()
    model = build_default_llm_model()
    agent = build_linter_agent(model=model, knowledge=km)
    assert agent.id == "linter"
    assert agent.name == "Linter"
    assert agent.instructions
    assert len(agent.tools) > 0
    assert agent.model.id == "test-model"
    assert agent.knowledge is km
