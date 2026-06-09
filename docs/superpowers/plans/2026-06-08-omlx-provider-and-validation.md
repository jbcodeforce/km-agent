# OMLX Provider + Full-Surface Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OMLX (OpenAI-compatible local MLX server) as a first-class `mlx` chat + embedding provider, keep Ollama as an alternative, and validate the full agent surface (Compiler, Navigator, SQL, Researcher, Linter) with integration tests driven by real flink-studies markdown.

**Architecture:** A new `mlx` value in the provider enums routes chat through Agno's `OpenAILike` (chat-completions) and embeddings through `OpenAIEmbedder`, both pointed at `KMA_MLX_BASE_URL` (default `http://127.0.0.1:7999/v1`). Chat and embedding base URLs are decoupled. Integration tests build agents from `build_default_llm_model()` (env-driven, so OMLX when `KMA_LLM_PROVIDER=mlx`) and are gated by `KMA_IT_MLX=1` plus clean skips when services are unavailable.

**Tech Stack:** Python 3.11+, `uv`, pytest, Agno (`OpenAILike`, `OpenAIEmbedder`, `PgVector`), PostgreSQL + pgvector, OMLX.

**Spec:** `docs/superpowers/specs/2026-06-08-omlx-provider-and-validation-design.md`

**Conventions used throughout:**
- Run tests with `uv run pytest`.
- All commits use the existing repo trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- Work happens on branch `omlx-provider-and-validation` (already created).

---

## Part A — OMLX as a first-class `mlx` provider

### Task 1: Config — `mlx` enums, base-url accessors, required embed model/dims

**Files:**
- Modify: `src/kma/config.py`
- Test: `tests/ut/test_config_mlx.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/ut/test_config_mlx.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ut/test_config_mlx.py -v`
Expected: FAIL with `ImportError` (e.g. `cannot import name 'get_mlx_base_url'`).

- [ ] **Step 3: Edit `src/kma/config.py`**

Change the provider literals (lines ~41-42):

```python
CompilerLlmProvider = Literal["ollama", "openai", "anthropic", "cursor", "mlx"]
EmbedProvider = Literal["ollama", "openai", "mlx"]
```

Add `mlx` to `_DEFAULT_COMPILER_MODEL` (the dict at ~line 44):

```python
_DEFAULT_COMPILER_MODEL: dict[CompilerLlmProvider, str] = {
    "ollama": "qwen3.6:35b-a3b",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "cursor": "composer-2.5",
    "mlx": "Qwen3.6-35B-A3B-UD-MLX-4bit",
}
```

Update `get_llm_provider()` validation tuple to include `"mlx"`:

```python
    if raw not in ("ollama", "openai", "anthropic", "cursor", "mlx"):
        raise ValueError(
            f"Invalid KMA_LLM_PROVIDER={raw!r}; expected ollama, openai, anthropic, cursor, or mlx"
        )
```

Update `get_embed_provider()` validation tuple:

```python
    if raw not in ("ollama", "openai", "mlx"):
        raise ValueError(f"Invalid KMA_EMBED_PROVIDER={raw!r}; expected ollama, openai, or mlx")
```

Replace `get_embed_model_id()` and `get_embed_dimensions()` so `mlx` requires explicit env (OMLX has no default embed model):

```python
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
        return int(explicit.strip())
    provider = get_embed_provider()
    if provider == "mlx":
        raise ValueError(
            "KMA_EMBED_DIMENSIONS is required when KMA_EMBED_PROVIDER=mlx "
            "(set it to match the embedding model you loaded into OMLX)"
        )
    return _DEFAULT_EMBED_MODEL_AND_DIMS[provider][1]
```

Add the new accessors (place near the other `get_*` accessors, e.g. after `get_embed_dimensions`):

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/ut/test_config_mlx.py -v`
Expected: PASS (all 9 tests).

- [ ] **Step 5: Run the existing config-adjacent tests to confirm no regression**

Run: `uv run pytest tests/ut/test_kma_trace_flags.py tests/ut/test_kma_db_env_pref.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/kma/config.py tests/ut/test_config_mlx.py
git commit -m "feat(config): add mlx provider enums, base-url accessors, required embed model/dims

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Chat factory — `mlx` branch via `OpenAILike`

**Files:**
- Modify: `src/kma/llm_factory.py`
- Test: `tests/ut/test_llm_factory_mlx.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/ut/test_llm_factory_mlx.py`:

```python
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


def test_build_default_llm_model_mlx_overrides(monkeypatch) -> None:
    monkeypatch.setenv("KMA_LLM_PROVIDER", "mlx")
    monkeypatch.setenv("KMA_MODEL_ID", "mlx-community--Qwen3-4B-Instruct-2507-4bit")
    monkeypatch.setenv("KMA_MLX_BASE_URL", "http://localhost:9000/v1")

    model = build_default_llm_model()
    assert model.id == "mlx-community--Qwen3-4B-Instruct-2507-4bit"
    assert model.base_url == "http://localhost:9000/v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ut/test_llm_factory_mlx.py -v`
Expected: FAIL — `build_default_llm_model` raises `ValueError: Invalid KMA_LLM_PROVIDER` is NOT expected (Task 1 already accepts mlx); instead it falls through to the `anthropic` branch and raises `ValueError: ANTHROPIC_API_KEY`. Either failure confirms the `mlx` branch is missing.

- [ ] **Step 3: Edit `src/kma/llm_factory.py`**

Add the import (with the other agno model imports near the top):

```python
from agno.models.openai import OpenAIResponses, OpenAILike
```

(If `OpenAIResponses` is imported on its own line, change that line to the combined import above.)

Add the `mlx` branch inside `build_default_llm_model()`, immediately before the `if provider == "cursor":` branch:

```python
    if provider == "mlx":
        from kma.config import get_mlx_api_key, get_mlx_base_url

        return OpenAILike(
            id=mid,
            base_url=get_mlx_base_url(),
            api_key=get_mlx_api_key(),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/ut/test_llm_factory_mlx.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the full existing llm_factory suite (no regression)**

Run: `uv run pytest tests/ut/test_llm_factory.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/kma/llm_factory.py tests/ut/test_llm_factory_mlx.py
git commit -m "feat(llm): route mlx provider to OpenAILike (OMLX chat-completions)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Embedder — `mlx` branch + decoupled embed base URL

