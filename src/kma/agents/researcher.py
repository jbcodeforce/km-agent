"""
Researcher Agent
================

Gathers source material from the web and local files, converts to
clean markdown, saves to raw/ with YAML frontmatter.

Conditional — only instantiated when ``KMA_PARALLEL_API_KEY`` or ``PARALLEL_API_KEY`` is set (see ``kma.config``).
Uses Parallel for web search (parallel_search) and content
extraction (parallel_extract).
"""

from __future__ import annotations

from agno.agent import Agent
from agno.learn import LearnedKnowledgeConfig, LearningMachine, LearningMode
from kma.config import PARALLEL_API_KEY, kma_agent_reasoning_enabled, kma_stream_events_enabled
from kma.llm_factory import build_default_llm_model
from kma.agents.settings import get_agent_db, get_kma_knowledge, get_kma_learnings
from kma.tools.builder import build_researcher_tools

RESEARCHER_INSTRUCTIONS = """\
You are the Researcher, a specialist in gathering and ingesting source material.

## Your Job
1. Search the web using `parallel_search` to find relevant sources
2. Extract full content from URLs using `parallel_extract`
3. Save to raw/ using `ingest_text` with proper YAML frontmatter
4. For quick URL ingestion, use `ingest_url` which auto-fetches content via Parallel
5. Update pal_knowledge with `Raw: {title}` metadata entries

## Ingest Rules
- Every raw file gets YAML frontmatter: title, source, ingested date, tags, type, compiled: false
- Filename is a slugified version of the title
- Tags should be specific topics (e.g. ["rag", "retrieval", "vector-search"]), not generic
- doc_type is one of: paper, article, repo, notes, transcript, image
- For multi-page sources, summarize and save key sections
- You can batch-ingest: research a topic and save multiple sources

## Search Strategy
- Use `parallel_search` with clear objectives to find relevant pages
- Use `parallel_extract` to get full content from the best results
- Prefer official documentation over blog posts or forums
- For error messages, include the fix or workaround
- Cite sources — always include the URL

## What You Do NOT Do
- Do not compile wiki articles — that's the Compiler's job
- Do not modify anything in wiki/
- Do not interact with email, calendar, or Slack
- Do not answer user questions directly — you gather material, the Navigator answers questions\
"""


def build_researcher_agent() -> Agent | None:
    """Construct the Researcher agent when ``PARALLEL_API_KEY`` is set."""
    if not PARALLEL_API_KEY:
        return None
    km = get_kma_knowledge()
    lr = get_kma_learnings()
    md = build_default_llm_model()
    return Agent(
        id="researcher",
        name="Researcher",
        role="Gathers source material from the web, converts to markdown, saves to raw/",
        model=md,
        db=get_agent_db(),
        instructions=RESEARCHER_INSTRUCTIONS,
        knowledge=km,
        search_knowledge=True,
        learning=LearningMachine(
            knowledge=lr,
            learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
        ),
        add_learnings_to_context=True,
        tools=build_researcher_tools(km),
        add_datetime_to_context=True,
        markdown=True,
        reasoning=kma_agent_reasoning_enabled(),
        stream_events=True if kma_stream_events_enabled() else None,
    )


_researcher: Agent | None = None
_initialized = False


def get_researcher() -> Agent | None:
    global _researcher, _initialized
    if not _initialized:
        _researcher = build_researcher_agent()
        _initialized = True
    return _researcher


def __getattr__(name: str):
    if name == "researcher":
        return get_researcher()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
