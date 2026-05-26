"""Wiki tools — read/update the wiki index and state."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from agno.tools import tool

def get_or_create_wiki_paths(context_dir: Path) -> tuple[Path,Path,Path]:
    if not context_dir.is_dir():
        Path.mkdir(context_dir)
    docs_dir = context_dir / "docs"
    if not docs_dir.is_dir():
        Path.mkdir(docs_dir)
    wiki_dir = context_dir / "wiki"
    if not wiki_dir.is_dir():
        Path.mkdir(wiki_dir)
    raw_dir = wiki_dir / "raw"
    if not raw_dir.is_dir():
        Path.mkdir(raw_dir)
    return (context_dir, docs_dir, wiki_dir)


def create_wiki_tools(wiki_dir: Path):
    """Create wiki management tools bound to the wiki/ directory.

    Args:
        wiki_dir: Path to wiki/ (resolved from KMA_CONTEXT_DIR).

    Returns:
        List of tool functions.
    """

    @tool
    def read_wiki_index() -> str:
        """Read the wiki index to see all compiled articles and their summaries.

        Returns:
            The full content of wiki/index.md.
        """
        index_path = wiki_dir / "index.md"
        if index_path.exists():
            return index_path.read_text()
        return "Wiki index is empty. No articles compiled yet."

    @tool
    def update_wiki_index(content: str) -> str:
        """Replace the wiki index with updated content."""
        index_path = wiki_dir / "index.md"
        index_path.write_text(content)
        return "Wiki index updated."

    @tool
    def read_wiki_state() -> str:
        """Read the wiki state (last compile time, counts, last lint time)."""
        state_path = wiki_dir / ".state.json"
        if state_path.exists():
            return state_path.read_text()
        return json.dumps(
            {"last_compiled": None, "article_count": 0, "source_count": 0, "output_count": 0, "last_lint": None}
        )

    @tool
    def update_wiki_state(
        article_count: int | None = None,
        source_count: int | None = None,
        output_count: int | None = None,
        mark_compiled: bool = False,
        mark_linted: bool = False,
    ) -> str:
        """Update the wiki state after compilation or linting."""
        state_path = wiki_dir / ".state.json"
        if state_path.exists():
            state = json.loads(state_path.read_text())
        else:
            state = {"last_compiled": None, "article_count": 0, "source_count": 0, "output_count": 0, "last_lint": None}

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if mark_compiled:
            state["last_compiled"] = now
        if mark_linted:
            state["last_lint"] = now
        if article_count is not None:
            state["article_count"] = article_count
        if source_count is not None:
            state["source_count"] = source_count
        if output_count is not None:
            state["output_count"] = output_count

        state_path.write_text(json.dumps(state, indent=2) + "\n")
        return f"Wiki state updated: {json.dumps(state)}"

    return [read_wiki_index, update_wiki_index, read_wiki_state, update_wiki_state]
