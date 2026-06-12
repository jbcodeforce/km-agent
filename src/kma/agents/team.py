from __future__ import annotations

from agno.agent import Agent
from agno.learn import LearnedKnowledgeConfig, LearningMachine, LearningMode
from agno.team import Team, TeamMode
from kma.agents.settings import get_agent_db, get_kma_knowledge, get_kma_learnings
from kma.agents.compiler import get_compiler
from kma.agents.navigator import get_navigator
from kma.agents.researcher import get_researcher
from kma.agents.linter import get_linter

from kma.config import (
    kma_show_team_member_responses_enabled,
    kma_stream_events_enabled,
)
from kma.llm_factory import build_default_llm_model


def _build_members() -> list[Agent | Team]:
    return [m for m in [get_navigator(), get_researcher(), get_compiler(), get_linter()] if m is not None]


def build_kma_team() -> Team:
    return Team(
        id="kma",
        name="KMA",
        mode=TeamMode.coordinate,
        model=build_default_llm_model(),
        members=_build_members(),
        db=get_agent_db(),
        instructions=[],
        tools=[],
        learning=LearningMachine(
            knowledge=get_kma_knowledge(),
            learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
        ),
        add_learnings_to_context=True,
        enable_agentic_memory=True,
        search_past_sessions=True,
        num_past_sessions_to_search=10,
        add_datetime_to_context=True,
        add_history_to_context=True,
        read_chat_history=True,
        num_history_runs=5,
        markdown=True,
        stream_events=True if kma_stream_events_enabled() else None,
        show_members_responses=kma_show_team_member_responses_enabled(),
    )


_kma_team: Team | None = None


def get_kma_team() -> Team:
    global _kma_team
    if _kma_team is None:
        _kma_team = build_kma_team()
    return _kma_team


def __getattr__(name: str):
    if name == "kma_team":
        return get_kma_team()
    if name == "members":
        return _build_members()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