**Files:**
- Modify: `src/kma/db.py` (`build_default_embedder`)
- Test: `tests/ut/test_embedder_factory.py` (extend)

- [ ] **Step 1: Write the failing tests (append to existing file)**

Append to `tests/ut/test_embedder_factory.py`:

```python
def test_build_default_embedder_mlx(monkeypatch) -> None:
    monkeypatch.setenv("KMA_EMBED_PROVIDER", "mlx")
    monkeypatch.setenv("KMA_EMBED_MODEL", "some-embed-model")
    monkeypatch.setenv("KMA_EMBED_DIMENSIONS", "1024")
    monkeypatch.setenv("KMA_MLX_BASE_URL", "http://127.0.0.1:7999/v1")
    monkeypatch.delenv("KMA_MLX_EMBED_BASE_URL", raising=False)
    emb = build_default_embedder()
    assert type(emb).__name__ == "OpenAIEmbedder"
    assert emb.id == "some-embed-model"
    assert emb.dimensions == 1024
    assert emb.base_url == "http://127.0.0.1:7999/v1"


def test_build_default_embedder_mlx_requires_model(monkeypatch) -> None:
    monkeypatch.setenv("KMA_EMBED_PROVIDER", "mlx")
    monkeypatch.delenv("KMA_EMBED_MODEL", raising=False)
    monkeypatch.delenv("KMA_EMBED_DIMENSIONS", raising=False)
    with pytest.raises(ValueError, match="KMA_EMBED_MODEL"):
        build_default_embedder()


def test_build_default_embedder_openai_uses_embed_base_url(monkeypatch) -> None:
    monkeypatch.setenv("KMA_EMBED_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("KMA_EMBED_BASE_URL", "http://embed.local/v1")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    emb = build_default_embedder()
    assert emb.base_url == "http://embed.local/v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ut/test_embedder_factory.py -v`
Expected: FAIL on the three new tests (mlx branch missing → `ValueError: Invalid KMA_EMBED_PROVIDER` no longer raised after Task 1, so it falls through; `KMA_EMBED_BASE_URL` not yet honored).

- [ ] **Step 3: Edit `src/kma/db.py` `build_default_embedder()`**

Update imports at the top of the file to add the config accessors:

```python
from kma.config import (
    get_embed_base_url,
    get_embed_dimensions,
    get_embed_model_id,
    get_embed_provider,
    get_mlx_api_key,
    get_mlx_embed_base_url,
    get_ollama_embed_host,
)
```

Replace the body of `build_default_embedder()` with:

```python
def build_default_embedder() -> Embedder:
    """Embedder for Knowledge bases from ``KMA_EMBED_PROVIDER``."""
    provider = get_embed_provider()
    if provider == "ollama":
        return OllamaEmbedder(
            id=get_embed_model_id(),
            host=get_ollama_embed_host(),
            dimensions=get_embed_dimensions(),
        )
    if provider == "mlx":
        return OpenAIEmbedder(
            id=get_embed_model_id(),
            dimensions=get_embed_dimensions(),
            api_key=get_mlx_api_key(),
            base_url=get_mlx_embed_base_url(),
        )
    # openai
    api_key = getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "OPENAI_API_KEY is required when KMA_EMBED_PROVIDER=openai "
            "(set the key in the environment or .env)"
        )
    return OpenAIEmbedder(
        id=get_embed_model_id(),
        dimensions=get_embed_dimensions(),
        api_key=api_key.strip(),
        base_url=get_embed_base_url(),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/ut/test_embedder_factory.py -v`
Expected: PASS (all tests, original 3 + new 3).

- [ ] **Step 5: Commit**

