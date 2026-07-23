import os
from pathlib import Path
from typing import Final, Literal
import logging
from dotenv import load_dotenv

# Prefer explicit path (e.g. KMA_ENV_FILE=tests/it/.env for integration tests).
_env_file = os.getenv("KMA_ENV_FILE")
load_dotenv(_env_file) if _env_file else load_dotenv()


_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(filename)s:%(lineno)d %(message)s"

def setup_logging() -> logging.Logger:
    _LOGGER = logging.getLogger("kma")
    _LOGGER.setLevel(logging.INFO)
    if not _LOGGER.handlers:
        log_path = Path("logs/kma.logs")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path = log_path.with_suffix(".log")
        handler = logging.FileHandler(log_path)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        _LOGGER.addHandler(handler)
    return _LOGGER

setup_logging()
class Env:
    """Environment variable names (sync with repository ``.env``)."""

    # LLM
    KMA_LLM_PROVIDER: Final = "KMA_LLM_PROVIDER"
    KMA_LLM_MODEL_ID: Final = "KMA_LLM_MODEL_ID"
    KMA_LLM_API_KEY: Final = "KMA_LLM_API_KEY"
    KMA_LLM_HOST: Final = "KMA_LLM_HOST"
    KMA_LLM_PORT: Final = "KMA_LLM_PORT"
    KMA_LLM_BASE_URL: Final = "KMA_LLM_BASE_URL"
   
    # Embeddings
    KMA_EMBED_PROVIDER: Final = "KMA_EMBED_PROVIDER"
    KMA_EMBED_MODEL: Final = "KMA_EMBED_MODEL"
    KMA_EMBED_DIMENSIONS: Final = "KMA_EMBED_DIMENSIONS"
    KMA_EMBED_BASE_URL: Final = "KMA_EMBED_BASE_URL"

    # Integrations
    KMA_PARALLEL_API_KEY: Final = "KMA_PARALLEL_API_KEY"  # legacy; unused for search
    KMA_PARALLEL_MAX_RESULTS: Final = "KMA_PARALLEL_MAX_RESULTS"  # legacy alias for web search max
    KMA_PARALLEL_MAX_CHARS_PER_RESULT: Final = "KMA_PARALLEL_MAX_CHARS_PER_RESULT"
    KMA_PARALLEL_INGEST_MAX_CHARS: Final = "KMA_PARALLEL_INGEST_MAX_CHARS"  # legacy alias
    KMA_WEB_SEARCH_MAX_RESULTS: Final = "KMA_WEB_SEARCH_MAX_RESULTS"
    KMA_INGEST_MAX_CHARS: Final = "KMA_INGEST_MAX_CHARS"
    SGAI_API_KEY: Final = "SGAI_API_KEY"
    EXA_API_KEY: Final = "EXA_API_KEY"

     # Context / DB
    KMA_CONTEXT_DIR: Final = "KMA_CONTEXT_DIR"
    KMA_DB_USER: Final = "KMA_DB_USER"
    KMA_DB_PASS: Final = "KMA_DB_PASS"
    KMA_DB_HOST: Final = "KMA_DB_HOST"
    KMA_DB_PORT: Final = "KMA_DB_PORT"
    KMA_DB_DATABASE: Final = "KMA_DB_DATABASE"
   
    # AgentOS / frontend / verify
    KMA_AGENT_OS_HOST: Final = "KMA_AGENT_OS_HOST"
    KMA_AGENT_OS_PORT: Final = "KMA_AGENT_OS_PORT"
    KMA_VITE_PORT: Final = "KMA_VITE_PORT"
   
    KMA_VERIFY_AGENT_DB_CONTAINER: Final = "KMA_VERIFY_AGENT_DB_CONTAINER"
    KMA_VERIFY_TRACE_ENV: Final = "KMA_VERIFY_TRACE_ENV"

    # Agent behavior / Agno
    KMA_NUM_HISTORY_RUNS: Final = "KMA_NUM_HISTORY_RUNS"
    KMA_AGENT_REASONING: Final = "KMA_AGENT_REASONING"
    KMA_STREAM_EVENTS: Final = "KMA_STREAM_EVENTS"
    KMA_SHOW_TEAM_MEMBERS: Final = "KMA_SHOW_TEAM_MEMBERS"
    KMA_AUTO_COMPILE_AFTER_RESEARCH: Final = "KMA_AUTO_COMPILE_AFTER_RESEARCH"
    KMA_STUDIES_ROOT: Final = "KMA_STUDIES_ROOT"
    KMA_ONTOLOGY_ENABLED: Final = "KMA_ONTOLOGY_ENABLED"
    KMA_ONTOLOGY_ENRICH: Final = "KMA_ONTOLOGY_ENRICH"
    AGNO_DEBUG: Final = "AGNO_DEBUG"
    AGNO_DEBUG_LEVEL: Final = "AGNO_DEBUG_LEVEL"


