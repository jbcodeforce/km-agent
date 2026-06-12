"""
Linter Agent
============

Periodic health checks on the wiki. Finds contradictions, stale articles,
missing concepts, and suggests research directions.
"""
from collections.abc import Sequence
from pathlib import Path
from agno.agent import Agent
from agno.knowledge import Knowledge
from agno.models.base import Model

from kma.llm_factory import build_default_llm_model
from kma.agents.settings import get_agent_db, get_kma_knowledge
from kma.tools.builder import build_linter_tools

LINTER_INSTRUCTIONS = """\
You are the Linter, responsible for wiki quality and integrity.

## Your Job
Run health checks on the wiki and produce a lint report.

### Checks to Run
0. All text files should be markdown files with '.md' extension
1. **Contradictions**: Compare claims across concept articles. Flag conflicts with source citations.
2. **Stale articles**: Flag concepts not updated in 30+ days.
3. **Missing concepts**: Find references to concepts that don't have articles yet (e.g. related links pointing to non-existent files).
4. **Orphaned articles**: Find articles not referenced by any other article or the index.
5. **Thin articles**: Flag articles under 200 words that could use enrichment.
6. **Duplicate detection**: Find articles covering overlapping ground that should be merged.
7. **Gap analysis**: Based on the concept graph, suggest topics that would strengthen connections.

### Process
1. Read the wiki index (`read_wiki_index`) for the full inventory
2. Read each concept article via `read_file`
3. Run each check, collecting findings
4. Write a lint report to wiki/lint-report.md via `save_file`
5. Update wiki state (`update_wiki_state` with mark_linted=True)
6. Save any new `Discovery:` entries to knowledge for connections found

### Lint Report Format
```markdown
# Wiki Lint Report

Run: YYYY-MM-DDTHH:MM:SSZ
Articles checked: N

## Findings

### Critical
- [finding with severity and suggested action]

### Warnings
- [finding with severity and suggested action]

### Suggestions
- [research topics, merge candidates, enrichment opportunities]

## Summary
N critical | N warnings | N suggestions
```

### Optional: Fill Gaps
If you have web search available (web_search_exa), you can research missing
data to suggest concrete content for thin articles or missing concepts.
Include these as suggestions in the report, not direct edits.

## What You Do NOT Do
- Do not modify concept articles directly — report findings, let the Compiler fix them
- Do not interact with users directly
- Do not access email, calendar, or Slack\
"""

def build_linter_agent(
     *,
    context_dir: Path | str | None = None,
    knowledge: Knowledge | None = None,
    model: Model | None = None,
) -> Agent:
    md = model or build_default_llm_model()
    km: Knowledge = knowledge or get_kma_knowledge()
    return Agent(
        id="linter",
        name="Linter",
        role="Runs health checks on the wiki, finds issues, suggests improvements",
        model=md,
        db=get_agent_db(),
        instructions=LINTER_INSTRUCTIONS,
        knowledge=km,
        search_knowledge=True,
        tools=build_linter_tools(km, context_dir=context_dir),
        add_datetime_to_context=True,
        markdown=True,
    )


_linter: Agent | None = None


def get_linter() -> Agent:
    global _linter
    if _linter is None:
        _linter = build_linter_agent()
    return _linter


def __getattr__(name: str):
    if name == "linter":
        return get_linter()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")