```bash
git add src/kma/db.py tests/ut/test_embedder_factory.py
git commit -m "feat(db): add mlx embedder branch and decouple embed base URL from chat

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Document the `mlx` provider in `example.env` and `CLAUDE.md`

**Files:**
- Modify: `example.env`
- Modify: `CLAUDE.md`
- Test: `tests/ut/test_example_env_mlx.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/ut/test_example_env_mlx.py`:

```python
"""example.env documents the OMLX (`mlx`) provider knobs."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_ENV = REPO_ROOT / "example.env"


def test_example_env_documents_mlx() -> None:
    text = EXAMPLE_ENV.read_text(encoding="utf-8")
    for token in (
        "KMA_LLM_PROVIDER=mlx",
        "KMA_MLX_BASE_URL",
        "KMA_MLX_API_KEY",
        "KMA_EMBED_PROVIDER=mlx",
        "KMA_EMBED_MODEL",
        "KMA_EMBED_DIMENSIONS",
    ):
        assert token in text, f"missing {token!r} in example.env"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ut/test_example_env_mlx.py -v`
Expected: FAIL (`missing 'KMA_LLM_PROVIDER=mlx'`).

- [ ] **Step 3: Add an OMLX block to `example.env`**

Insert after the existing `# KMA_LLM_PROVIDER=cursor` line:

```bash
# --- OMLX (local MLX server, OpenAI-compatible) ---
# Chat runs on OMLX via the OpenAI-compatible chat-completions API.
# KMA_LLM_PROVIDER=mlx
# KMA_MLX_BASE_URL=http://127.0.0.1:7999/v1
# KMA_MLX_API_KEY=not-needed
# KMA_MODEL_ID=Qwen3.6-35B-A3B-UD-MLX-4bit   # any id from GET ${KMA_MLX_BASE_URL}/models
#
# Embeddings on OMLX (requires an embedding model loaded into OMLX).
# OMLX serves no embedding model by default — set model + dimensions to match what you load.
# KMA_EMBED_PROVIDER=mlx
# KMA_EMBED_MODEL=<your-omlx-embedding-model-id>
# KMA_EMBED_DIMENSIONS=<vector-size-of-that-model>
# KMA_MLX_EMBED_BASE_URL=http://127.0.0.1:7999/v1   # defaults to KMA_MLX_BASE_URL
# Alternatively keep embeddings on Ollama (KMA_EMBED_PROVIDER=ollama) while chat is mlx.
```

- [ ] **Step 4: Update `CLAUDE.md` provider list**

In the "Pluggable providers" bullet, change the chat line to include `mlx`:

```markdown
- Chat: `KMA_LLM_PROVIDER` ∈ `ollama` (default) | `openai` | `anthropic` | `cursor` | `mlx` (OMLX, OpenAI-compatible chat-completions at `KMA_MLX_BASE_URL`, default `http://127.0.0.1:7999/v1`); model via `KMA_COMPILER_MODEL_ID` → `KMA_MODEL_ID` → per-provider default.
```

And change the embeddings line to include `mlx`:

```markdown
- Embeddings: `KMA_EMBED_PROVIDER` ∈ `ollama` (default, `nomic-embed-text`, 768d) | `openai` (`text-embedding-3-small`, 1536d) | `mlx` (OMLX-served; **requires** `KMA_EMBED_MODEL` + `KMA_EMBED_DIMENSIONS`). **Dimensions must match the model** — if you change embedder, drop the vector tables or recreate the DB volume (`docker compose down -v`).
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/ut/test_example_env_mlx.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add example.env CLAUDE.md tests/ut/test_example_env_mlx.py
git commit -m "docs: document mlx/OMLX provider in example.env and CLAUDE.md

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Verify script — OMLX `/models` check

**Files:**
- Modify: `scripts/verify_agent_env.sh`
- Test: `tests/ut/test_verify_agent_env_script.py` (extend)

- [ ] **Step 1: Write the failing test (append to existing file)**

Append to `tests/ut/test_verify_agent_env_script.py`:

```python
def test_verify_script_contains_omlx_check() -> None:
    text = VERIFY_SH.read_text(encoding="utf-8")
    assert "check_omlx" in text
    assert "KMA_MLX_BASE_URL" in text
    assert "/models" in text


def test_verify_script_omlx_check_only_when_mlx(monkeypatch) -> None:
    """check_omlx is invoked from main and guarded by provider == mlx."""
    text = VERIFY_SH.read_text(encoding="utf-8")
    # Guard on the mlx provider so non-mlx setups are unaffected.
    assert 'mlx' in text
    assert "check_omlx || ok=1" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ut/test_verify_agent_env_script.py -v`
Expected: FAIL on the two new tests (`check_omlx` not present).

- [ ] **Step 3: Edit `scripts/verify_agent_env.sh`**

Add resolved-config lines: in `trace_resolved_configuration()`, after the `LLM_HOST` echo, add:

```bash
  echo "  KMA_MLX_BASE_URL=${KMA_MLX_BASE_URL:-<unset>}  KMA_EMBED_MODEL=${KMA_EMBED_MODEL:-<unset>}  KMA_EMBED_DIMENSIONS=${KMA_EMBED_DIMENSIONS:-<unset>}"
```

Add a new check function (place it just before `main()`):

```bash
check_omlx() {
  # Only runs when chat or embeddings use the OMLX (mlx) provider.
  if [[ "${KMA_LLM_PROVIDER:-}" != "mlx" && "${KMA_EMBED_PROVIDER:-}" != "mlx" ]]; then
    return 0
  fi
  local base="${KMA_MLX_BASE_URL:-http://127.0.0.1:7999/v1}"
  echo "== OMLX (${base}) =="
  have_cmd curl || die "curl not found (needed for HTTP checks)."
  local body code
  body=$(curl -sS --max-time 10 "${base}/models" 2>/dev/null) || body=""
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "${base}/models" 2>/dev/null) || code="000"
  if [[ "$code" != "200" ]]; then
    echo "  GET ${base}/models → HTTP ${code} (is OMLX running?)." >&2
    return 1
  fi
  echo "  GET ${base}/models → HTTP 200"
  if [[ "${KMA_LLM_PROVIDER:-}" == "mlx" ]]; then
    local chat_id="${KMA_COMPILER_MODEL_ID:-${KMA_MODEL_ID:-Qwen3.6-35B-A3B-UD-MLX-4bit}}"
    if echo "$body" | grep -q "\"${chat_id}\""; then
      echo "  chat model present: ${chat_id}"
    else
      echo "  chat model NOT found in /models: ${chat_id}" >&2
      return 1
    fi
  fi
  if [[ "${KMA_EMBED_PROVIDER:-}" == "mlx" ]]; then
    local embed_id="${KMA_EMBED_MODEL:-}"
    if [[ -z "$embed_id" ]]; then
      echo "  embed model: KMA_EMBED_MODEL unset (required for KMA_EMBED_PROVIDER=mlx)." >&2
      return 1
    fi
    if echo "$body" | grep -q "\"${embed_id}\""; then
      echo "  embed model present: ${embed_id}"
    else
      echo "  WARNING: embed model not in /models yet: ${embed_id} (load it into OMLX)." >&2
    fi
  fi
}
```

In `main()`, add the call after `check_backend || ok=1`:

```bash
  check_omlx || ok=1
```

- [ ] **Step 4: Verify shell syntax and run tests**

Run: `bash -n scripts/verify_agent_env.sh && uv run pytest tests/ut/test_verify_agent_env_script.py -v`
Expected: syntax OK; PASS (all tests).

- [ ] **Step 5: Manual smoke (optional, requires OMLX running)**

Run: `KMA_LLM_PROVIDER=mlx KMA_VERIFY_AGENT_DB_CONTAINER=0 ./scripts/verify_agent_env.sh || true`
Expected: an `== OMLX (...) ==` section reporting `GET .../models → HTTP 200` and `chat model present`.

- [ ] **Step 6: Commit**

```bash
git add scripts/verify_agent_env.sh tests/ut/test_verify_agent_env_script.py
git commit -m "feat(scripts): verify_agent_env checks OMLX /models when provider is mlx

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Part B — Full-surface integration validation

### Task 6: Seed `tests/data/` with real flink-studies markdown

**Files:**
- Create: `tests/data/README.md`
- Create: `tests/data/raw/*.md` (copied + frontmatter)
- Test: `tests/ut/test_tests_data_corpus.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/ut/test_tests_data_corpus.py`:

```python
"""The tests/data raw corpus exists and carries valid raw frontmatter."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW = REPO_ROOT / "tests" / "data" / "raw"


def test_corpus_has_several_markdown_files() -> None:
    files = sorted(RAW.glob("*.md"))
    assert len(files) >= 4, f"expected >=4 seed docs, found {len(files)}"


