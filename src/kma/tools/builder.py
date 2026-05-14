from collections.abc import Sequence
from pathlib import Path

from agno.knowledge import Knowledge
from agno.tools.file import FileTools
from agno.tools.sql import SQLTools
from agno.tools.parallel import ParallelTools

from kma.config import get_kma_context_dir
from kma.tools.compiler_fs import create_compiler_file_tools, use_labelled_raw_paths
from kma.tools.ingest import create_compiler_manifest_tools
from kma.tools.knowledge import create_update_knowledge
from kma.tools.wiki import create_wiki_tools
from kma.db import KMA_SCHEMA, get_sql_engine
from kma.tools.ingest import create_ingest_tools


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
    """Tools for the Compiler agent — reads raw/, writes wiki/.

    Args:
        knowledge: Knowledge base for ``update_knowledge``.
        context_dir: Root containing ``wiki/``; default ``raw/`` is ``context_dir/raw`` unless
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



def build_navigator_tools(knowledge: Knowledge, context_dir: Path | str | None = None) -> list:
    """Tools for the Navigator agent — email, calendar, SQL, files, Exa, wiki reading, manifest.

    Args:
        knowledge: Knowledge base for ``update_knowledge``.
        context_dir: Root containing ``wiki/`` and ``raw/``; defaults to ``get_kma_context_dir()``.
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

    # Manifest access — lets Navigator discover ingested raw sources
    _, _, read_manifest, _ = create_ingest_tools(raw_dir)
    tools.append(read_manifest)

    return tools


def build_researcher_tools(knowledge: Knowledge) -> list:
    """Tools for the Researcher agent — Parallel search/extract + ingest to raw/."""
    raw_dir = get_kma_context_dir() / "raw"
    ingest_url, ingest_text, read_manifest, _ = create_ingest_tools(RAW_DIR)
    return [
        FileTools(base_dir=get_kma_context_dir(), enable_delete_file=False),
        ParallelTools(),
        create_update_knowledge(knowledge),
        ingest_url,
        ingest_text,
        read_manifest,
    ]