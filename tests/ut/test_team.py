"""Unit tests for team leader wiring."""

from pathlib import Path

from kma.agents.team import TEAM_INSTRUCTIONS, build_team_instructions


def test_team_instructions_cover_enrichment() -> None:
    assert "Researcher" in TEAM_INSTRUCTIONS
    assert "trigger_wiki_refresh" in TEAM_INSTRUCTIONS
    assert "read_web_site_refs" in TEAM_INSTRUCTIONS
    assert "background" in TEAM_INSTRUCTIONS.lower()
    assert "If Researcher is unavailable" not in TEAM_INSTRUCTIONS
    assert "web_search_exa" not in TEAM_INSTRUCTIONS
    assert "Exa" not in TEAM_INSTRUCTIONS


def test_build_team_instructions_researcher_present() -> None:
    text = build_team_instructions(researcher_available=True)
    assert "Researcher is a team member" in text
    assert "Always delegate to Researcher" in text
    assert "Never** claim Researcher is unavailable" in text
    assert "If Researcher is unavailable" not in text
    assert "web_search_exa" not in text
    assert "Exa" not in text


def test_build_team_instructions_researcher_absent() -> None:
    text = build_team_instructions(researcher_available=False)
    assert "Researcher is not on this team" in text
    assert "wiki" in text.lower() and "raw" in text.lower()
    assert "Always delegate to Researcher" not in text
    assert "Do **not** invent web-search tools" in text
    assert "If Researcher is unavailable" not in text
    assert "KMA_PARALLEL_API_KEY" not in text


def test_build_kma_team_has_instructions_and_tools() -> None:
    from kma.tools.builder import build_team_tools

    tools = build_team_tools(Path("/tmp/kma-context"))
    assert len(tools) == 1
    assert tools[0].name == "trigger_wiki_refresh"


def test_navigator_instructions_omit_exa() -> None:
    from kma.agents.navigator import build_navigator_instructions

    text = build_navigator_instructions()
    assert "web_search_exa" not in text
    assert "Web Research (Exa)" not in text