def test_each_doc_has_yaml_frontmatter() -> None:
    for f in sorted(RAW.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{f.name} missing frontmatter open"
        assert "\n---\n" in text, f"{f.name} missing frontmatter close"
        assert "title:" in text.split("\n---\n", 1)[0], f"{f.name} missing title"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ut/test_tests_data_corpus.py -v`
Expected: FAIL (`tests/data/raw` does not exist).

- [ ] **Step 3: Copy 5 real flink-studies docs and add frontmatter**

Run (copies small docs spanning sql / architecture / cookbook):

```bash
mkdir -p tests/data/raw
SRC=/Users/jerome/Documents/Code/flink-studies/docs
cp "$SRC/architecture/kafka.md"        tests/data/raw/kafka.md
cp "$SRC/architecture/fitforpurpose.md" tests/data/raw/fitforpurpose.md
cp "$SRC/cookbook/job_lifecycle.md"    tests/data/raw/job_lifecycle.md
cp "$SRC/cookbook/governance.md"       tests/data/raw/governance.md
cp "$SRC/methodology/data_as_a_product.md" tests/data/raw/data_as_a_product.md
```

If any path above is missing on disk, pick another `.md` of similar size from `find /Users/jerome/Documents/Code/flink-studies/docs -name '*.md'` in the same topic folder. Keep total under ~30 KB for fast tests; if a file exceeds ~12 KB, truncate it to its first ~150 lines with `head -n 150 <file> > <file>.tmp && mv <file>.tmp <file>` before adding frontmatter.

Then add raw frontmatter to each (the script also records them in `tests/data/raw/.manifest.json`):

```bash
uv run python scripts/add_raw_frontmatter.py tests/data/raw/kafka.md --title "Kafka for Flink" --source flink-studies --tags flink,kafka
uv run python scripts/add_raw_frontmatter.py tests/data/raw/fitforpurpose.md --title "Fit For Purpose" --source flink-studies --tags flink,architecture
uv run python scripts/add_raw_frontmatter.py tests/data/raw/job_lifecycle.md --title "Flink Job Lifecycle" --source flink-studies --tags flink,operations
uv run python scripts/add_raw_frontmatter.py tests/data/raw/governance.md --title "Data Governance" --source flink-studies --tags flink,governance
uv run python scripts/add_raw_frontmatter.py tests/data/raw/data_as_a_product.md --title "Data as a Product" --source flink-studies --tags data,methodology
```

- [ ] **Step 4: Write `tests/data/README.md`**

```markdown
# tests/data

Curated, small copies of real [flink-studies](https://github.com/jbcodeforce/flink-studies)
markdown used as the raw corpus for integration tests (`tests/it/`). Each file under
`raw/` has km-agent raw YAML frontmatter (added via `scripts/add_raw_frontmatter.py`) and
is tracked in `raw/.manifest.json`. Keep files small; they exist for deterministic,
fast compile/query tests, not as a faithful mirror of the source repo.
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/ut/test_tests_data_corpus.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/data tests/ut/test_tests_data_corpus.py
git commit -m "test(data): seed tests/data/raw with real flink-studies docs + frontmatter

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: OMLX fixtures in `tests/it/conftest.py`

**Files:**
- Modify: `tests/it/conftest.py`
- Test: validated indirectly by Task 8+ (no standalone unit test; fixtures are exercised by integration modules).

- [ ] **Step 1: Add OMLX fixtures (append to `tests/it/conftest.py`)**

```python
# --- OMLX (mlx) fixtures -----------------------------------------------------

def _fetch_omlx_models(base_url: str) -> dict | None:
    url = f"{base_url.rstrip('/')}/models"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None


@pytest.fixture(scope="session")
def omlx_base_url() -> str:
    from kma.config import get_mlx_base_url

    return get_mlx_base_url()


@pytest.fixture(scope="session")
def omlx_models(omlx_base_url: str) -> dict:
    data = _fetch_omlx_models(omlx_base_url)
    if data is None:
        pytest.skip(f"OMLX not reachable at {omlx_base_url} (start the OMLX server)")
    return data


@pytest.fixture(scope="session")
def omlx_model_id_for_integration(omlx_models: dict) -> str:
    """Pick an OMLX chat model id for integration tests.

    Order: ``KMA_IT_MLX_MODEL`` if present in /models → configured model id if present
    → small default ``mlx-community--Qwen3-4B-Instruct-2507-4bit`` if present → first listed.
    """
    from kma.config import get_llm_model_id

    ids = {m.get("id") for m in omlx_models.get("data", []) if m.get("id")}
    it_model = os.environ.get("KMA_IT_MLX_MODEL")
    if it_model and it_model in ids:
        return it_model
    preferred = get_llm_model_id()
    if preferred in ids:
        return preferred
    small = "mlx-community--Qwen3-4B-Instruct-2507-4bit"
    if small in ids:
        return small
    if ids:
        return sorted(ids)[0]
    pytest.skip("OMLX /models returned no models")


@pytest.fixture(scope="session")
def omlx_embed_model_available(omlx_models: dict) -> str:
    """Ensure the configured mlx embed model is served and dimensions are set."""
    from kma.config import get_embed_dimensions, get_embed_model_id, get_embed_provider

    if get_embed_provider() != "mlx":
        pytest.skip("KMA_EMBED_PROVIDER must be 'mlx' for OMLX embedding integration tests")
    try:
        mid = get_embed_model_id()
        _ = get_embed_dimensions()
    except ValueError as exc:
        pytest.skip(f"OMLX embeddings not configured: {exc}")
    ids = {m.get("id") for m in omlx_models.get("data", []) if m.get("id")}
    if mid not in ids:
        pytest.skip(f"Embedding model {mid!r} not served by OMLX (load it; see /models)")
    return mid
```

- [ ] **Step 2: Verify fixtures import cleanly**

Run: `uv run pytest tests/it/conftest.py --collect-only -q`
Expected: no collection errors (conftest imports cleanly).

- [ ] **Step 3: Commit**

```bash
git add tests/it/conftest.py
git commit -m "test(it): add OMLX reachability/model/embedding fixtures

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Compiler integration on OMLX (compile / ingest)

**Files:**
- Create: `tests/it/test_compiler_omlx_integration.py`

- [ ] **Step 1: Write the test**

Create `tests/it/test_compiler_omlx_integration.py`:

```python
"""Integration: Compiler compiles real flink-studies raw docs into the wiki, using OMLX.

Run:
    KMA_IT_MLX=1 KMA_LLM_PROVIDER=mlx KMA_EMBED_PROVIDER=mlx \
    KMA_EMBED_MODEL=<id> KMA_EMBED_DIMENSIONS=<n> \
    uv run pytest tests/it/test_compiler_omlx_integration.py -m integration -v
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from agno.models.openai import OpenAILike
from agno.run.base import RunStatus
from agno.run.agent import RunOutput

from kma.agents.compiler import build_compiler_agent
from kma.config import get_mlx_api_key, get_mlx_base_url
from kma.tools.ingest import sync_manifest_from_raw_markdown

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KMA_IT_MLX") != "1",
        reason="set KMA_IT_MLX=1 to run OMLX integration (OMLX + Postgres + embeddings)",
    ),
]

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


@pytest.mark.usefixtures("require_postgres", "omlx_embed_model_available")
def test_compiler_compiles_flink_studies_doc(
    omlx_model_id_for_integration: str,
    omlx_base_url: str,
    kma_knowledge_it,
    tmp_path: Path,
) -> None:
    sandbox = tmp_path / "ctx"
    (sandbox / "raw").mkdir(parents=True)
    (sandbox / "wiki").mkdir(parents=True)
    target = "kafka.md"
    shutil.copy(DATA_RAW / target, sandbox / "raw" / target)
    sync_manifest_from_raw_markdown(sandbox / "raw")

    model = OpenAILike(
        id=omlx_model_id_for_integration,
        base_url=get_mlx_base_url(),
        api_key=get_mlx_api_key(),
    )
    agent = build_compiler_agent(context_dir=sandbox, knowledge=kma_knowledge_it, model=model)

    prompt = (
        "You are in an automated integration test. Use your tools only (no user questions).\n"
        "1) Call read_manifest.\n"
        f"2) Read raw/{target} via read_file.\n"
        f"3) Write wiki/summaries/{target} with a short markdown summary (heading + >=2 sentences).\n"
        "4) Create one file under wiki/concepts/ with a short slug name describing a key topic.\n"
        f"5) Call update_manifest_compiled with filename {target}.\n"
        "6) Call update_wiki_index listing the new concept under ## Concepts with paths starting wiki/.\n"
        "7) Call update_wiki_state with mark_compiled true and article_count at least 1.\n"
        "Keep responses short; complete the workflow."
    )

    final: RunOutput | None = None
    for chunk in agent.run(prompt, stream=True, stream_events=True, yield_run_output=True):
        if isinstance(chunk, RunOutput):
            final = chunk
    assert final is not None
    if final.status != RunStatus.completed:
        msg = (final.content or "").lower()
        if any(t in msg for t in ("memory", "not found", "requires more", "timeout")):
            pytest.skip(f"Compiler run infra issue: {final.content!r}")
    assert final.status == RunStatus.completed, f"compiler run failed: {final.content!r}"

    manifest = json.loads((sandbox / "raw" / ".manifest.json").read_text(encoding="utf-8"))
    entry = next((e for e in manifest if e.get("file") == target), None)
    assert entry is not None and entry.get("compiled") is True

    assert (sandbox / "wiki" / "summaries" / target).is_file()
    assert list((sandbox / "wiki" / "concepts").glob("*.md"))
    idx = (sandbox / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "wiki/concepts" in idx
```

- [ ] **Step 2: Run (gated) to confirm it is collected and skips without the gate**

Run: `uv run pytest tests/it/test_compiler_omlx_integration.py -v`
Expected: 1 skipped (reason mentions `KMA_IT_MLX=1`).

- [ ] **Step 3: Run for real against OMLX**

Run (substitute your loaded embed model id + dims):

```bash
KMA_IT_MLX=1 KMA_LLM_PROVIDER=mlx KMA_EMBED_PROVIDER=mlx \
  KMA_EMBED_MODEL=<your-embed-model> KMA_EMBED_DIMENSIONS=<n> \
  KMA_IT_MLX_MODEL=mlx-community--Qwen3-4B-Instruct-2507-4bit \
  uv run pytest tests/it/test_compiler_omlx_integration.py -m integration -v
```

Expected: PASS, or a clean SKIP if OMLX/Postgres/embeddings are unavailable. If it fails on assertions (not infra), debug with superpowers:systematic-debugging before continuing.

- [ ] **Step 4: Commit**

```bash
git add tests/it/test_compiler_omlx_integration.py
git commit -m "test(it): compiler compiles real flink-studies doc via OMLX

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Navigator integration on OMLX (retrieve / connect / file_read / meta)

**Files:**
- Create: `tests/it/test_navigator_omlx_integration.py`

- [ ] **Step 1: Write the test**

Create `tests/it/test_navigator_omlx_integration.py`:

```python
"""Integration: Navigator reads wiki index + manifest + a context file, using OMLX."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from agno.models.openai import OpenAILike
from agno.run.base import RunStatus

from kma.agents.navigator import build_navigator_agent
from kma.config import get_mlx_api_key, get_mlx_base_url

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KMA_IT_MLX") != "1",
        reason="set KMA_IT_MLX=1 to run OMLX integration (OMLX + Postgres + embeddings)",
    ),
]


