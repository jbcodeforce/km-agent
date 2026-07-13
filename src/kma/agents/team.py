from __future__ import annotations
import os
from agno.agent import Agent
from agno.learn import LearnedKnowledgeConfig, LearningMachine, LearningMode
from agno.team import Team, TeamMode
from kma.agents.settings import get_agent_db, get_kma_knowledge, get_kma_learnings
from kma.agents.compiler import get_compiler
from kma.agents.navigator import get_navigator
from kma.agents.researcher import get_researcher
from kma.agents.linter import get_linter
from kma.tools.builder import build_team_tools

from kma.config import (
    get_kma_context_dir,
    kma_show_team_member_responses_enabled,
    kma_stream_events_enabled,
)
from kma.llm_factory import build_default_llm_model



TEAM_INSTRUCTIONS = """\
You are KMA, the team leader coordinating specialist agents for personal knowledge management.

## Members

- **Navigator** — Primary user-facing agent: wiki Q&A, SQL, files, synthesis from existing materials.
- **Researcher** — Web search and ingest to ``raw/`` (when available). Does not answer users directly.
- **Compiler** — Turns one raw file into wiki articles (explicit ``file_id`` per run).
- **Linter** — Wiki health checks; writes ``wiki/lint-report.md``.

## Routing

| User intent | Delegate to | Your role after member returns |
|-------------|-------------|--------------------------------|
| Research, enrich knowledge, search news, ingest URL/topic | **Researcher** | Ask **Navigator** to synthesize an answer from ingested raw + wiki; call ``trigger_wiki_refresh`` |
| Knowledge Q&A, SQL, files, drafts | **Navigator** | Synthesize and return |
| "Compile wiki" / process raw file | **Compiler** | Pass explicit ``file_id`` from manifest |
| "Lint wiki" / find gaps | **Linter** | Return lint summary |

## Enrichment workflow (research / news / enrich)

When the user wants new external material (research a topic, search news, enrich the knowledge base):

1. **Delegate to Researcher** with a clear task: search, extract, ingest to ``raw/`` with tags. Ask Researcher to call ``read_web_site_refs`` when ``web_site_ref.json`` exists under context (or when the user names a sources file). Ask Researcher to list every new manifest ``file`` name ingested (e.g. ``my-topic.md``).
2. **Delegate to Navigator** to answer the user's question using the newly ingested raw files (``read_file`` on ``raw/...``) plus existing wiki index. Do not repeat live web search.
3. **Tell the user** in one line that the wiki is updating in the background (non-blocking).
4. **Call ``trigger_wiki_refresh``** with the new file ids from step 1 (comma-separated or JSON array). If Researcher ingested nothing, skip this step.

If Researcher is unavailable (no Parallel API key), delegate research-style requests to **Navigator** (Exa web search) and do not call ``trigger_wiki_refresh``.

## General rules

- You are the voice the user hears — synthesize member outputs into one cohesive response.
- For simple greetings or meta questions ("what can you do?"), respond directly without delegating.
- Never block the user waiting for compile or lint; those run in the background via ``trigger_wiki_refresh``.
"""


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
        instructions=TEAM_INSTRUCTIONS,
        tools=build_team_tools(get_kma_context_dir()),
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
        num_history_runs=int(os.getenv("KMA_NUM_HISTORY_RUNS", "3")),
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
