import os
from pathlib import Path
from typing import Literal

# Default context root (string) for env files and backward compatibility.
KMA_CONTEXT_DIR = os.getenv("KMA_CONTEXT_DIR", "./context")


def _env_truthy(name: str) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return False
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def kma_agent_reasoning_enabled() -> bool:
    """When True, Agno runs an explicit reasoning phase (extra model work; logs + SSE reasoning events)."""
    return _env_truthy("KMA_AGENT_REASONING")


def kma_stream_events_enabled() -> bool:
    """When True, streaming runs emit tool / model / reasoning progress events (see Agno RunEvent / TeamRunEvent)."""
    return _env_truthy("KMA_STREAM_EVENTS")


def kma_show_team_member_responses_enabled() -> bool:
    """When True, team debug surfaces member responses (Agno ``show_members_responses``)."""
    return _env_truthy("KMA_SHOW_TEAM_MEMBERS")


def _env_first_nonempty(*keys: str) -> str | None:
    for key in keys:
        raw = os.getenv(key)
        if raw is not None and raw.strip() != "":
            return raw.strip()
    return None


PARALLEL_API_KEY = _env_first_nonempty("KMA_PARALLEL_API_KEY", "PARALLEL_API_KEY")

CompilerLlmProvider = Literal["ollama", "openai", "anthropic", "cursor", "mlx"]
EmbedProvider = Literal["ollama", "openai", "mlx"]

_DEFAULT_COMPILER_MODEL: dict[CompilerLlmProvider, str] = {
    "ollama": "qwen3.6:35b-a3b",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "cursor": "composer-2.5",
    "mlx": "Qwen3.6-35B-A3B-UD-MLX-4bit",
}

_DEFAULT_EMBED_MODEL_AND_DIMS: dict[Literal["ollama", "openai"], tuple[str, int]] = {
    "ollama": ("nomic-embed-text:latest", 768),
    "openai": ("text-embedding-3-small", 1536),
}


def get_kma_context_dir() -> Path:
    """Resolved context directory (raw/, wiki/ live under here)."""
    return Path(os.getenv("KMA_CONTEXT_DIR", "./context"))


def get_llm_provider() -> CompilerLlmProvider:
    """Which backend serves the Compiler chat model."""
    raw = (os.getenv("KMA_LLM_PROVIDER") or "ollama").strip().lower()
    if raw not in ("ollama", "openai", "anthropic", "cursor", "mlx"):
        raise ValueError(
            f"Invalid KMA_LLM_PROVIDER={raw!r}; expected ollama, openai, anthropic, cursor, or mlx"
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
    if raw not in ("ollama", "openai", "mlx"):
        raise ValueError(f"Invalid KMA_EMBED_PROVIDER={raw!r}; expected ollama, openai, or mlx")
    return raw  # type: ignore[return-value]


def get_embed_model_id() -> str:
    """Embedding model id or name for the active ``KMA_EMBED_PROVIDER``."""
    explicit = os.getenv("KMA_EMBED_MODEL")
    if explicit is not None and explicit.strip() != "":
        return explicit.strip()
    provider = get_embed_provider()
    if provider == "mlx":
        raise ValueError(
            "KMA_EMBED_MODEL is required when KMA_EMBED_PROVIDER=mlx "
            "(OMLX has no default embedding model; set it to the model you loaded)"
        )
    return _DEFAULT_EMBED_MODEL_AND_DIMS[provider][0]


def get_embed_dimensions() -> int:
    """Vector size for the embedding model; must match the chosen model."""
    explicit = os.getenv("KMA_EMBED_DIMENSIONS")
    if explicit is not None and explicit.strip() != "":
        try:
            return int(explicit.strip())
        except ValueError:
            raise ValueError(
                f"KMA_EMBED_DIMENSIONS={explicit.strip()!r} is not a valid integer"
            )
    provider = get_embed_provider()
    if provider == "mlx":
        raise ValueError(
            "KMA_EMBED_DIMENSIONS is required when KMA_EMBED_PROVIDER=mlx "
            "(set it to match the embedding model you loaded into OMLX)"
        )
    return _DEFAULT_EMBED_MODEL_AND_DIMS[provider][1]


def get_mlx_base_url() -> str:
    """Base URL for the OMLX OpenAI-compatible chat endpoint."""
    raw = os.getenv("KMA_MLX_BASE_URL")
    if raw is not None and raw.strip() != "":
        return raw.strip()
    return "http://127.0.0.1:7999/v1"


def get_mlx_api_key() -> str:
    """API key string for OMLX. OpenAILike requires a non-empty key; OMLX ignores it."""
    raw = os.getenv("KMA_MLX_API_KEY")
    if raw is not None and raw.strip() != "":
        return raw.strip()
    return "not-needed"


def get_mlx_embed_base_url() -> str:
    """Base URL for OMLX embeddings; falls back to the chat base URL (same server)."""
    raw = os.getenv("KMA_MLX_EMBED_BASE_URL")
    if raw is not None and raw.strip() != "":
        return raw.strip()
    return get_mlx_base_url()


def get_embed_base_url() -> str | None:
    """Base URL for the OpenAI-compatible embedder (decoupled from chat).

    Prefers ``KMA_EMBED_BASE_URL`` then ``OPENAI_BASE_URL``; ``None`` means the
    OpenAI client default.
    """
    for key in ("KMA_EMBED_BASE_URL", "OPENAI_BASE_URL"):
        raw = os.getenv(key)
        if raw is not None and raw.strip() != "":
            return raw.strip()
    return None


def get_cursor_runtime() -> Literal["local", "cloud"]:
    """Cursor SDK runtime for ``KMA_LLM_PROVIDER=cursor``."""
    raw = (os.getenv("KMA_CURSOR_RUNTIME") or "local").strip().lower()
    if raw not in ("local", "cloud"):
        raise ValueError(f"Invalid KMA_CURSOR_RUNTIME={raw!r}; expected local or cloud")
    return raw  # type: ignore[return-value]


def get_cursor_cwd() -> str | None:
    """Workspace directory for local Cursor agents."""
    raw = os.getenv("KMA_CURSOR_CWD")
    if raw is not None and raw.strip() != "":
        return raw.strip()
    context = os.getenv("KMA_CONTEXT_DIR")
    if context is not None and context.strip() != "":
        return str(Path(context).resolve())
    return None


def get_cursor_repo_url() -> str | None:
    """Git repository URL for cloud Cursor agents."""
    return _env_first_nonempty("KMA_CURSOR_REPO", "CURSOR_CLOUD_REPO")


def get_cursor_repo_ref() -> str:
    """Starting git ref for cloud Cursor agents."""
    return _env_first_nonempty("KMA_CURSOR_REPO_REF", "CURSOR_CLOUD_REPO_REF") or "main"


def get_cursor_auto_create_pr() -> bool:
    """When True, cloud Cursor agents open a PR after successful runs."""
    return _env_truthy("KMA_CURSOR_AUTO_CREATE_PR")


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
