"""Unit test: build_default_llm_model wires OMLX (`mlx`) to OpenAILike. No network."""

from agno.models.openai import OpenAILike

from kma.llm_factory import build_default_llm_model


def test_build_default_llm_model_mlx_defaults(monkeypatch) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "mlx")
    monkeypatch.delenv("KMA_MODEL_ID", raising=False)
    monkeypatch.delenv("KMA_COMPILER_MODEL_ID", raising=False)
    monkeypatch.delenv("KMA_MLX_BASE_URL", raising=False)
    monkeypatch.delenv("KMA_MLX_API_KEY", raising=False)

    model = build_default_llm_model()
    assert isinstance(model, OpenAILike)
    assert model.id == "Qwen3.6-35B-A3B-UD-MLX-4bit"
    assert model.base_url == "http://127.0.0.1:7999/v1"
    assert model.api_key == "not-needed"


def test_build_default_llm_model_mlx_overrides(monkeypatch) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "mlx")
    monkeypatch.setenv("KMA_MODEL_ID", "mlx-community--Qwen3-4B-Instruct-2507-4bit")
    monkeypatch.setenv("KMA_MLX_BASE_URL", "http://localhost:9000/v1")
    monkeypatch.delenv("KMA_MLX_API_KEY", raising=False)

    model = build_default_llm_model()
    assert model.id == "mlx-community--Qwen3-4B-Instruct-2507-4bit"
    assert model.base_url == "http://localhost:9000/v1"
