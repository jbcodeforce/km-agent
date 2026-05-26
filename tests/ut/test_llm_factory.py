"""Unit tests for Cursor SDK wiring in llm_factory."""

from unittest.mock import patch

import pytest

from agno.models.message import Message
from kma.llm_factory import build_cursor_agent, build_default_llm_model, cursor_agent_options
from kma.models.cursor_agent import CursorAgentModel, format_messages_for_cursor


def test_format_messages_for_cursor_includes_roles() -> None:
    prompt = format_messages_for_cursor(
        [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="Summarize the wiki index."),
        ]
    )
    assert "[system]" in prompt
    assert "[user]" in prompt
    assert "Summarize the wiki index." in prompt


def test_build_default_llm_model_cursor_local(monkeypatch) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "cursor")
    monkeypatch.setenv("KMA_MODEL_ID", "composer-2.5")
    monkeypatch.setenv("CURSOR_API_KEY", "cursor_test_key")
    monkeypatch.setenv("KMA_CURSOR_RUNTIME", "local")
    monkeypatch.setenv("KMA_CURSOR_CWD", "/tmp/kma-workspace")

    model = build_default_llm_model()
    assert isinstance(model, CursorAgentModel)
    assert model.id == "composer-2.5"
    assert model.runtime == "local"
    assert model.cwd == "/tmp/kma-workspace"


def test_build_default_llm_model_cursor_requires_api_key(monkeypatch) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "cursor")
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    monkeypatch.delenv("KMA_LLM_API_KEY", raising=False)
    with pytest.raises(ValueError, match="CURSOR_API_KEY"):
        build_default_llm_model()


def test_cursor_agent_options_cloud_repo(monkeypatch) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "cursor")
    monkeypatch.setenv("KMA_MODEL_ID", "composer-2.5")
    monkeypatch.setenv("CURSOR_API_KEY", "cursor_test_key")
    monkeypatch.setenv("KMA_CURSOR_RUNTIME", "cloud")
    monkeypatch.setenv("KMA_CURSOR_REPO", "https://github.com/org/repo")

    options = cursor_agent_options()
    assert options.model == "composer-2.5"
    assert options.cloud is not None
    assert options.cloud.repos[0].url == "https://github.com/org/repo"


def test_build_cursor_agent_returns_sdk_handle(monkeypatch) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "cursor")
    monkeypatch.setenv("CURSOR_API_KEY", "cursor_test_key")
    monkeypatch.setenv("KMA_CURSOR_RUNTIME", "local")

    fake_agent = object()
    with patch("cursor_sdk.Agent.create", return_value=fake_agent) as create:
        agent = build_cursor_agent(model_id="composer-2.5")
    assert agent is fake_agent
    create.assert_called_once()
