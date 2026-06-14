"""Researcher tool assembly — Parallel limits and wiring."""

from unittest.mock import MagicMock

from kma.config import Env
from kma.tools.builder import build_researcher_tools


def test_build_researcher_tools_parallel_limits(monkeypatch, mock_knowledge) -> None:
    monkeypatch.setenv(Env.KMA_PARALLEL_API_KEY, "test-key")
    monkeypatch.setenv(Env.KMA_PARALLEL_MAX_RESULTS, "2")
    monkeypatch.setenv(Env.KMA_PARALLEL_MAX_CHARS_PER_RESULT, "3000")

    tools = build_researcher_tools(mock_knowledge)
    parallel = next(t for t in tools if getattr(t, "name", None) == "parallel_tools")
    assert parallel.max_results == 2
    assert parallel.max_chars_per_result == 3000


def test_build_researcher_tools_parallel_defaults(monkeypatch, mock_knowledge) -> None:
    monkeypatch.setenv(Env.KMA_PARALLEL_API_KEY, "test-key")
    monkeypatch.delenv(Env.KMA_PARALLEL_MAX_RESULTS, raising=False)
    monkeypatch.delenv(Env.KMA_PARALLEL_MAX_CHARS_PER_RESULT, raising=False)

    tools = build_researcher_tools(mock_knowledge)
    parallel = next(t for t in tools if getattr(t, "name", None) == "parallel_tools")
    assert parallel.max_results == 2
    assert parallel.max_chars_per_result == 3000
