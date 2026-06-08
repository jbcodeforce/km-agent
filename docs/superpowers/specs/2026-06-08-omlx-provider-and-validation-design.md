# OMLX Provider + Full-Surface Validation — Design

**Date:** 2026-06-08
**Status:** Approved (pending spec review)

## Goal

Make km-agent fully working and validated, with local inference moving from Ollama to **OMLX** (an OpenAI-compatible MLX server on Apple Silicon, default `http://127.0.0.1:7999/v1`). Ollama remains a supported alternative ("on the side"). Validation means **integration tests across the full agent surface** (Navigator, Compiler, Researcher, Linter — all SPEC intents) driven by **real flink-studies markdown** in `tests/data/`.

## Context & Findings

- **Agno has no native MLX chat model.** OMLX is reached as an OpenAI-compatible endpoint. The right Agno class is `OpenAILike` (chat-completions API), **not** `OpenAIResponses` — OMLX serves `/v1/chat/completions`, confirmed working (Qwen3-4B returns a completion in ~3.4s warm).
- **OMLX is chat-only today.** `/v1/models` lists 7 chat/vision models (Codestral-22B, GLM-4.6V-Flash, Qwen3.6-27B, Qwen3.6-35B-A3B, gpt-oss-20b, Qwen3-4B-Instruct, Qwen3-8B). `/v1/embeddings` returns "Model not found". The user will **load an embedding model into OMLX** so embeddings are also served from `:7999`.
- Existing provider pattern: `kma/config.py` exposes `CompilerLlmProvider` / `EmbedProvider` literals; `kma/llm_factory.py` builds chat models; `kma/db.py::build_default_embedder` builds embedders. Chat and embed currently share one `OPENAI_BASE_URL` — must be decoupled.
- flink-studies is cloned locally at `/Users/jerome/Documents/Code/flink-studies` (44 markdown docs under `docs/`).

## Decision

**Approach 1 — explicit `mlx` provider** for both chat and embeddings, reusing Agno's OpenAI-compatible classes under the hood with a dedicated `KMA_MLX_BASE_URL`. Chosen over reusing the `openai` provider (conflates cloud OpenAI with local OMLX) and over a generic `openai_compatible` provider (YAGNI). Leaves the real `openai` cloud path untouched.

## Part A — OMLX as a first-class `mlx` provider

