"""Fire-and-forget background wiki refresh after research ingest."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from kma.config import get_kma_context_dir, kma_auto_compile_after_research_enabled
from kma.workflows.wiki_refresh import refresh_wiki_from_raw

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_pending: set[frozenset[str]] = set()


def schedule_wiki_refresh(
    context_dir: Path | None = None,
    file_ids: list[str] | None = None,
) -> str:
    """Schedule compile + lint in a daemon thread. Returns status message."""
    if not kma_auto_compile_after_research_enabled():
        return "Wiki auto-compile disabled (KMA_AUTO_COMPILE_AFTER_RESEARCH)."

    ctx = (context_dir or get_kma_context_dir()).resolve()
    ids = [f.strip() for f in (file_ids or []) if f and f.strip()]
    if not ids:
        return "No file_ids to compile; background wiki refresh skipped."

    key = frozenset(ids)
    with _lock:
        if key in _pending:
            return f"Wiki refresh already scheduled for {len(ids)} file(s)."
        _pending.add(key)

    def _run() -> None:
        try:
            logger.info("background wiki refresh starting for %d file(s)", len(ids))
            refresh_wiki_from_raw(ctx, ids)
            logger.info("background wiki refresh completed")
        except Exception:
            logger.exception("background wiki refresh failed")
        finally:
            with _lock:
                _pending.discard(key)

    thread = threading.Thread(target=_run, name="wiki-refresh", daemon=True)
    thread.start()
    return f"Scheduled wiki refresh for {len(ids)} file(s) in background."
