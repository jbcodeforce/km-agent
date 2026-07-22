from collections.abc import Sequence
from pathlib import Path
import json
from typing import Tuple
from agno.knowledge import Knowledge
from agno.tools import tool
from agno.tools.file import FileTools
from agno.tools.sql import SQLTools
from agno.tools.duckduckgo import DuckDuckGoTools

from kma.config import (
    get_kma_context_dir,
    get_web_search_max_results,
)
from kma.tools.compiler_fs import create_compiler_file_tools, use_labelled_raw_paths
from kma.tools.ingest import create_compiler_manifest_tools, create_ingest_tools, list_uncompiled_file_ids
from kma.tools.knowledge import create_update_knowledge, create_search_wiki
from kma.tools.site_refs import create_read_web_site_refs_tool
from kma.tools.ontology_tools import create_ontology_tools
from kma.tools.wiki import create_wiki_tools
from kma.db import KMA_SCHEMA, get_sql_engine


def _get_paths(context_dir: Path | str | None = None, raw_roots: Sequence[tuple[str, Path]] | None = None) -> tuple[Path, list[tuple[str, Path]], Path]:
    base = Path(context_dir) if context_dir is not None else get_kma_context_dir()
    base = base.resolve()
    roots: list[tuple[str, Path]] = (
        [(str(lab), Path(path).resolve()) for lab, path in raw_roots]
        if raw_roots is not None
        else [("raw", (base / "raw").resolve())]
    )
    wiki_dir = base / "wiki"
    return base, roots, wiki_dir


def build_compiler_tools(
    knowledge: Knowledge,
    context_dir: Path | str | None = None,
    raw_roots: Sequence[tuple[str, Path]] | None = None,
) -> list:
    """
    Tools for the Compiler agent — reads docs/ or wiki/raw, writes wiki/.

    Args:
        knowledge: Knowledge base for ``update_knowledge``.
        context_dir: Root containing ``wiki/``; default ``raw/`` is ``context_dir/wiki/raw`` unless
            ``raw_roots`` overrides where raw documents live.
        raw_roots: Optional ``(label, path)`` list. Multiple roots or a single non-default
            raw directory use virtual paths ``raw/<label>/...`` and merged manifests.
    """
    base, roots, wiki_dir = _get_paths(context_dir, raw_roots)
    use_custom_fs = use_labelled_raw_paths(roots, base)
    read_manifest, update_compiled = create_compiler_manifest_tools(base, roots)
    file_part: list = (
        create_compiler_file_tools(base, roots)
        if use_custom_fs
        else [FileTools(base_dir=base, enable_delete_file=False)]
    )
    return [
        *file_part,
        create_update_knowledge(knowledge),
        read_manifest,
        update_compiled,
        *create_wiki_tools(wiki_dir),
    ]



def build_navigator_tools(
    knowledge: Knowledge,
    context_dir: Path | str | None = None,
    wiki_knowledge: Knowledge | None = None,
) -> list:
    """Tools for the Navigator agent — SQL, files, wiki reading, ontology, manifest.

    Args:
        knowledge: Knowledge base for ``update_knowledge``.
        context_dir: Root containing ``wiki/`` and ``raw/``; defaults to ``get_kma_context_dir()``.
        wiki_knowledge: Optional ``kma_wiki`` base for ``search_wiki`` semantic recall.
    """
    base = Path(context_dir).resolve() if context_dir is not None else get_kma_context_dir().resolve()
    tools: list = [
        SQLTools(db_engine=get_sql_engine(), schema=KMA_SCHEMA),
        FileTools(base_dir=base, enable_delete_file=False),
        create_update_knowledge(knowledge),
        # MCPTools(url=EXA_MCP_URL),
    ]
    wiki_dir = base / "wiki"
    raw_dir = base / "raw"
    # create_wiki_tools returns: [read_index, update_index, read_state, update_state]
    read_wiki_index, _, read_wiki_state, _ = create_wiki_tools(wiki_dir)
    tools.extend([read_wiki_index, read_wiki_state])
    tools.extend(create_ontology_tools(base))
    if wiki_knowledge is not None:
        tools.append(create_search_wiki(wiki_knowledge))

    # Manifest access — lets Navigator discover ingested raw sources
    _, _, read_manifest, *_ = create_ingest_tools(raw_dir)
    tools.append(read_manifest)

    return tools


def build_researcher_tools(
    knowledge: Knowledge,
    context_dir: Path  | None = None) -> list:
    """Tools for the Researcher agent — DuckDuckGo search + ingest to raw/."""
    ctx_dir = Path(context_dir or get_kma_context_dir()).resolve()
    raw_dir = ctx_dir / "raw"
    ingest_url, ingest_text, read_manifest, _, sync_raw_manifest_from_disk = create_ingest_tools(raw_dir)
    return [
        FileTools(base_dir=ctx_dir, enable_delete_file=False),
        DuckDuckGoTools(
            enable_search=True,
            enable_news=False,
            fixed_max_results=get_web_search_max_results(),
        ),
        create_update_knowledge(knowledge),
        create_read_web_site_refs_tool(ctx_dir),
        ingest_url,
        ingest_text,
        read_manifest,
        sync_raw_manifest_from_disk,
    ]

def build_linter_tools(knowledge: Knowledge,
    context_dir: Path | str | None = None) -> list:
    """
    Tools for the Linter agent — reads wiki/, writes lint reports, 
    web search for gaps.
    """
    ctx_dir = context_dir or get_kma_context_dir()
    wiki_dir = ctx_dir / "wiki"
    read_wiki_index, _, read_wiki_state, update_wiki_state = create_wiki_tools(wiki_dir)
    return [
        FileTools(base_dir=ctx_dir, enable_delete_file=False),
        create_update_knowledge(knowledge),
        read_wiki_index,
        read_wiki_state,
        update_wiki_state,
        *create_ontology_tools(Path(ctx_dir).resolve()),
    ]


def _parse_wiki_refresh_file_ids(raw: str) -> list[str]:
    text = raw.strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass
    return [part.strip() for part in text.split(",") if part.strip()]


def build_team_tools(context_dir: Path | str | None = None) -> list:
    """Tools for the kma team leader — background wiki refresh after research ingest."""
    ctx = Path(context_dir).resolve() if context_dir is not None else get_kma_context_dir().resolve()
    raw_dir = ctx / "raw"

    @tool
    def trigger_wiki_refresh(file_ids: str = "") -> str:
        """Schedule background compile + lint for newly ingested raw files.

        Call after Researcher ingests content. Pass comma-separated filenames
        (e.g. ``flink-2-news.md,another.md``) or a JSON array string.
        When ``file_ids`` is empty, all uncompiled entries under ``raw/`` are refreshed.

        Args:
            file_ids: New raw manifest file names from Researcher, or empty for all uncompiled.

        Returns:
            Scheduling status (compile and lint run in background; user is not blocked).
        """
        ids = _parse_wiki_refresh_file_ids(file_ids)
        if not ids:
            ids = list_uncompiled_file_ids(ctx)
        from kma.workflows.background import schedule_wiki_refresh

        return schedule_wiki_refresh(ctx, ids)

    return [trigger_wiki_refresh]