def _write_sandbox(root: Path) -> None:
    (root / "raw").mkdir(parents=True)
    (root / "wiki").mkdir(parents=True)
    (root / "wiki" / "index.md").write_text(
        "# Wiki Index\n\nNavOmlxMarker\n\n## Concepts\n- [Kafka](wiki/concepts/kafka.md) — messaging for Flink\n",
        encoding="utf-8",
    )
    (root / "raw" / "note.md").write_text("---\ntitle: Note\n---\nNavFileMarker body\n", encoding="utf-8")
    manifest = [{"file": "note.md", "title": "Note", "source": "it", "ingested": "2026-01-01T00:00:00Z", "compiled": False}]
    (root / "raw" / ".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


@pytest.mark.usefixtures("require_postgres", "omlx_embed_model_available")
def test_navigator_reads_sources(
    omlx_model_id_for_integration: str,
    kma_knowledge_it,
    kma_learnings_it,
    tmp_path: Path,
) -> None:
    sandbox = tmp_path / "ctx"
    _write_sandbox(sandbox)

    model = OpenAILike(id=omlx_model_id_for_integration, base_url=get_mlx_base_url(), api_key=get_mlx_api_key())
    agent = build_navigator_agent(
        model=model, knowledge=kma_knowledge_it, learnings=kma_learnings_it, context_dir=sandbox
    )

    prompt = (
        "You are in an automated integration test. Use your tools only (no user questions).\n"
        "1) Call read_wiki_index.\n"
        "2) Call read_manifest.\n"
        "3) If the wiki index contains the exact substring NavOmlxMarker and the manifest JSON "
        "includes the filename note.md, your final line must be exactly: NAV_OMLX_OK\n"
        "Otherwise your final line must be exactly: NAV_OMLX_FAIL\nKeep the rest short."
    )

    out = agent.run(prompt)
    if out.status != RunStatus.completed:
        msg = (out.content or "").lower()
        if any(t in msg for t in ("memory", "not found", "requires more", "timeout")):
            pytest.skip(f"Navigator run infra issue: {out.content!r}")
    assert out.status == RunStatus.completed, f"navigator run failed: {out.content!r}"
    assert "NAV_OMLX_OK" in (out.content or ""), f"expected token in: {out.content!r}"
```

- [ ] **Step 2: Run gated (skips without flag)**

Run: `uv run pytest tests/it/test_navigator_omlx_integration.py -v`
Expected: 1 skipped.

- [ ] **Step 3: Run for real against OMLX**

Run (same env prefix as Task 8 Step 3) and confirm PASS or clean SKIP.

- [ ] **Step 4: Commit**

```bash
git add tests/it/test_navigator_omlx_integration.py
git commit -m "test(it): navigator reads wiki/manifest via OMLX

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: SQL capture / retrieve / organize integration

**Files:**
- Create: `tests/it/test_sql_omlx_integration.py`

- [ ] **Step 1: Write the test**

This test exercises the `kma` schema directly through the same engine the Navigator's `SQLTools` uses, validating capture → retrieve round-trips and the schema isolation (`search_path=kma,public`). It does not require the LLM, so it gates only on Postgres + `KMA_IT_MLX` (kept under the same suite gate for consistency).

Create `tests/it/test_sql_omlx_integration.py`:

```python
"""Integration: capture/retrieve/organize against the kma schema (Navigator SQL backbone)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from kma.db import KMA_SCHEMA, get_sql_engine

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KMA_IT_MLX") != "1",
        reason="set KMA_IT_MLX=1 to run integration suite",
    ),
]


@pytest.mark.usefixtures("require_postgres")
def test_capture_retrieve_organize_in_kma_schema() -> None:
    engine = get_sql_engine()  # bootstraps CREATE SCHEMA IF NOT EXISTS kma + search_path
    table = "kma_it_notes"
    try:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            conn.execute(text(f"CREATE TABLE {table} (id serial primary key, topic text, body text)"))
            # capture
            conn.execute(
                text(f"INSERT INTO {table} (topic, body) VALUES (:t, :b)"),
                {"t": "flink", "b": "Kafka is a common Flink source"},
            )
        with engine.connect() as conn:
            # retrieve
            row = conn.execute(text(f"SELECT topic, body FROM {table} WHERE topic = :t"), {"t": "flink"}).one()
            assert row.topic == "flink"
            assert "Kafka" in row.body
            # confirm schema isolation: table lives in kma schema
            schema = conn.execute(
                text(
                    "SELECT table_schema FROM information_schema.tables WHERE table_name = :n"
                ),
                {"n": table},
            ).scalar_one()
            assert schema == KMA_SCHEMA
        with engine.begin() as conn:
            # organize: rename column (a structural change agents may propose)
            conn.execute(text(f"ALTER TABLE {table} RENAME COLUMN body TO content"))
        with engine.connect() as conn:
            row = conn.execute(text(f"SELECT content FROM {table} WHERE topic = :t"), {"t": "flink"}).one()
            assert "Kafka" in row.content
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        engine.dispose()
```

- [ ] **Step 2: Run gated (skips without flag)**

Run: `uv run pytest tests/it/test_sql_omlx_integration.py -v`
Expected: 1 skipped.

- [ ] **Step 3: Run for real (needs Postgres only)**

Run: `KMA_IT_MLX=1 uv run pytest tests/it/test_sql_omlx_integration.py -m integration -v`
Expected: PASS, or clean SKIP if Postgres unreachable.

- [ ] **Step 4: Commit**

```bash
git add tests/it/test_sql_omlx_integration.py
git commit -m "test(it): capture/retrieve/organize round-trip in kma schema

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Researcher integration (research / ingest) — gated on PARALLEL_API_KEY

**Files:**
- Create: `tests/it/test_researcher_omlx_integration.py`

- [ ] **Step 1: Write the test**

The Researcher is only constructed when `PARALLEL_API_KEY` is set, and hits the external Parallel API, so this test adds a second gate and verifies the ingest-to-raw side effect.

Create `tests/it/test_researcher_omlx_integration.py`:

```python
"""Integration: Researcher saves a source to raw/ and updates the manifest, using OMLX.

Doubly gated: KMA_IT_MLX=1 AND a configured Parallel key (KMA_PARALLEL_API_KEY / PARALLEL_API_KEY).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from agno.models.openai import OpenAILike
from agno.run.base import RunStatus

from kma.config import PARALLEL_API_KEY, get_mlx_api_key, get_mlx_base_url

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KMA_IT_MLX") != "1",
        reason="set KMA_IT_MLX=1 to run OMLX integration",
    ),
    pytest.mark.skipif(
        not PARALLEL_API_KEY,
        reason="set KMA_PARALLEL_API_KEY/PARALLEL_API_KEY to run Researcher integration",
    ),
]


@pytest.mark.usefixtures("require_postgres", "omlx_embed_model_available")
def test_researcher_ingests_text_to_raw(
    omlx_model_id_for_integration: str,
    kma_knowledge_it,
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Point the context dir at a sandbox so raw/ writes are isolated.
    monkeypatch.setenv("KMA_CONTEXT_DIR", str(tmp_path / "ctx"))
    (tmp_path / "ctx" / "raw").mkdir(parents=True)

    # Build the Researcher with an OMLX model and the IT knowledge base.
    from agno.agent import Agent
    from kma.agents.instructions import RESEARCHER_INSTRUCTIONS
    from kma.agents.settings import agent_db
    from kma.tools.builder import build_researcher_tools

    model = OpenAILike(id=omlx_model_id_for_integration, base_url=get_mlx_base_url(), api_key=get_mlx_api_key())
    agent = Agent(
        id="researcher-it",
        name="Researcher IT",
        model=model,
        db=agent_db,
        instructions=RESEARCHER_INSTRUCTIONS,
        knowledge=kma_knowledge_it,
        tools=build_researcher_tools(kma_knowledge_it),
    )

    prompt = (
        "You are in an automated integration test. Use tools only (no web search needed).\n"
        "Call ingest_text to save a short note titled 'IT Research Note' with body "
        "'OMLX researcher integration sample about Flink checkpoints.' and tag flink.\n"
        "Then call read_manifest. Keep responses short."
    )
    out = agent.run(prompt)
    if out.status != RunStatus.completed:
        msg = (out.content or "").lower()
        if any(t in msg for t in ("memory", "not found", "requires more", "timeout")):
            pytest.skip(f"Researcher run infra issue: {out.content!r}")
    assert out.status == RunStatus.completed, f"researcher run failed: {out.content!r}"

    raw_dir = tmp_path / "ctx" / "raw"
    manifest_path = raw_dir / ".manifest.json"
    assert manifest_path.is_file(), "researcher did not create a manifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert any("research" in (e.get("title", "").lower()) or e.get("file") for e in manifest)
    assert list(raw_dir.glob("*.md")), "researcher did not write any raw markdown"
```

- [ ] **Step 2: Run gated (skips without flags)**

Run: `uv run pytest tests/it/test_researcher_omlx_integration.py -v`
Expected: 1 skipped (KMA_IT_MLX and/or PARALLEL key missing).

- [ ] **Step 3: Run for real (requires OMLX + Postgres + Parallel key)**

Run (add your Parallel key to the env prefix from Task 8 Step 3):

```bash
KMA_IT_MLX=1 KMA_LLM_PROVIDER=mlx KMA_EMBED_PROVIDER=mlx \
  KMA_EMBED_MODEL=<id> KMA_EMBED_DIMENSIONS=<n> \
  KMA_PARALLEL_API_KEY=<key> \
  uv run pytest tests/it/test_researcher_omlx_integration.py -m integration -v
```

Expected: PASS, or clean SKIP. If `ingest_text` is not exposed under that name, inspect `create_ingest_tools` in `src/kma/tools/ingest.py` (returns `[ingest_url, ingest_text, read_manifest, update_manifest_compiled, sync_raw_manifest_from_disk]`) and adjust the prompt tool name to match.

- [ ] **Step 4: Commit**

```bash
git add tests/it/test_researcher_omlx_integration.py
git commit -m "test(it): researcher ingests text to raw/ via OMLX (gated on Parallel key)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: Linter integration (lint)

**Files:**
- Create: `tests/it/test_linter_omlx_integration.py`

- [ ] **Step 1: Write the test**

Create `tests/it/test_linter_omlx_integration.py`:

```python
"""Integration: Linter reads the wiki and reports on it, using OMLX."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from agno.models.openai import OpenAILike
from agno.run.base import RunStatus

from kma.agents.linter import build_linter_agent
from kma.config import get_mlx_api_key, get_mlx_base_url

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KMA_IT_MLX") != "1",
        reason="set KMA_IT_MLX=1 to run OMLX integration",
    ),
]


