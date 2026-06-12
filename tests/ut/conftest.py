"""Unit-test isolation: mock lowest-level DB APIs before agent modules load."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

_mock_postgres_db = MagicMock(name="PostgresDb")
_mock_knowledge = MagicMock(name="Knowledge")
_mock_engine = MagicMock(name="Engine")

patch("kma.db.get_postgres_db", return_value=_mock_postgres_db).start()
patch("kma.db.create_knowledge", return_value=_mock_knowledge).start()
patch("kma.db.get_sql_engine", return_value=_mock_engine).start()


@pytest.fixture
def mock_postgres_db() -> MagicMock:
    return _mock_postgres_db


@pytest.fixture
def mock_knowledge() -> MagicMock:
    return _mock_knowledge


@pytest.fixture
def mock_llm_model() -> MagicMock:
    model = MagicMock(name="Model")
    model.id = "test-model"
    return model


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    from kma.agents.settings import clear_settings_cache

    clear_settings_cache()
    yield
    clear_settings_cache()
