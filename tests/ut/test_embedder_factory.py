"""Knowledge embedder selection from environment; no API calls."""

import importlib.util
from unittest.mock import MagicMock, patch

import pytest

from kma.llm_factory import build_default_embedder, _cached_build_default_embedder
from kma.config import Env


@pytest.fixture(autouse=True)
def _clear_embedder_cache() -> None:
    _cached_build_default_embedder.cache_clear()
    yield
    _cached_build_default_embedder.cache_clear()


def _find_spec_with_mlx(name: str):
    if name == "mlx_embeddings":
        return MagicMock()
    return importlib.util.find_spec(name)


@patch("kma.embeddings.local_mlx.load_local_mlx_runtime")
@patch("importlib.util.find_spec", side_effect=_find_spec_with_mlx)
def test_build_default_embedder_local(
    _mock_find_spec: MagicMock,
    mock_load: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_load.return_value = ("mlx-community/nomicai-modernbert-embed-base-4bit", "modernbert")
    monkeypatch.setenv(Env.KMA_EMBED_PROVIDER, "local")
    monkeypatch.delenv(Env.KMA_EMBED_MODEL, raising=False)
    monkeypatch.delenv(Env.KMA_EMBED_DIMENSIONS, raising=False)
    emb = build_default_embedder()
    assert type(emb).__name__ == "LocalMLXEmbedder"
    assert emb.id == "nomical-modernbert-embed-base-4bit"
    assert emb.dimensions == 768


def test_build_default_embedder_local_missing_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(Env.KMA_EMBED_PROVIDER, "local")
    with patch("importlib.util.find_spec", return_value=None):
        with pytest.raises(RuntimeError, match="local-mlx extra"):
            build_default_embedder()


def test_build_default_embedder_ollama(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_EMBED_PROVIDER, "ollama")
    monkeypatch.delenv(Env.KMA_EMBED_MODEL, raising=False)
    monkeypatch.delenv(Env.KMA_EMBED_DIMENSIONS, raising=False)
    emb = build_default_embedder()
    assert type(emb).__name__ == "OllamaEmbedder"
    assert emb.id == "nomic-embed-text:latest"


def test_build_default_embedder_openai(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_EMBED_PROVIDER, "openai")
    monkeypatch.delenv(Env.KMA_EMBED_MODEL, raising=False)
    monkeypatch.delenv(Env.KMA_EMBED_DIMENSIONS, raising=False)
    monkeypatch.setenv(Env.KMA_LLM_API_KEY, "sk-test")
    emb = build_default_embedder()
    assert type(emb).__name__ == "OpenAIEmbedder"
    assert emb.id == "text-embedding-3-small"


def test_build_default_embedder_openai_requires_key(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_EMBED_PROVIDER, "openai")
    monkeypatch.delenv(Env.KMA_LLM_API_KEY, raising=False)
    emb= build_default_embedder()
    assert emb is not None
    assert emb.api_key == "not-needed"


def test_build_default_embedder_mlx(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_EMBED_PROVIDER, "mlx")
    monkeypatch.setenv(Env.KMA_EMBED_MODEL, "some-embed-model")
    monkeypatch.setenv(Env.KMA_EMBED_DIMENSIONS, "1024")
    monkeypatch.setenv(Env.KMA_LLM_BASE_URL, "http://127.0.0.1:7999/v1")
    monkeypatch.delenv(Env.KMA_EMBED_BASE_URL, raising=False)
    monkeypatch.delenv(Env.KMA_LLM_API_KEY, raising=False)
    emb = build_default_embedder()
    assert type(emb).__name__ == "OpenAIEmbedder"
    assert emb.id == "some-embed-model"
    assert emb.dimensions == 1024
    assert emb.base_url == "http://127.0.0.1:7999/v1"
    assert emb.api_key == "not-needed"


def test_build_default_embedder_mlx_requires_model(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_EMBED_PROVIDER, "mlx")
    monkeypatch.delenv(Env.KMA_EMBED_MODEL, raising=False)
    monkeypatch.delenv(Env.KMA_EMBED_DIMENSIONS, raising=False)
    with pytest.raises(ValueError, match=Env.KMA_EMBED_MODEL):
        build_default_embedder()


def test_build_default_embedder_openai_uses_embed_base_url(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_EMBED_PROVIDER, "openai")
    monkeypatch.setenv(Env.KMA_LLM_API_KEY, "sk-test")
    monkeypatch.setenv(Env.KMA_EMBED_BASE_URL, "http://embed.local/v1")
    monkeypatch.delenv(Env.KMA_LLM_BASE_URL, raising=False)
    emb = build_default_embedder()
    assert emb.base_url == "http://embed.local/v1"


def test_build_default_embedder_fastembed(monkeypatch) -> None:
    pytest.importorskip("fastembed")
    monkeypatch.setenv(Env.KMA_EMBED_PROVIDER, "fastembed")
    monkeypatch.delenv(Env.KMA_EMBED_MODEL, raising=False)
    monkeypatch.delenv(Env.KMA_EMBED_DIMENSIONS, raising=False)
    emb = build_default_embedder()
    assert type(emb).__name__ == "FastEmbedEmbedder"
    assert emb.id == "BAAI/bge-small-en-v1.5"
    assert emb.dimensions == 384


def test_build_default_embedder_fastembed_missing_extra(monkeypatch) -> None:
    import importlib.util
    import sys

    monkeypatch.setenv(Env.KMA_EMBED_PROVIDER, "fastembed")
    monkeypatch.setitem(sys.modules, "fastembed", None)
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None if name == "fastembed" else importlib.util.find_spec(name))
    with pytest.raises(RuntimeError, match="fastembed extra"):
        build_default_embedder()