def _env_truthy(name: str) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return False
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _env_first_nonempty(*keys: str) -> str | None:
    for key in keys:
        raw = os.getenv(key)
        if raw is not None and raw.strip() != "":
            return raw.strip()
    return None


# --- public APIs ---
def kma_agent_reasoning_enabled() -> bool:
    """When True, Agno runs an explicit reasoning phase (extra model work; logs + SSE reasoning events)."""
    return _env_truthy(Env.KMA_AGENT_REASONING)


def kma_stream_events_enabled() -> bool:
    """When True, streaming runs emit tool / model / reasoning progress events (see Agno RunEvent / TeamRunEvent)."""
    return _env_truthy(Env.KMA_STREAM_EVENTS)


def kma_show_team_member_responses_enabled() -> bool:
    """When True, team debug surfaces member responses (Agno ``show_members_responses``)."""
    return _env_truthy(Env.KMA_SHOW_TEAM_MEMBERS)


CompilerLlmProvider = Literal["ollama", "openai", "anthropic", "cursor", "mlx"]
EmbedProvider = Literal["ollama", "openai", "mlx", "local", "fastembed"]

_DEFAULT_LLM_MODEL_ID: dict[CompilerLlmProvider, str] = {
    "ollama": "qwen3.6:35b-a3b",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "cursor": "composer-2.5",
    "mlx": "Qwen3.6:27b-4bit",
}

# mlx has no default embedding model; KMA_EMBED_MODEL is required (enforced in get_embed_model_id).
_DEFAULT_EMBED_MODEL_AND_DIMS: dict[
    Literal["ollama", "openai", "mlx", "local", "fastembed"], tuple[str, int]
] = {
    "ollama": ("nomic-embed-text:latest", 768),
    "openai": ("text-embedding-3-small", 1536),
    "mlx": ("embeddinggemma-300m-6bit", 1536),
    "local": ("nomical-modernbert-embed-base-4bit", 768),
    "fastembed": ("BAAI/bge-small-en-v1.5", 384),
}


def get_kma_context_dir() -> Path:
    """Resolved context directory (raw/, wiki/ live under here)."""
    return Path(os.getenv(Env.KMA_CONTEXT_DIR, "./context"))


def get_llm_provider() -> CompilerLlmProvider:
    """Which backend serves the Compiler chat model."""
    raw = (os.getenv(Env.KMA_LLM_PROVIDER) or "ollama").strip().lower()
    if raw not in ("ollama", "openai", "anthropic", "cursor", "mlx"):
        raise ValueError(
            f"Invalid {Env.KMA_LLM_PROVIDER}={raw!r}; expected ollama, openai, anthropic, cursor, or mlx"
        )
    return raw  # type: ignore[return-value]


def get_llm_model_id() -> str:
    """Model id for the Compiler agent for the active ``KMA_LLM_PROVIDER`` (read each call for testability).

    Resolution order: ``KMA_COMPILER_MODEL_ID`` → ``KMA_LLM_MODEL_ID`` → ``KMA_LLM_MODEL`` → ``KMA_MODEL_ID``.
    """

    raw = os.getenv( Env.KMA_LLM_MODEL_ID)
    if raw is not None and raw.strip() != "":
        return raw.strip()
    return _DEFAULT_LLM_MODEL_ID[get_llm_provider()]


def get_embed_provider() -> EmbedProvider:
    """Which backend generates Knowledge / PgVector embeddings."""
    raw = (os.getenv(Env.KMA_EMBED_PROVIDER) or "ollama").strip().lower()
    if raw not in ("ollama", "openai", "mlx", "local", "fastembed"):
        raise ValueError(
            f"Invalid {Env.KMA_EMBED_PROVIDER}={raw!r}; "
            "expected ollama, openai, mlx, local, or fastembed"
        )
    return raw  # type: ignore[return-value]


def get_embed_model_id() -> str:
    """Embedding model id or name for the active ``KMA_EMBED_PROVIDER``."""
    explicit = _env_first_nonempty(Env.KMA_EMBED_MODEL, Env.KMA_EMBED_MODEL)
    if explicit is not None:
        return explicit
    provider = get_embed_provider()
    if provider == "mlx":
        raise ValueError(
            f"{Env.KMA_EMBED_MODEL} is required when {Env.KMA_EMBED_PROVIDER}=mlx "
            "(OMLX has no default embedding model; set it to the model you loaded)"
        )
    return _DEFAULT_EMBED_MODEL_AND_DIMS[provider][0]


def get_embed_dimensions() -> int:
    """Vector size for the embedding model; must match the chosen model."""
    explicit = os.getenv(Env.KMA_EMBED_DIMENSIONS)
    if explicit is not None and explicit.strip() != "":
        try:
            return int(explicit.strip())
        except ValueError:
            raise ValueError(
                f"{Env.KMA_EMBED_DIMENSIONS}={explicit.strip()!r} is not a valid integer"
            )
    provider = get_embed_provider()
    if provider == "mlx":
        raise ValueError(
            f"{Env.KMA_EMBED_DIMENSIONS} is required when {Env.KMA_EMBED_PROVIDER}=mlx "
            "(set it to match the embedding model you loaded into OMLX)"
        )
    return _DEFAULT_EMBED_MODEL_AND_DIMS[provider][1]


