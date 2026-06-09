"""Unit test: build_default_llm_model wires OMLX (`mlx`) to OpenAILike. No network."""

from agno.models.openai import OpenAILike

from kma.config import Env
from kma.llm_factory import build_default_llm_model


def test_build_default_llm_model_mlx_defaults(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_LLM_PROVIDER, "mlx")
    for key in (
        Env.KMA_MODEL_ID,
        Env.KMA_LLM_MODEL_ID,
        Env.KMA_LLM_MODEL,
        Env.KMA_COMPILER_MODEL_ID,
        Env.KMA_MLX_BASE_URL,
        Env.KMA_MLX_API_KEY,
        Env.KMA_LLM_HOST,
        Env.KMA_LLM_PORT,
    ):
        monkeypatch.delenv(key, raising=False)

    model = build_default_llm_model()
    assert isinstance(model, OpenAILike)
    assert model.id == "Qwen3.6:27b-4bit"
    assert model.base_url == "http://127.0.0.1:7999/v1"
    assert model.api_key == "not-needed"


def test_build_default_llm_model_mlx_overrides(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_LLM_PROVIDER, "mlx")
    monkeypatch.setenv(Env.KMA_LLM_MODEL_ID, "mlx-community--Qwen3-4B-Instruct-2507-4bit")
    monkeypatch.setenv(Env.KMA_MLX_BASE_URL, "http://localhost:9000/v1")
    monkeypatch.delenv(Env.KMA_MLX_API_KEY, raising=False)

    model = build_default_llm_model()
    assert model.id == "mlx-community--Qwen3-4B-Instruct-2507-4bit"
    assert model.base_url == "http://localhost:9000/v1"
