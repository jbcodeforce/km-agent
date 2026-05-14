"""Compiler agent wiring: model id from env via config; no LLM runs."""

from pathlib import Path

import pytest

from kma.agents.compiler import build_compiler_agent


def test_build_compiler_agent_model_id_from_env(monkeypatch) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("KMA_MODEL_ID", "kma-test-model:tag")
    agent = build_compiler_agent()
    assert agent.id == "compiler"
    assert agent.model.id == "kma-test-model:tag"
    assert type(agent.model).__name__ == "OllamaResponses"


def test_build_compiler_agent_openai_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "openai")
    monkeypatch.delenv("KMA_MODEL_ID", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    agent = build_compiler_agent()
    assert type(agent.model).__name__ == "OpenAIResponses"
    assert agent.model.id == "gpt-4o-mini"


def test_build_compiler_agent_anthropic_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("KMA_MODEL_ID", "claude-3-5-haiku-20241022")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    agent = build_compiler_agent()
    assert type(agent.model).__name__ == "Claude"
    assert agent.model.id == "claude-3-5-haiku-20241022"


def test_build_compiler_agent_openai_requires_api_key(monkeypatch) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("KMA_MODEL_ID", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        build_compiler_agent()


def test_build_compiler_agent_accepts_raw_roots(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "ollama")
    docs = tmp_path / "docs"
    docs.mkdir()
    ctx = tmp_path / "ctx"
    ctx.mkdir()
    (ctx / "raw").mkdir()
    (ctx / "wiki").mkdir()
    agent = build_compiler_agent(context_dir=ctx, raw_roots=[("studies", docs), ("ingested", ctx / "raw")])
    assert agent.id == "compiler"
    names = [getattr(t, "name", None) for t in agent.tools]
    assert "read_manifest" in names