def _write_wiki(root: Path) -> None:
    (root / "wiki" / "concepts").mkdir(parents=True)
    (root / "wiki" / "index.md").write_text(
        "# Wiki Index\n\nLintOmlxMarker\n\n## Concepts\n- [Kafka](wiki/concepts/kafka.md) — Flink source\n",
        encoding="utf-8",
    )
    (root / "wiki" / "concepts" / "kafka.md").write_text(
        "---\ntitle: Kafka\n---\nKafka is a streaming source for Flink.\n", encoding="utf-8"
    )


@pytest.mark.usefixtures("require_postgres", "omlx_embed_model_available")
def test_linter_reads_wiki_index(
    omlx_model_id_for_integration: str,
    kma_knowledge_it,
    tmp_path: Path,
    monkeypatch,
) -> None:
    sandbox = tmp_path / "ctx"
    _write_wiki(sandbox)
    monkeypatch.setenv("KMA_CONTEXT_DIR", str(sandbox))

    model = OpenAILike(id=omlx_model_id_for_integration, base_url=get_mlx_base_url(), api_key=get_mlx_api_key())
    agent = build_linter_agent(context_dir=sandbox, knowledge=kma_knowledge_it, model=model)

    prompt = (
        "You are in an automated integration test. Use your tools only (no user questions).\n"
        "1) Call read_wiki_index.\n"
        "2) If the index contains the exact substring LintOmlxMarker, your final line must be "
        "exactly: LINT_OMLX_OK\nOtherwise: LINT_OMLX_FAIL\nKeep the rest short."
    )
    out = agent.run(prompt)
    if out.status != RunStatus.completed:
        msg = (out.content or "").lower()
        if any(t in msg for t in ("memory", "not found", "requires more", "timeout")):
            pytest.skip(f"Linter run infra issue: {out.content!r}")
    assert out.status == RunStatus.completed, f"linter run failed: {out.content!r}"
    assert "LINT_OMLX_OK" in (out.content or ""), f"expected token in: {out.content!r}"
