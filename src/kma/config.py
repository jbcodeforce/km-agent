import os
from pathlib import Path
from typing import Literal

# Default context root (string) for env files and backward compatibility.
KMA_CONTEXT_DIR = os.getenv("KMA_CONTEXT_DIR", "./context")

PARALLEL_API_KEY = os.getenv("PARALLEL_API_KEY")

CompilerLlmProvider = Literal["ollama", "openai", "anthropic"]
EmbedProvider = Literal["ollama", "openai"]

_DEFAULT_COMPILER_MODEL: dict[CompilerLlmProvider, str] = {
    "ollama": "qwen3.6:35b-a3b",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
}

_DEFAULT_EMBED_MODEL_AND_DIMS: dict[EmbedProvider, tuple[str, int]] = {
    "ollama": ("nomic-embed-text:latest", 768),
    "openai": ("text-embedding-3-small", 1536),
}


def get_kma_context_dir() -> Path:
    """Resolved context directory (raw/, wiki/ live under here)."""
    return Path(os.getenv("KMA_CONTEXT_DIR", "./context"))


def get_llm_provider() -> CompilerLlmProvider:
    """Which backend serves the Compiler chat model."""
    raw = (os.getenv("KMA_LLM_PROVIDER") or "ollama").strip().lower()
    if raw not in ("ollama", "openai", "anthropic"):
        raise ValueError(
            f"Invalid KMA_LLM_PROVIDER={raw!r}; expected ollama, openai, or anthropic"
        )
    return raw  # type: ignore[return-value]


def get_llm_model_id() -> str:
    """Model id for the Compiler agent for the active ``KMA_LLM_PROVIDER`` (read each call for testability).

    ``KMA_COMPILER_MODEL_ID`` wins when set; otherwise ``KMA_MODEL_ID`` (see ``example.env``).
    """
    for key in ("KMA_COMPILER_MODEL_ID", "KMA_MODEL_ID"):
        raw = os.getenv(key)
        if raw is not None and raw.strip() != "":
            return raw.strip()
    return _DEFAULT_COMPILER_MODEL[get_llm_provider()]


def get_embed_provider() -> EmbedProvider:
    """Which backend generates Knowledge / PgVector embeddings."""
    raw = (os.getenv("KMA_EMBED_PROVIDER") or "ollama").strip().lower()
    if raw not in ("ollama", "openai"):
        raise ValueError(f"Invalid KMA_EMBED_PROVIDER={raw!r}; expected ollama or openai")
    return raw  # type: ignore[return-value]


def get_embed_model_id() -> str:
    """Embedding model id or name for the active ``KMA_EMBED_PROVIDER``."""
    explicit = os.getenv("KMA_EMBED_MODEL")
    if explicit is not None and explicit.strip() != "":
        return explicit.strip()
    return _DEFAULT_EMBED_MODEL_AND_DIMS[get_embed_provider()][0]


def get_embed_dimensions() -> int:
    """Vector size for the embedding model; must match the chosen model."""
    explicit = os.getenv("KMA_EMBED_DIMENSIONS")
    if explicit is not None and explicit.strip() != "":
        return int(explicit.strip())
    return _DEFAULT_EMBED_MODEL_AND_DIMS[get_embed_provider()][1]


def get_ollama_embed_host() -> str | None:
    """Base URL for the ollama-python embed client (no ``/v1`` suffix).

    ``OLLAMA_EMBED_HOST`` overrides; otherwise ``OLLAMA_HOST`` is normalized
    (OpenAI-compatible URLs may end with ``/v1`` — stripped for the embed client).
    """
    raw = (os.getenv("OLLAMA_EMBED_HOST") or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434").strip()
    raw = raw.rstrip("/")
    if raw.endswith("/v1"):
        raw = raw[:-3].rstrip("/")
    return raw or None
