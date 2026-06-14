"""Lazy-cached Postgres DB and Knowledge bases for agents."""

from __future__ import annotations

from functools import lru_cache

from agno.db.postgres import PostgresDb
from agno.knowledge import Knowledge

from kma.db import create_knowledge, get_postgres_db


@lru_cache(maxsize=1)
def get_agent_db() -> PostgresDb:
    return get_postgres_db()


@lru_cache(maxsize=1)
def get_kma_knowledge() -> Knowledge:
    return create_knowledge("kma Knowledge", "kma_knowledge")


@lru_cache(maxsize=1)
def get_kma_learnings() -> Knowledge:
    return create_knowledge("kma Learnings", "kma_learnings")


@lru_cache(maxsize=1)
def get_kma_wiki() -> Knowledge:
    return create_knowledge("kma Wiki", "kma_wiki")


def clear_settings_cache() -> None:
    """Reset cached DB/knowledge singletons (for tests)."""
    get_agent_db.cache_clear()
    get_kma_knowledge.cache_clear()
    get_kma_learnings.cache_clear()
    get_kma_wiki.cache_clear()


def __getattr__(name: str):
    if name == "agent_db":
        return get_agent_db()
    if name == "kma_knowledge":
        return get_kma_knowledge()
    if name == "kma_learnings":
        return get_kma_learnings()
    if name == "kma_wiki":
        return get_kma_wiki()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