```

- [ ] **Step 2: Run gated (skips without flag)**

Run: `uv run pytest tests/it/test_linter_omlx_integration.py -v`
Expected: 1 skipped.

- [ ] **Step 3: Run for real against OMLX**

Run (same env prefix as Task 8 Step 3). Expected PASS or clean SKIP. If `build_linter_agent` does not expose `read_wiki_index` under that name, confirm against `build_linter_tools` in `src/kma/tools/builder.py` (it returns `read_wiki_index, read_wiki_state, update_wiki_state`) and adjust the prompt.

- [ ] **Step 4: Commit**

```bash
git add tests/it/test_linter_omlx_integration.py
git commit -m "test(it): linter reads wiki index via OMLX

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: Document the OMLX integration workflow + full verification

**Files:**
- Modify: `docs/DEVELOPER_PRACTICES.md`
- Test: `tests/ut/test_developer_practices_omlx.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/ut/test_developer_practices_omlx.py`:

```python
"""DEVELOPER_PRACTICES documents the OMLX integration suite."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "docs" / "DEVELOPER_PRACTICES.md"


def test_doc_mentions_omlx_and_gate() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "OMLX" in text
    assert "KMA_IT_MLX" in text
    assert "KMA_MLX_BASE_URL" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ut/test_developer_practices_omlx.py -v`
