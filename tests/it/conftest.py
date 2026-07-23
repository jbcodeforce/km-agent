"""Shared fixtures for integration tests (Postgres, Ollama, OMLX, optional OpenAI embeddings).

Loads env from ``KMA_ENV_FILE`` (default ``tests/it/.env``, else ``tests/it/.env.example``)
before importing ``kma`` so LLM/DB settings match the IT environment.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from dotenv import load_dotenv

_IT_DIR = Path(__file__).resolve().parent
_DEFAULT_IT_ENV = _IT_DIR / ".env"
_IT_ENV_EXAMPLE = _IT_DIR / ".env.example"


def _bootstrap_it_env() -> Path:
    """Resolve and load the IT env file; set ``KMA_ENV_FILE`` when unset."""
    configured = os.environ.get("KMA_ENV_FILE")
    if configured:
        path = Path(configured).expanduser().resolve()
    elif _DEFAULT_IT_ENV.is_file():
        path = _DEFAULT_IT_ENV
        os.environ["KMA_ENV_FILE"] = str(path)
    elif _IT_ENV_EXAMPLE.is_file():
        path = _IT_ENV_EXAMPLE
        os.environ["KMA_ENV_FILE"] = str(path)
    else:
        raise pytest.UsageError(
            "Integration tests need an env file. Set KMA_ENV_FILE or create "
            f"{_DEFAULT_IT_ENV} (copy from {_IT_ENV_EXAMPLE})."
        )
    if not path.is_file():
        raise pytest.UsageError(f"KMA_ENV_FILE={path} does not exist")
    load_dotenv(path, override=True)
    return path


_IT_ENV_PATH = _bootstrap_it_env()

from kma.config import (  # noqa: E402
    Env,
    get_embed_provider,
    get_llm_model_id,
)


def _build_it_embedder():
    """Build embedder from env; skip IT cleanly when optional extras are missing."""
    from kma.llm_factory import build_default_embedder

    try:
        return build_default_embedder()
    except RuntimeError as exc:
        provider = get_embed_provider()
        if provider == "local":
            pytest.skip(
                f"{Env.KMA_EMBED_PROVIDER}=local requires the local-mlx extra "
                f"(run: uv sync --extra local-mlx). Original error: {exc}"
            )
        if provider == "fastembed":
            pytest.skip(
                f"{Env.KMA_EMBED_PROVIDER}=fastembed requires the fastembed extra "
                f"(run: uv sync --extra fastembed). Original error: {exc}"
            )
        raise


@pytest.fixture(scope="session")
def it_embedder():
    """Session-scoped embedder for IT knowledge bases (matches ``KMA_EMBED_PROVIDER``)."""
    return _build_it_embedder()


@pytest.fixture(scope="session")
def require_postgres() -> None:
    """Skip integration tests if Postgres from ``kma.db`` is not reachable."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError

    from kma.db import build_db_url

    url = build_db_url()
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL not reachable ({url!r}): {exc}")
    finally:
        eng.dispose()


@pytest.fixture(scope="session")
def kma_knowledge_it(require_postgres: None, it_embedder):
    """Dedicated Knowledge tables for compiler integration (avoid main ``kma_knowledge``)."""
    from kma.db import create_knowledge

    return create_knowledge("kma IT Knowledge", "kma_knowledge_it", embedder=it_embedder)


@pytest.fixture(scope="session")
def kma_learnings_it(require_postgres: None, it_embedder):
    """Dedicated learnings knowledge for Navigator integration (avoid main ``kma_learnings``)."""
    from kma.db import create_knowledge

    return create_knowledge("kma IT Learnings", "kma_learnings_it", embedder=it_embedder)


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
    from kma.config import get_llm_base_url

    return get_llm_base_url()


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
    from kma.config import get_embed_dimensions, get_embed_model_id

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
