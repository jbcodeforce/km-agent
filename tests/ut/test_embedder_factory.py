"""Knowledge embedder selection from environment; no API calls."""

import pytest

from kma.db import build_default_embedder


def test_build_default_embedder_ollama(monkeypatch) -> None:
    monkeypatch.setenv("KMA_EMBED_PROVIDER", "ollama")
    monkeypatch.delenv("KMA_EMBED_MODEL", raising=False)
    monkeypatch.delenv("KMA_EMBED_DIMENSIONS", raising=False)
    emb = build_default_embedder()
    assert type(emb).__name__ == "OllamaEmbedder"
    assert emb.id == "nomic-embed-text:latest"


def test_build_default_embedder_openai(monkeypatch) -> None:
    monkeypatch.setenv("KMA_EMBED_PROVIDER", "openai")
    monkeypatch.delenv("KMA_EMBED_MODEL", raising=False)
    monkeypatch.delenv("KMA_EMBED_DIMENSIONS", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    emb = build_default_embedder()
    assert type(emb).__name__ == "OpenAIEmbedder"
    assert emb.id == "text-embedding-3-small"


def test_build_default_embedder_openai_requires_key(monkeypatch) -> None:
    monkeypatch.setenv("KMA_EMBED_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        build_default_embedder()
