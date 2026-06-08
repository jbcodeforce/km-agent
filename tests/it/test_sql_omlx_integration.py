"""Integration: capture/retrieve/organize against the kma schema (Navigator SQL backbone)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from kma.db import KMA_SCHEMA, get_sql_engine

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KMA_IT_MLX") != "1",
        reason="set KMA_IT_MLX=1 to run integration suite",
    ),
]


@pytest.mark.usefixtures("require_postgres")
def test_capture_retrieve_organize_in_kma_schema() -> None:
    engine = get_sql_engine()  # bootstraps CREATE SCHEMA IF NOT EXISTS kma + search_path
    table = "kma_it_notes"
    try:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            conn.execute(text(f"CREATE TABLE {table} (id serial primary key, topic text, body text)"))
            # capture
            conn.execute(
                text(f"INSERT INTO {table} (topic, body) VALUES (:t, :b)"),
                {"t": "flink", "b": "Kafka is a common Flink source"},
            )
        with engine.connect() as conn:
            # retrieve
            row = conn.execute(text(f"SELECT topic, body FROM {table} WHERE topic = :t"), {"t": "flink"}).one()
            assert row.topic == "flink"
            assert "Kafka" in row.body
            # confirm schema isolation: table lives in kma schema
            schema = conn.execute(
                text(
                    "SELECT table_schema FROM information_schema.tables WHERE table_name = :n"
                ),
                {"n": table},
            ).scalar_one()
            assert schema == KMA_SCHEMA
        with engine.begin() as conn:
            # organize: rename column (a structural change agents may propose)
            conn.execute(text(f"ALTER TABLE {table} RENAME COLUMN body TO content"))
        with engine.connect() as conn:
            row = conn.execute(text(f"SELECT content FROM {table} WHERE topic = :t"), {"t": "flink"}).one()
            assert "Kafka" in row.content
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        engine.dispose()
