"""Shared fixtures for integration tests (Postgres, Ollama, OMLX, optional OpenAI embeddings)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def _fetch_ollama_tags() -> dict | None:
    url = f"{OLLAMA_HOST}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None


@pytest.fixture(scope="session")
def ollama_tags() -> dict:
    data = _fetch_ollama_tags()
    if data is None:
        pytest.skip(
            f"Ollama not reachable at {OLLAMA_HOST} "
            "(set OLLAMA_HOST if needed; start the server with ./scripts/starter.sh or `ollama serve`)"
        )
    return data


@pytest.fixture(scope="session")
def ollama_host() -> str:
    return OLLAMA_HOST


@pytest.fixture(scope="session")
def ollama_model_id_for_integration(ollama_tags: dict) -> str:
    """Pick a model to call for integration tests.

    Resolution order:
    1. ``KMA_IT_OLLAMA_MODEL`` if set and present in ``ollama list``
    2. ``get_compiler_model_id()`` if that model is pulled
    3. First name in lexicographic order (stable fallback)
    """
    from kma.config import get_llm_model_id

    names = {m.get("name") for m in ollama_tags.get("models", []) if m.get("name")}
    it_model = os.environ.get("KMA_IT_OLLAMA_MODEL")
    if it_model and it_model in names:
        return it_model
    preferred = get_llm_model_id()
    if preferred in names:
        return preferred
    if names:
        return sorted(names)[0]
    pytest.skip("Ollama has no pulled models (`ollama pull <model>`)")


@pytest.fixture(scope="session")
def ollama_embed_model_available() -> str:
    """Ensure embedding backend is usable (Ollama model pulled, or OpenAI key set)."""
    from kma.config import get_embed_model_id, get_embed_provider

    if get_embed_provider() == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key or not key.strip():
            pytest.skip(
                "KMA_EMBED_PROVIDER=openai requires OPENAI_API_KEY for integration tests "
                "(embeddings are not checked against Ollama in this mode)"
            )
        return get_embed_model_id()

    data = _fetch_ollama_tags()
    if data is None:
        pytest.skip(
            f"Ollama not reachable at {OLLAMA_HOST} "
            "(set OLLAMA_HOST if needed; start the server with ./scripts/starter.sh or `ollama serve`)"
        )
    mid = get_embed_model_id()
    names = {m.get("name") for m in data.get("models", []) if m.get("name")}
    if mid not in names:
        pytest.skip(f"Embedding model {mid!r} not in ollama list (`ollama pull {mid}`)")
    return mid


@pytest.fixture(scope="session")
def require_postgres() -> None:
    """Skip integration tests if Postgres from ``kma.db`` is not reachable."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError

    from kma.db import db_url

    eng = create_engine(db_url)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL not reachable ({db_url!r}): {exc}")
    finally:
        eng.dispose()


@pytest.fixture(scope="session")
def kma_knowledge_it(require_postgres: None):
    """Dedicated Knowledge tables for compiler integration (avoid main ``kma_knowledge``)."""
    from kma.db import create_knowledge

    return create_knowledge("kma IT Knowledge", "kma_knowledge_it")


@pytest.fixture(scope="session")
def kma_learnings_it(require_postgres: None):
    """Dedicated learnings knowledge for Navigator integration (avoid main ``kma_learnings``)."""
    from kma.db import create_knowledge

    return create_knowledge("kma IT Learnings", "kma_learnings_it")


# --- OMLX (mlx) fixtures -----------------------------------------------------

def _fetch_omlx_models(base_url: str) -> dict | None:
    url = f"{base_url.rstrip('/')}/models"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None


@pytest.fixture(scope="session")
def omlx_base_url() -> str:
    from kma.config import get_mlx_base_url

    return get_mlx_base_url()


@pytest.fixture(scope="session")
def omlx_models(omlx_base_url: str) -> dict:
    data = _fetch_omlx_models(omlx_base_url)
    if data is None:
        pytest.skip(f"OMLX not reachable at {omlx_base_url} (start the OMLX server)")
    return data


@pytest.fixture(scope="session")
def omlx_model_id_for_integration(omlx_models: dict) -> str:
    """Pick an OMLX chat model id for integration tests.

    Order: ``KMA_IT_MLX_MODEL`` if present in /models -> configured model id if present
    -> small default ``mlx-community--Qwen3-4B-Instruct-2507-4bit`` if present -> first listed.
    """
    from kma.config import get_llm_model_id

    ids = {m.get("id") for m in omlx_models.get("data", []) if m.get("id")}
    it_model = os.environ.get("KMA_IT_MLX_MODEL")
    if it_model and it_model in ids:
        return it_model
    preferred = get_llm_model_id()
    if preferred in ids:
        return preferred
    small = "mlx-community--Qwen3-4B-Instruct-2507-4bit"
    if small in ids:
        return small
    if ids:
        return sorted(ids)[0]
    pytest.skip("OMLX /models returned no models")


@pytest.fixture(scope="session")
def omlx_embed_model_available(omlx_models: dict) -> str:
    """Ensure the configured mlx embed model is served and dimensions are set."""
    from kma.config import get_embed_dimensions, get_embed_model_id, get_embed_provider

    if get_embed_provider() != "mlx":
        pytest.skip("KMA_EMBED_PROVIDER must be 'mlx' for OMLX embedding integration tests")
    try:
        mid = get_embed_model_id()
        _ = get_embed_dimensions()
    except ValueError as exc:
        pytest.skip(f"OMLX embeddings not configured: {exc}")
    ids = {m.get("id") for m in omlx_models.get("data", []) if m.get("id")}
    if mid not in ids:
        pytest.skip(f"Embedding model {mid!r} not served by OMLX (load it; see /models)")
    return mid
