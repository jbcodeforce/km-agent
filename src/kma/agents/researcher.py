"""
Researcher Agent
================

Gathers source material from the web and local files, converts to
clean markdown, saves to raw/ with YAML frontmatter.

Uses DuckDuckGo (``web_search``) for free web search and ``ingest_url`` /
``ingest_text`` to save sources under ``raw/``.
"""

from __future__ import annotations
from pathlib import Path
from agno.agent import Agent
from agno.knowledge import Knowledge
from agno.models.base import Model
from kma.config import kma_stream_events_enabled
from kma.llm_factory import build_default_llm_model
from kma.agents.settings import get_agent_db, get_kma_knowledge
from kma.tools.builder import build_researcher_tools

RESEARCHER_INSTRUCTIONS = """\
You are the Researcher, a specialist in gathering and ingesting source material.

## Your Job
1. When ``web_site_ref.json`` exists under context (or the user names a sources file), call ``read_web_site_refs`` first
2. Search the web using `web_search` (DuckDuckGo) to find relevant sources — bias toward trusted sites from step 1
3. For promising URLs, save content with `ingest_url` (fetches a bounded text excerpt) or summarize into `ingest_text`
4. Update knowledge with `Raw: {title}` metadata entries
5. List every new manifest ``file`` name you ingested

## Ingest Rules
- Every raw file gets YAML frontmatter: title, source, ingested date, tags, type, compiled: false
- Filename is a slugified version of the title
- Tags should be specific topics (e.g. ["rag", "retrieval", "vector-search"]), not generic
- doc_type is one of: paper, article, repo, notes, transcript, image
- For multi-page sources, summarize and save key sections
- Prefer one source per run when running on local MLX — avoid batch-ingest in a single invocation

## Search Strategy (keep context small)
- Use **one** `web_search` per topic (tool returns a small fixed result count)
- Prefer `ingest_url` on **one URL at a time**, or `ingest_text` with a concise summary
- Prefer official documentation over blog posts or forums
- When trusted sites are listed, search and ingest from those domains first
- For error messages, include the fix or workaround
- Cite sources — always include the URL

## What You Do NOT Do
- Do not compile wiki articles — that's the Compiler's job
- Do not modify anything in wiki/
- Do not interact with email, calendar, or Slack
- Do not answer user questions directly — you gather material, the Navigator answers questions\
"""


def build_researcher_agent(
    context_dir: Path | None = None,
    knowledge: Knowledge | None = None,
    model: Model | None = None,
) -> Agent:
    """Construct the Researcher agent (DuckDuckGo web search + ingest)."""
    km = knowledge or get_kma_knowledge()
    md = model or build_default_llm_model()
    return Agent(
        id="researcher",
        name="Researcher",
        role="Gathers source material from the web, converts to markdown, saves to raw/",
        model=md,
        db=get_agent_db(),
        instructions=RESEARCHER_INSTRUCTIONS,
        knowledge=km,
        search_knowledge=False,
        tools=build_researcher_tools(km, context_dir=context_dir),
        add_datetime_to_context=True,
        markdown=True,
        reasoning=False,
        stream_events=True if kma_stream_events_enabled() else None,
    )


_researcher: Agent | None = None
_initialized = False


def get_researcher() -> Agent:
    global _researcher, _initialized
    if not _initialized:
        _researcher = build_researcher_agent()
        _initialized = True
    return _researcher


def __getattr__(name: str):
    if name == "researcher":
        return get_researcher()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
