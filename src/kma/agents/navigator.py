"""
Navigator Agent
===============

The primary agent users interact with. Handles files, web research, and wiki-aware Q&A.

Reads the wiki index first for knowledge questions, then pulls
specific articles. Falls back to raw/ and live sources.
"""

from __future__ import annotations

from pathlib import Path

from agno.agent import Agent
from agno.knowledge import Knowledge
from agno.db.postgres import PostgresDb
from agno.learn import LearnedKnowledgeConfig, LearningMachine, LearningMode
from agno.models.base import Model

from kma.agents.instructions import BASE_INSTRUCTIONS, EXA_INSTRUCTIONS, WIKI_INSTRUCTIONS
from kma.agents.settings import get_agent_db, get_kma_knowledge, get_kma_learnings
from kma.config import kma_agent_reasoning_enabled, kma_stream_events_enabled
from kma.llm_factory import build_default_llm_model
from kma.tools.builder import build_navigator_tools


def build_navigator_instructions() -> str:
    """Build instructions for the Navigator agent (core ops + wiki-aware retrieval).
    """
    parts = [BASE_INSTRUCTIONS, EXA_INSTRUCTIONS, WIKI_INSTRUCTIONS]
    return "".join(parts)


def build_navigator_agent(
    *,
    model: Model | None = None,
    knowledge: Knowledge | None = None,
    learnings: Knowledge | None = None,
    db: PostgresDb | None = None,
    context_dir: Path | str | None = None,
    instructions: str | None = None,
) -> Agent:
    """Construct the Navigator agent.

    Args:
        model: LLM (default from ``KMA_LLM_PROVIDER``, ``KMA_MODEL_ID``, and provider env).
        knowledge: Primary knowledge base (default ``kma_knowledge``).
        learnings: Knowledge base for agentic learning (default ``kma_learnings``).
        db: Session / memory DB (default ``agent_db``).
        context_dir: Root containing ``wiki/`` and ``raw/`` for file and wiki tools.
        instructions: System instructions (default from ``build_navigator_instructions()``).
    """
    kn: Knowledge = knowledge or get_kma_knowledge()
    lr: Knowledge = learnings or get_kma_learnings()
    md = model or build_default_llm_model()
    pg: PostgresDb = db or get_agent_db()
    instr = instructions if instructions is not None else build_navigator_instructions()
    ctx = Path(context_dir).resolve() if context_dir is not None else None
    return Agent(
        id="navigator",
        name="Navigator",
        role="Primary agent for user interaction, knowledge queries, email, calendar, SQL, files, and wiki Q&A",
        model=md,
        db=pg,
        instructions=instr,
        knowledge=kn,
        search_knowledge=True,
        learning=LearningMachine(
            knowledge=lr,
            learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
        ),
        tools=build_navigator_tools(kn, context_dir=ctx),
        enable_agentic_memory=True,
        search_past_sessions=True,
        num_past_sessions_to_search=5,
        add_datetime_to_context=True,
        add_history_to_context=True,
        read_chat_history=True,
        num_history_runs=10,
        markdown=True,
        #reasoning=kma_agent_reasoning_enabled(),
        stream_events=True if kma_stream_events_enabled() else None,
    )


_navigator: Agent | None = None


def get_navigator() -> Agent:
    global _navigator
    if _navigator is None:
        _navigator = build_navigator_agent()
    return _navigator


def __getattr__(name: str):
    if name == "navigator":
        return get_navigator()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