def _llm_host_port_base_url() -> str | None:
    """Build ``http://host:port`` from ``KMA_LLM_HOST`` + ``KMA_LLM_PORT`` (legacy ``LLM_*`` accepted)."""
    host = _env_first_nonempty(Env.KMA_LLM_HOST)
    port = _env_first_nonempty(Env.KMA_LLM_PORT)
    if host is None or port is None:
        return None
    h = host.rstrip("/")
    if h.startswith("http://") or h.startswith("https://"):
        return h if ":" in h.rsplit("/", 1)[-1] else f"{h}:{port}"
    return f"http://{h}:{port}"


def get_llm_base_url() -> str:
    """Base URL for the OMLX OpenAI-compatible chat endpoint."""
    raw = os.getenv(Env.KMA_LLM_BASE_URL)
    if raw is not None and raw.strip() != "":
        return raw.strip()
    host_base = _llm_host_port_base_url()
    if host_base is not None:
        base = host_base.rstrip("/")
        return base if base.endswith("/v1") else f"{base}/v1"
    return "http://127.0.0.1:7999/v1"


def get_llm_api_key() -> str:
    """API key string for OMLX. OpenAILike requires a non-empty key; OMLX ignores it."""
    raw = _env_first_nonempty(Env.KMA_LLM_API_KEY, Env.KMA_LLM_API_KEY)
    if raw is not None:
        return raw
    return "not-needed"


def get_embed_base_url() -> str:
    """Base URL for OMLX embeddings; falls back to the chat base URL (same server)."""
    raw = os.getenv(Env.KMA_EMBED_BASE_URL)
    if raw is not None and raw.strip() != "":
        return raw.strip()
    return get_llm_base_url()

def get_embed_host() -> str:
    """Host for OMLX embeddings; falls back to the chat host."""
    raw = get_embed_base_url()
    return raw.split("://")[-1].split(":")[0]


def get_parallel_api_key() -> str | None:
    """Legacy Parallel API key (no longer required for Researcher)."""
    return _env_first_nonempty(Env.KMA_PARALLEL_API_KEY, "PARALLEL_API_KEY")


def _env_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        raise ValueError(f"{name}={raw.strip()!r} is not a valid integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return value


def get_web_search_max_results() -> int:
    """Max DuckDuckGo search hits per Researcher call."""
    raw = os.getenv(Env.KMA_WEB_SEARCH_MAX_RESULTS)
    if raw is not None and str(raw).strip():
        return _env_positive_int(Env.KMA_WEB_SEARCH_MAX_RESULTS, 5)
    return _env_positive_int(Env.KMA_PARALLEL_MAX_RESULTS, 5)


def get_parallel_max_results() -> int:
    """Alias for ``get_web_search_max_results`` (legacy name)."""
    return get_web_search_max_results()


def get_parallel_max_chars_per_result() -> int:
    """Legacy Parallel excerpt limit (unused after DuckDuckGo switch)."""
    return _env_positive_int(Env.KMA_PARALLEL_MAX_CHARS_PER_RESULT, 3000)


def get_ingest_max_chars() -> int:
    """Max chars saved per ``ingest_url`` page fetch."""
    raw = os.getenv(Env.KMA_INGEST_MAX_CHARS)
    if raw is not None and str(raw).strip():
        return _env_positive_int(Env.KMA_INGEST_MAX_CHARS, 8000)
    return _env_positive_int(Env.KMA_PARALLEL_INGEST_MAX_CHARS, 8000)


def get_parallel_ingest_max_chars() -> int:
    """Alias for ``get_ingest_max_chars`` (legacy name)."""
    return get_ingest_max_chars()


def kma_auto_compile_after_research_enabled() -> bool:
    """When True, team enrichment workflow schedules compile+lint after research ingest."""
    raw = os.getenv(Env.KMA_AUTO_COMPILE_AFTER_RESEARCH)
    if raw is None or not str(raw).strip():
        return True
    return _env_truthy(Env.KMA_AUTO_COMPILE_AFTER_RESEARCH)


def get_kma_studies_root() -> Path | None:
    """Optional flink-studies (or similar) repo root for code/ scanning."""
    raw = os.getenv(Env.KMA_STUDIES_ROOT)
    if raw is None or not raw.strip():
        return None
    p = Path(raw.strip()).expanduser()
    return p if p.is_dir() else None


def kma_ontology_enabled() -> bool:
    """When True, rebuild OWL/RDF graph after wiki compile+lint."""
    return _env_truthy(Env.KMA_ONTOLOGY_ENABLED)


def kma_ontology_enrich_enabled() -> bool:
    """When True, run gap-triggered enrichment into proposed.ttl after ontology build."""
    return _env_truthy(Env.KMA_ONTOLOGY_ENRICH)

