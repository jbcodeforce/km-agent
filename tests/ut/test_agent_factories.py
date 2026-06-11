"""Compiler agent wiring: model id from env via config; no LLM runs."""

from pathlib import Path

import pytest
from dotenv import load_dotenv
from kma.agents.compiler import build_compiler_agent
from src.kma.config import Env

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_build_compiler_agent_model_id_from_env() -> None:
    load_dotenv(REPO_ROOT / "example.env", override=True)
    agent = build_compiler_agent()
    assert agent.id == "compiler"
    assert agent.model.id == "Qwen3.6:27b-4bit"
    assert type(agent.model).__name__ == "OpenAILike"


def test_build_compiler_agent_openai_when_configured(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_LLM_PROVIDER, "openai")
    monkeypatch.setenv(Env.KMA_LLM_MODEL_ID, "gpt-4o-mini")
    monkeypatch.setenv(Env.KMA_LLM_API_KEY, "sk-test-key")
    monkeypatch.setenv(Env.KMA_LLM_BASE_URL, "http://localhost:7999/v1")
    agent = build_compiler_agent()
    assert type(agent.model).__name__ == "OpenAIResponses"
    assert agent.model.id == "gpt-4o-mini"


def test_build_compiler_agent_anthropic_when_configured(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_LLM_PROVIDER, "anthropic")
    monkeypatch.setenv(Env.KMA_LLM_MODEL_ID, "claude-3-5-haiku-20241022")
    monkeypatch.setenv(Env.KMA_LLM_API_KEY, "sk-ant-test")
    agent = build_compiler_agent()
    assert type(agent.model).__name__ == "Claude"
    assert agent.model.id == "claude-3-5-haiku-20241022"
