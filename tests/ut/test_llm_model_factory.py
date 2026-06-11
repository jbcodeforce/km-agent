"""Unit test: build_default_llm_model wires OMLX (`mlx`) to OpenAILike. No network."""

from agno.models.ollama import OllamaResponses
from agno.models.openai import OpenAILike, OpenAIResponses
from dotenv import load_dotenv
from kma.config import Env
from kma.llm_factory import build_default_llm_model, build_default_embedder
from pathlib import Path
from agno.knowledge.embedder.openai import OpenAIEmbedder
REPO_ROOT = Path(__file__).resolve().parents[2]

def test_build_default_llm_model_mlx_defaults() -> None:
    load_dotenv(REPO_ROOT / "example.env", override=True)
    model = build_default_llm_model()
    assert isinstance(model, OpenAILike)
    assert model.id == "Qwen3.6:27b-4bit"
    assert model.base_url == "http://localhost:7999/v1"
    assert model.api_key == "not-needed"


def test_build_default_llm_model_mlx_overrides(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_LLM_PROVIDER, "mlx")
    monkeypatch.setenv(Env.KMA_LLM_MODEL_ID, "mlx-community--Qwen3-4B-Instruct-2507-4bit")
    monkeypatch.setenv(Env.KMA_LLM_BASE_URL, "http://localhost:9000/v1")
    monkeypatch.delenv(Env.KMA_LLM_API_KEY, raising=False)

    model = build_default_llm_model()
    assert model.id == "mlx-community--Qwen3-4B-Instruct-2507-4bit"
    assert model.base_url == "http://localhost:9000/v1"
    assert isinstance(model, OpenAILike)

def test_build_default_llm_ollama_provider(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_LLM_PROVIDER, "ollama")
    monkeypatch.setenv(Env.KMA_LLM_MODEL_ID, "qwen3.6:35b-a3b")
    monkeypatch.setenv(Env.KMA_LLM_HOST, "http://localhost:11434")
    monkeypatch.setenv(Env.KMA_LLM_BASE_URL, "http://localhost:11434/v1")
    monkeypatch.setenv(Env.KMA_LLM_PORT, "11434")

    model = build_default_llm_model()
    assert model.id == "qwen3.6:35b-a3b"
    assert model.base_url == "http://localhost:11434/v1"
    assert isinstance(model, OllamaResponses)

def test_build_default_llm_openai_provider(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_LLM_PROVIDER, "openai")
    monkeypatch.setenv(Env.KMA_LLM_MODEL_ID, "gpt-4o")
    monkeypatch.setenv(Env.KMA_LLM_BASE_URL, "http://localhost:11434/v1")
    monkeypatch.setenv(Env.KMA_LLM_API_KEY, "not-needed")
    monkeypatch.setenv(Env.KMA_LLM_PORT, "11434")

    model = build_default_llm_model()
    assert model.id == "gpt-4o"
    assert model.base_url == "http://localhost:11434/v1"
    assert isinstance(model, OpenAIResponses)

def test_build_default_embedder_mlx() -> None:
    load_dotenv(REPO_ROOT / "example.env", override=True)
    embedder = build_default_embedder()
    assert isinstance(embedder, OpenAIEmbedder)
    assert embedder.id == "embeddinggemma-300m-6bit"
    assert embedder.dimensions == 2048
    assert embedder.base_url == "http://localhost:7999/v1"
    assert embedder.api_key == "not-needed"
    src_text = "This is a test text"
    embedding = embedder.get_embedding(text=src_text)
    assert len(embedding) > 512