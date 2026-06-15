"""Unit tests for team leader wiring."""

from pathlib import Path

from kma.agents.team_instructions import TEAM_INSTRUCTIONS


def test_team_instructions_cover_enrichment() -> None:
    assert "Researcher" in TEAM_INSTRUCTIONS
    assert "trigger_wiki_refresh" in TEAM_INSTRUCTIONS
    assert "background" in TEAM_INSTRUCTIONS.lower()


def test_build_kma_team_has_instructions_and_tools() -> None:
    from kma.tools.builder import build_team_tools

    tools = build_team_tools(Path("/tmp/kma-context"))
    assert len(tools) == 1
    assert tools[0].name == "trigger_wiki_refresh"
