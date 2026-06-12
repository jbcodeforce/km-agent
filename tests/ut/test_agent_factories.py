"""Compiler agent wiring: model id from env via config; no LLM runs."""

from unittest.mock import MagicMock

from kma.agents.compiler import build_compiler_agent
from kma.agents.linter import build_linter_agent
from kma.config import Env
from kma.llm_factory import build_default_llm_model


def test_build_compiler_agent_model_id_from_env(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_LLM_PROVIDER, "mlx")
    monkeypatch.setenv(Env.KMA_LLM_MODEL_ID, "Qwen3.6:27b-4bit")
    monkeypatch.setenv(Env.KMA_LLM_BASE_URL, "http://localhost:7999/v1")
    monkeypatch.setenv(Env.KMA_LLM_API_KEY, "not-needed")
    agent = build_compiler_agent(knowledge=MagicMock())
    assert agent.id == "compiler"
    assert agent.model.id == "Qwen3.6:27b-4bit"
    assert type(agent.model).__name__ == "OpenAILike"


def test_build_compiler_agent_openai_when_configured(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_LLM_PROVIDER, "openai")
    monkeypatch.setenv(Env.KMA_LLM_MODEL_ID, "gpt-4o-mini")
    monkeypatch.setenv(Env.KMA_LLM_API_KEY, "sk-test-key")
    monkeypatch.setenv(Env.KMA_LLM_BASE_URL, "http://localhost:7999/v1")
    agent = build_compiler_agent(knowledge=MagicMock())
    assert type(agent.model).__name__ == "OpenAIResponses"
    assert agent.model.id == "gpt-4o-mini"


def test_build_compiler_agent_anthropic_when_configured(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_LLM_PROVIDER, "anthropic")
    monkeypatch.setenv(Env.KMA_LLM_MODEL_ID, "claude-3-5-haiku-20241022")
    monkeypatch.setenv(Env.KMA_LLM_API_KEY, "sk-ant-test")
    agent = build_compiler_agent(knowledge=MagicMock())
    assert type(agent.model).__name__ == "Claude"
    assert agent.model.id == "claude-3-5-haiku-20241022"


def test_build_compiler_agent_uses_mock_db_by_default(mock_postgres_db, mock_knowledge) -> None:
    agent = build_compiler_agent(model=build_default_llm_model(), knowledge=mock_knowledge)
    assert agent.db is mock_postgres_db
    assert agent.knowledge is mock_knowledge
    assert agent.model is not None
    assert type(agent.model).__name__ == "OpenAILike"
    assert agent.instructions

def test_build_linter_agent_uses_mock_db_by_default(mock_postgres_db, mock_knowledge) -> None:
    agent = build_linter_agent(model=build_default_llm_model(), knowledge=mock_knowledge)
    assert agent.db is mock_postgres_db
    assert agent.knowledge is mock_knowledge
    assert agent.model is not None
    assert type(agent.model).__name__ == "OpenAILike"
    assert agent.instructions