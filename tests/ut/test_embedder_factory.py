"""Knowledge embedder selection from environment; no API calls."""

import pytest

from kma.llm_factory import build_default_embedder
from kma.config import Env

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
