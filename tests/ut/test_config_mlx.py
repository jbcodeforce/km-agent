"""Config accessors for the OMLX (`mlx`) provider; env-driven, no network."""

import pytest

from kma.config import (
    get_embed_base_url,
    get_embed_dimensions,
    get_embed_model_id,
    get_embed_provider,
    get_llm_provider,
    get_mlx_api_key,
    get_mlx_base_url,
    get_mlx_embed_base_url,
)


def test_llm_provider_accepts_mlx(monkeypatch) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "mlx")
    assert get_llm_provider() == "mlx"


def test_embed_provider_accepts_mlx(monkeypatch) -> None:
    monkeypatch.setenv("KMA_EMBED_PROVIDER", "mlx")
    assert get_embed_provider() == "mlx"


def test_mlx_base_url_default(monkeypatch) -> None:
    monkeypatch.delenv("KMA_MLX_BASE_URL", raising=False)
    assert get_mlx_base_url() == "http://127.0.0.1:7999/v1"


def test_mlx_base_url_override(monkeypatch) -> None:
    monkeypatch.setenv("KMA_MLX_BASE_URL", "http://localhost:9000/v1")
    assert get_mlx_base_url() == "http://localhost:9000/v1"


def test_mlx_api_key_default_is_nonempty(monkeypatch) -> None:
    monkeypatch.delenv("KMA_MLX_API_KEY", raising=False)
    assert get_mlx_api_key() == "not-needed"


def test_mlx_embed_base_url_falls_back_to_chat(monkeypatch) -> None:
    monkeypatch.setenv("KMA_MLX_BASE_URL", "http://host:7999/v1")
    monkeypatch.delenv("KMA_MLX_EMBED_BASE_URL", raising=False)
    assert get_mlx_embed_base_url() == "http://host:7999/v1"


def test_embed_base_url_prefers_kma_then_openai(monkeypatch) -> None:
    monkeypatch.delenv("KMA_EMBED_BASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    assert get_embed_base_url() == "https://api.openai.com/v1"
    monkeypatch.setenv("KMA_EMBED_BASE_URL", "http://127.0.0.1:7999/v1")
    assert get_embed_base_url() == "http://127.0.0.1:7999/v1"


def test_mlx_embed_requires_model_and_dims(monkeypatch) -> None:
    monkeypatch.setenv("KMA_EMBED_PROVIDER", "mlx")
    monkeypatch.delenv("KMA_EMBED_MODEL", raising=False)
    monkeypatch.delenv("KMA_EMBED_DIMENSIONS", raising=False)
    with pytest.raises(ValueError, match="KMA_EMBED_MODEL"):
        get_embed_model_id()
    with pytest.raises(ValueError, match="KMA_EMBED_DIMENSIONS"):
        get_embed_dimensions()


def test_mlx_embed_with_explicit_values(monkeypatch) -> None:
    monkeypatch.setenv("KMA_EMBED_PROVIDER", "mlx")
    monkeypatch.setenv("KMA_EMBED_MODEL", "some-embed-model")
    monkeypatch.setenv("KMA_EMBED_DIMENSIONS", "1024")
    assert get_embed_model_id() == "some-embed-model"
    assert get_embed_dimensions() == 1024


def test_embed_dimensions_non_integer_raises(monkeypatch) -> None:
    monkeypatch.setenv("KMA_EMBED_PROVIDER", "ollama")
    monkeypatch.setenv("KMA_EMBED_DIMENSIONS", "not-a-number")
    with pytest.raises(ValueError, match="not a valid integer"):
        get_embed_dimensions()
