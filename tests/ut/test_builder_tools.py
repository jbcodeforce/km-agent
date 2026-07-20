"""Researcher tool assembly — DuckDuckGo wiring."""

from kma.config import Env
from kma.tools.builder import build_researcher_tools


def test_build_researcher_tools_includes_duckduckgo(monkeypatch, mock_knowledge) -> None:
    monkeypatch.setenv(Env.KMA_WEB_SEARCH_MAX_RESULTS, "3")
    monkeypatch.delenv(Env.KMA_PARALLEL_MAX_RESULTS, raising=False)

    tools = build_researcher_tools(mock_knowledge)
    web = next(t for t in tools if getattr(t, "name", None) == "websearch")
    assert web.fixed_max_results == 3
    assert "web_search" in web.functions


def test_build_researcher_tools_max_results_legacy_env(monkeypatch, mock_knowledge) -> None:
    monkeypatch.delenv(Env.KMA_WEB_SEARCH_MAX_RESULTS, raising=False)
    monkeypatch.setenv(Env.KMA_PARALLEL_MAX_RESULTS, "2")

    tools = build_researcher_tools(mock_knowledge)
    web = next(t for t in tools if getattr(t, "name", None) == "websearch")
    assert web.fixed_max_results == 2