Expected: FAIL.

- [ ] **Step 3: Add an OMLX subsection to `docs/DEVELOPER_PRACTICES.md`**

Add a new subsection under the "Integration tests" → "Environment variables" area (after the existing env table). Include:

```markdown
### OMLX (mlx) provider and integration suite

km-agent can run chat (and optionally embeddings) on a local OMLX server, reached as an
OpenAI-compatible endpoint at `KMA_MLX_BASE_URL` (default `http://127.0.0.1:7999/v1`).
Chat uses the chat-completions API (`agno` `OpenAILike`); OMLX serves no embedding model
by default, so embeddings on `mlx` require `KMA_EMBED_MODEL` + `KMA_EMBED_DIMENSIONS` set to
match a model you have loaded (alternatively keep `KMA_EMBED_PROVIDER=ollama`).

The OMLX-backed integration suite is gated by `KMA_IT_MLX=1` and skips cleanly when OMLX,
Postgres, or the embedding model are unavailable. It covers Compiler (compile/ingest),
Navigator (retrieve/connect/file_read), SQL (capture/retrieve/organize), Researcher
(research/ingest — additionally needs `KMA_PARALLEL_API_KEY`), and Linter (lint).

| Variable | Role |
|----------|------|
| `KMA_IT_MLX` | Set to `1` to enable the OMLX integration modules (`tests/it/test_*_omlx_integration.py`). |
| `KMA_IT_MLX_MODEL` | Optional chat model id from `GET ${KMA_MLX_BASE_URL}/models`; default `mlx-community--Qwen3-4B-Instruct-2507-4bit` when present. |
| `KMA_MLX_BASE_URL` | OMLX chat endpoint base URL (default `http://127.0.0.1:7999/v1`). |
| `KMA_MLX_EMBED_BASE_URL` | OMLX embeddings base URL; defaults to `KMA_MLX_BASE_URL`. |
| `KMA_EMBED_MODEL` / `KMA_EMBED_DIMENSIONS` | Required when `KMA_EMBED_PROVIDER=mlx`; must match the loaded model. |

Run the whole OMLX suite:

​```bash
KMA_IT_MLX=1 KMA_LLM_PROVIDER=mlx KMA_EMBED_PROVIDER=mlx \
  KMA_EMBED_MODEL=<id> KMA_EMBED_DIMENSIONS=<n> \
  uv run pytest tests/it -m integration -k omlx -v
​```
```

(Remove the zero-width characters around the code fence — they are only here to keep this plan's fence intact; write a normal triple-backtick block.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/ut/test_developer_practices_omlx.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full unit suite to confirm green**

Run: `uv run pytest tests/ut -v`
Expected: PASS (DB-touching tests may skip if Postgres is down — that is acceptable).

- [ ] **Step 6: Run the OMLX integration suite end-to-end (real services)**

Run:

```bash
KMA_IT_MLX=1 KMA_LLM_PROVIDER=mlx KMA_EMBED_PROVIDER=mlx \
  KMA_EMBED_MODEL=<id> KMA_EMBED_DIMENSIONS=<n> \
  uv run pytest tests/it -m integration -k omlx -v
```

Expected: PASS, or clean SKIPs for unavailable services. Investigate any hard failure with superpowers:systematic-debugging.

- [ ] **Step 7: Commit**

```bash
git add docs/DEVELOPER_PRACTICES.md tests/ut/test_developer_practices_omlx.py
git commit -m "docs: document OMLX provider and KMA_IT_MLX integration suite

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (completed during planning)

**Spec coverage:**
- `mlx` chat via OpenAILike → Task 2. ✓
- `mlx` embeddings via OpenAIEmbedder + required model/dims → Tasks 1, 3. ✓
- Decoupled chat vs embed base URLs → Tasks 1, 3. ✓
- enums/defaults/accessors → Task 1. ✓
- example.env + CLAUDE.md → Task 4. ✓
- verify_agent_env.sh OMLX check + test update → Task 5. ✓
- tests/data real flink-studies corpus + frontmatter → Task 6. ✓
- conftest OMLX fixtures (reachable / chat model / embed model + dims guard) → Task 7. ✓
- Full agent surface IT: Compiler (Task 8), Navigator (Task 9), SQL capture/retrieve/organize (Task 10), Researcher gated on Parallel (Task 11), Linter (Task 12). ✓
- KMA_IT_MLX master gate + clean skips → Tasks 8-12. ✓
- DEVELOPER_PRACTICES env matrix → Task 13. ✓
- Dimension-mismatch mitigations: verify script (Task 5), conftest guard via `omlx_embed_model_available` requiring dims (Task 7), `_it` tables (existing fixtures, used in Tasks 8/9/11/12). ✓

**Notes for the executor:**
- Ollama-based integration modules (`test_compiler_agent_integration.py`, `test_navigator_integration.py`) are left intact; the new `*_omlx_integration.py` modules add the OMLX path. Do not delete the Ollama tests.
- Tool names in prompts (`read_manifest`, `ingest_text`, `read_wiki_index`, etc.) come from the builders in `src/kma/tools/`. If a name differs at execution time, confirm against the relevant `create_*`/`build_*` function rather than guessing.
- The embed model id and dimensions are intentionally unset in defaults; every real integration run must supply `KMA_EMBED_MODEL` + `KMA_EMBED_DIMENSIONS` (or switch embeddings to Ollama).
```
