"""
Compiler Agent
==============

Reads uncompiled raw documents and produces/updates wiki articles.
The core of the knowledge base compilation pipeline.

Only reads raw/ and writes wiki/. Does not interact with users,
query live sources, or run web searches.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from agno.agent import Agent
from agno.knowledge import Knowledge
from agno.models.base import Model

from kma.agents.settings import get_agent_db, get_kma_knowledge
from kma.config import kma_stream_events_enabled
from kma.llm_factory import build_default_llm_model
from kma.tools.builder import build_compiler_tools

COMPILER_INSTRUCTIONS = """\
You are the Compiler, responsible for turning raw source material into a structured wiki.

## Single-file contract
Each invocation compiles **at most one** raw file. Never process multiple uncompiled entries in one run.

### When the prompt names a file
If the prompt specifies a file (basename like ``fitforpurpose.md``, or labelled ``file_id`` like ``studies:sql/joins.md``):
1. Call ``read_manifest`` and confirm that entry exists and ``compiled`` is false.
2. Read **only** that document from raw/ (use ``raw/<label>/...`` when ``file_id`` has a label prefix).
3. Write a summary to ``wiki/summaries/{doc-name}.md``.
4. Extract key concepts and create or update articles under ``wiki/concepts/``.
5. Mark **only** that file compiled via ``update_manifest_compiled`` with the same ``file_id`` string.
6. Update ``wiki/index.md`` (``update_wiki_index``) and wiki state (``update_wiki_state``).

Do not read, summarize, or mark any other uncompiled file in this run.

### When the prompt does not name a file
1. Call ``read_manifest``.
2. List uncompiled entries with their ``file_id`` values and how many remain.
3. State that compilation requires an explicit file name or ``file_id``.
4. Stop. Do **not** read raw content or call ``update_manifest_compiled``.

## Wiki Article Format
Concept articles in wiki/concepts/ should follow this structure:

```markdown
---
title: "Concept Name"
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [raw/source-file.md, raw/another-source.md]
related: [related-concept, another-concept]
tags: [tag1, tag2]
---

# Concept Name

Clear explanation of the concept...

## Sources
- [Source Title](../summaries/source-file.md)

## Related
- [Related Concept](related-concept.md)
```

## Summary Format
Summaries in wiki/summaries/ should be concise (200-500 words) and capture:
- Main thesis/findings
- Key data points or claims
- How it connects to other concepts in the wiki

## Index Format
The wiki/index.md should list every concept article with a 1-line summary.
**IMPORTANT:** All paths in the index MUST start with `wiki/` so that any agent
can pass them directly to `read_file`. Do NOT use paths relative to wiki/.

```markdown
# Wiki Index

Last compiled: YYYY-MM-DDTHH:MM:SSZ
Articles: N | Sources: N | Outputs: N

## Concepts
- [Concept Name](wiki/concepts/concept-name.md) — One-line summary. Tags: tag1, tag2.
...

## Recent Outputs
- [Output Title](wiki/outputs/date-title.md) — One-line description.
...
```

## Multi-root raw (when your tools use ``raw/<label>/...``)
- If ``read_manifest`` entries include ``file_id`` like ``studies:sql/joins.md``, read that source at ``raw/studies/sql/joins.md`` and call ``update_manifest_compiled`` with the **same** ``file_id`` string when done.
- If there is only the default ``context/raw`` tree, paths stay ``raw/your-file.md`` and ``file_id`` equals ``file`` (no label prefix).

## Design Principles
- **Incremental**: Only process files where compiled is false. Never rewrite the entire wiki.
- **Additive**: New information enriches existing articles. Note contradictions, don't silently overwrite.
- **Source-tracked**: Every claim links back to the raw source that supports it.
- **Index-first**: The index is the most important file. Keep it accurate, concise, complete.

## What You Do NOT Do
- Do not interact with users directly
- Do not query live sources (email, calendar, web)
- Do not run web searches — you only work with what's already in raw/
- Do not delete files
- Do not compile more than one file per run\
"""


def compile_file_read_path(file_id: str) -> str:
    """Map manifest ``file_id`` to the virtual path passed to ``read_file``."""
    if ":" in file_id:
        label, rel = file_id.split(":", 1)
        return f"raw/{label}/{rel}"
    return f"raw/{file_id}"


def compile_summary_basename(file_id: str) -> str:
    """Basename for ``wiki/summaries/{name}.md`` from a ``file_id``."""
    rel = file_id.split(":", 1)[-1]
    return Path(rel).name


def build_compile_file_prompt(file_id: str, *, automated: bool = False) -> str:
    """Build a single-file compile prompt for scripts, tests, or direct agent runs."""
    read_path = compile_file_read_path(file_id)
    summary_name = compile_summary_basename(file_id)
    prefix = (
        "You are running an automated compile. Use tools only; do not ask the user questions.\n"
        if automated
        else ""
    )
    return (
        f"{prefix}"
        f"Process the file {file_id} only. Do not compile any other uncompiled manifest entries.\n"
        f"1) Call read_manifest and confirm {file_id} has compiled false.\n"
        f"2) Read {read_path} via read_file.\n"
        f"3) Write wiki/summaries/{summary_name} with a concise markdown summary.\n"
        "4) Create or update concept articles under wiki/concepts/ for key topics from this file.\n"
        f"5) Call update_manifest_compiled with filename {file_id}.\n"
        "6) Call update_wiki_index with paths starting with wiki/.\n"
        "7) Call update_wiki_state with mark_compiled true.\n"
        + ("Keep responses short; complete the workflow." if automated else "")
    )


def build_compiler_agent(
    *,
    context_dir: Path | str | None = None,
    raw_roots: Sequence[tuple[str, Path]] | None = None,
    knowledge: Knowledge | None = None,
    model: Model | None = None,
) -> Agent:
    """Construct the Compiler agent.

    Args:
        context_dir: Root containing ``wiki/`` and default ``raw/`` (default: config).
        raw_roots: Optional ``(label, path)`` list for one or more raw directories; see
            ``build_compiler_tools``. When omitted, raw is ``context_dir/raw``.
        knowledge: Knowledge base (default: ``kma_knowledge`` from settings).
        model: LLM (default from ``KMA_LLM_PROVIDER``, ``KMA_MODEL_ID``, and provider env).
    """
    km: Knowledge = knowledge or get_kma_knowledge()
    ctx = Path(context_dir) if context_dir is not None else None
    md = model or build_default_llm_model()
    return Agent(
        id="compiler",
        name="Compiler",
        role="Reads raw documents and compiles them into structured wiki articles",
        model=md,
        db=get_agent_db(),
        instructions=COMPILER_INSTRUCTIONS,
        knowledge=km,
        search_knowledge=True,
        tools=build_compiler_tools(km, context_dir=ctx, raw_roots=raw_roots),
        add_datetime_to_context=True,
        markdown=True,
        stream_events=True if kma_stream_events_enabled() else None,
    )


_compiler: Agent | None = None


def get_compiler() -> Agent:
    global _compiler
    if _compiler is None:
        _compiler = build_compiler_agent()
    return _compiler


def __getattr__(name: str):
    if name == "compiler":
        return get_compiler()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