### Config (`src/kma/config.py`)
- Add `"mlx"` to `CompilerLlmProvider` and `EmbedProvider` literals (and update the `get_llm_provider` / `get_embed_provider` validation sets).
- `_DEFAULT_COMPILER_MODEL["mlx"] = "Qwen3.6-35B-A3B-UD-MLX-4bit"` (same family as today's Ollama default).
- New accessors:
  - `get_mlx_base_url()` → `KMA_MLX_BASE_URL`, default `http://127.0.0.1:7999/v1`.
  - `get_mlx_api_key()` → `KMA_MLX_API_KEY`, default `"not-needed"` (`OpenAILike` requires a non-empty key string).
  - `get_mlx_embed_base_url()` → `KMA_MLX_EMBED_BASE_URL`, falls back to `get_mlx_base_url()` (same OMLX server by default).
  - `get_embed_base_url()` → `KMA_EMBED_BASE_URL` then `OPENAI_BASE_URL` (decouples chat vs embed endpoints).
- For `mlx` embeddings, **require** `KMA_EMBED_MODEL` and `KMA_EMBED_DIMENSIONS` — raise a clear `ValueError` if unset, since OMLX has no default embed model and dimensions cannot be guessed.

### Chat factory (`src/kma/llm_factory.py`)
- Import `OpenAILike` from `agno.models.openai`.
- Add `provider == "mlx"` branch: `return OpenAILike(id=mid, base_url=get_mlx_base_url(), api_key=get_mlx_api_key())`.

### Embedder (`src/kma/db.py`)
- Add `mlx` branch in `build_default_embedder()`: `OpenAIEmbedder(id=get_embed_model_id(), dimensions=get_embed_dimensions(), api_key=get_mlx_api_key(), base_url=get_mlx_embed_base_url())`.
- Change the existing `openai` branch to use `get_embed_base_url()` instead of reading `OPENAI_BASE_URL` directly.

### Wiring & docs
- `example.env`: add an OMLX block documenting `KMA_LLM_PROVIDER=mlx`, `KMA_MLX_BASE_URL`, `KMA_MLX_API_KEY`, `KMA_EMBED_PROVIDER=mlx`, `KMA_EMBED_MODEL`, `KMA_EMBED_DIMENSIONS`, `KMA_MLX_EMBED_BASE_URL`.
- `scripts/verify_agent_env.sh`: when chat or embed provider is `mlx`, `GET ${KMA_MLX_BASE_URL}/models` and assert the configured chat model id and embed model id appear; warn (don't hard-fail) if the embed model is missing. Update `tests/ut/test_verify_agent_env_script.py` accordingly.
- `CLAUDE.md`: add `mlx` to the documented provider list and note OMLX serves chat-completions.
- Ollama remains fully intact as the alternative provider.

## Part B — Full-surface integration validation

### Test data (`tests/data/`)
- Copy ~4–6 real flink-studies markdown files spanning `sql` / `architecture` / `cookbook` domains. Keep them small for speed.
- Apply raw YAML frontmatter via the existing `scripts/add_raw_frontmatter.py` so they are valid raw sources.

### Fixtures (`tests/it/conftest.py`)
- OMLX fixtures paralleling the Ollama ones: `omlx_reachable` (GET `/models`), `omlx_chat_model_available`, `omlx_embed_model_available`.
- Chat model selection: `KMA_IT_MLX_MODEL` → default small `mlx-community--Qwen3-4B-Instruct-2507-4bit`.
- Sandbox `context_dir`; dedicated `*_it` vector tables; reuse existing Postgres reachability.
- Guard that asserts configured `KMA_EMBED_DIMENSIONS` matches the loaded embed model before tests run.
- All fixtures **skip cleanly** when OMLX / Postgres / the embed model are unavailable.

### Integration tests — one focused module per agent, mapped to SPEC intents
- **Compiler** (`compile`/`ingest`): tests/data raw → wiki `concepts/`/`summaries/`/`index.md` + manifest `compiled: true`. Extends `test_compiler_agent_integration.py`.
- **Navigator** (`retrieve`/`connect`/`file_read`/`meta`): query wiki index, pull a specific article, multi-source synthesis, read a file. Extends `test_navigator_integration.py`.
- **SQL** (`capture`/`retrieve`/`organize`): insert rows into the `kma` schema, query them back, propose a restructure.
- **Researcher** (`research`/`ingest`): gated additionally on `PARALLEL_API_KEY` (skips without it) → search → save to `raw/` → manifest updated.
- **Linter** (`lint`): read wiki → produce lint report / gap list.

### Gating
- `KMA_IT_MLX=1` master gate for OMLX-backed integration tests (parallels `KMA_IT_COMPILER`).
- Researcher tests additionally require `PARALLEL_API_KEY`.
- Plain `uv run pytest tests` stays light: these tests skip when gates/services are absent.
- Update DEVELOPER_PRACTICES.md integration section and the env-var matrix for OMLX and the new gates.

### Unit tests
- Env-driven unit tests (no network) for the new config accessors and the `mlx` chat/embedder branches, matching existing `test_llm_factory.py` / `test_embedder_factory.py`.

## Error Handling — embedding dimension mismatch (primary risk)
Mitigated three ways: (1) `verify_agent_env.sh` checks the embed model exists in OMLX; (2) a conftest guard asserts `KMA_EMBED_DIMENSIONS` matches the loaded model before integration tests run, with a clear error if `KMA_EMBED_DIMENSIONS` is unset for `mlx`; (3) integration tests use dedicated `_it` vector tables, droppable independently of dev data when dimensions change.

## Out of Scope
- Auto-launching OMLX from `scripts/starter.sh` (OMLX is user-managed; starter only checks reachability).
- Migrating away from Ollama (kept as an alternative).
- Loading the embedding model into OMLX (user-operated; design is env-driven and does not hardcode the embed model id or dimensions).

## Open Item (non-blocking)
When the embedding model is loaded into OMLX, capture its **model id** and **vector dimensions** to fill the `example.env` examples and the verify check defaults.
