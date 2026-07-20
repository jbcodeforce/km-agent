"""Config accessors for the OMLX (`mlx`) provider; env-driven, no network."""

from pathlib import Path


from dotenv import load_dotenv
from kma.config import (
    Env,
    get_embed_dimensions,
    get_embed_model_id,
    get_embed_provider,
    get_embed_host,
    get_llm_model_id,
    get_llm_provider,
    get_llm_base_url,
    get_llm_api_key,
    get_embed_base_url,
    get_parallel_api_key,
    get_parallel_max_chars_per_result,
    get_parallel_max_results,
    get_parallel_ingest_max_chars,
    get_web_search_max_results,
    get_ingest_max_chars,
    kma_agent_reasoning_enabled,
    kma_stream_events_enabled,
    kma_show_team_member_responses_enabled,
    kma_auto_compile_after_research_enabled,
    get_kma_context_dir,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _dotenv_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        keys.add(stripped.split("=", 1)[0].strip())
    return keys


def test_env_constants_match_dotenv() -> None:
    """Every key in repository ``.env`` has a matching ``Env`` constant."""
    dotenv = REPO_ROOT / "example.env"
    assert dotenv.is_file(), f"expected {dotenv}"
    for key in _dotenv_keys(dotenv):
        assert hasattr(Env, key), f"missing Env.{key} for .env entry"
        assert getattr(Env, key) == key

def test_app_settings():
    load_dotenv(REPO_ROOT / "example.env", override=True)
    assert kma_agent_reasoning_enabled() == True
    assert kma_stream_events_enabled() == True
    assert kma_show_team_member_responses_enabled() == True
    assert get_kma_context_dir() == Path("./context")

def test_llm_configs() -> None:
    load_dotenv(REPO_ROOT / "example.env", override=True)
    assert get_llm_provider() == "mlx"
    assert get_llm_model_id() == "Qwen3.6:27b-4bit"
    assert get_llm_base_url() == "http://localhost:7999/v1"
    assert get_llm_api_key() == "not-needed"

    assert get_embed_provider() == "local"
    assert get_embed_model_id() == "nomical-modernbert-embed-base-4bit"
    assert get_embed_dimensions() == 768

def test_web_search_and_ingest_config_defaults(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_PARALLEL_API_KEY, "test-key")
    monkeypatch.delenv(Env.KMA_WEB_SEARCH_MAX_RESULTS, raising=False)
    monkeypatch.delenv(Env.KMA_PARALLEL_MAX_RESULTS, raising=False)
    monkeypatch.delenv(Env.KMA_PARALLEL_MAX_CHARS_PER_RESULT, raising=False)
    monkeypatch.delenv(Env.KMA_INGEST_MAX_CHARS, raising=False)
    monkeypatch.delenv(Env.KMA_PARALLEL_INGEST_MAX_CHARS, raising=False)
    assert get_parallel_api_key() == "test-key"
    assert get_web_search_max_results() == 5
    assert get_parallel_max_results() == 5
    assert get_parallel_max_chars_per_result() == 3000
    assert get_ingest_max_chars() == 8000
    assert get_parallel_ingest_max_chars() == 8000


def test_auto_compile_after_research(monkeypatch) -> None:
    monkeypatch.setenv(Env.KMA_AUTO_COMPILE_AFTER_RESEARCH, "0")
    assert kma_auto_compile_after_research_enabled() is False

    monkeypatch.delenv(Env.KMA_AUTO_COMPILE_AFTER_RESEARCH, raising=False)
    assert kma_auto_compile_after_research_enabled() is True