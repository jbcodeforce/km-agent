"""PostgreSQL connectivity using ``kma.db`` URL configuration."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from kma.db import db_url, get_sql_engine, KMA_SCHEMA, create_knowledge

def test_db_url() -> None:
    assert db_url is not None
    assert db_url.startswith("postgresql+psycopg://")
    assert db_url.endswith("/ai")

def test_postgres_public_schema_exists() -> None:
    """Default ``public`` schema is present on the configured database."""
    engine = get_sql_engine()
    try:
        with engine.connect() as conn:
            one = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.schemata "
                    "WHERE schema_name = 'public' LIMIT 1"
                )
            ).scalar_one()
            assert one == 1
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL not reachable ({db_url!r}): {exc}")
    finally:
        engine.dispose()

def test_postgres_kma_schema_exists() -> None:
    """KMA schema is present on the configured database."""
    engine = get_sql_engine()
    assert engine is not None
    try:
        with engine.connect() as conn:
            one = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.schemata "
                    f"WHERE schema_name = '{KMA_SCHEMA}' LIMIT 1"
                )
            ).scalar_one()
            assert one == 1
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL not reachable ({db_url!r}): {exc}")
    finally:
        engine.dispose()

def test_create_knowledge_base() -> None:
    knowledge_base = create_knowledge(name="test", table_name="test")
    assert knowledge_base is not None
    assert knowledge_base.name == "test"
    assert knowledge_base.vector_db is not None
    assert knowledge_base.contents_db is not None
    print(knowledge_base)