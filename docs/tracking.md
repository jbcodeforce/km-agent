# km-agent — tracking

Tracking document for tests, documentation, and `src/kma/` API surface. Use this when returning to the project after a break.

## Testing policy

| Layer | Scope | Assumptions |
|-------|-------|-------------|
| **Unit (`tests/ut/`)** | Pure logic: config resolution, ingest/manifest, compiler FS paths, factory wiring (no `agent.run`) | No LLM, no Postgres required for collection |
| **Integration (`tests/it/`)** | Agent runs, DB, embeddings, tool side effects | **OMLX server running** (`KMA_LLM_PROVIDER=mlx`); Postgres via `docker compose up -d agent-db` |
| **To rework (`tests/to_rework/`)** | Older Ollama/OMLX IT drafts; need import fixes (`get_mlx_*` renamed to `get_llm_*` in `config.py`) before moving back to `tests/it/` |

**Do not add unit tests that call an LLM.** Any behavior that needs a model goes in integration tests with `KMA_IT_MLX=1` (or legacy `KMA_IT_COMPILER=1` for LLM-based compiler IT).

**Skip unnecessary unit tests** for: Agno `Agent`/`Team` construction beyond model-type wiring, `@tool` closures (cover via the public helper they delegate to), and import-time singletons in `agents/settings.py`.

---

## Documentation index

| Document | Purpose |
|----------|---------|
| [SPEC.md](SPEC.md) | Product/system spec: agents, pipeline, knowledge model, intent routing |
| [DEVELOPER_PRACTICES.md](DEVELOPER_PRACTICES.md) | Setup, Compose, frontend, integration-test env matrix |
| [USER_GUIDE.md](USER_GUIDE.md) | End-user flows and env vars |
| [example.env](https://github.com/jbcodeforce/km-agent/blob/main/example.env) | Canonical env template (mlx + OMLX defaults) |
| [superpowers/specs/2026-06-08-omlx-provider-and-validation-design.md](superpowers/specs/2026-06-08-omlx-provider-and-validation-design.md) | OMLX provider design (some names since unified under `get_llm_*`) |
| [superpowers/plans/2026-06-08-omlx-provider-and-validation.md](superpowers/plans/2026-06-08-omlx-provider-and-validation.md) | Implementation plan for OMLX IT suite |

---

## Test inventory

### Unit tests (`tests/ut/`)

| File | What it covers | Notes |
|------|----------------|-------|
| `test_config.py` | `Env`, `get_*` config accessors, behavior toggles | Loads `example.env` |
| `test_llm_model_factory.py` | `build_default_llm_model`, mlx embedder branch | Provider branches via `monkeypatch`; no network |
| `test_embedder_factory.py` | `build_default_embedder` for ollama/openai/mlx | Validates mlx requires model/dims |
| `test_ingest.py` | Ingest helpers + manifest sync + tool wrappers | Core filesystem logic |
| `test_compiler_manifest.py` | Multi-root raw, labelled paths, compiler FS + builder | Good coverage of compiler tooling |
| `test_wiki_tools.py` | `get_or_create_wiki_paths`, `create_wiki_tools` count | Does not exercise individual wiki `@tool` bodies |
| `test_agent_factories.py` | `build_compiler_agent` model wiring | **Broken at collect**: imports `compiler` module → Postgres at import time; assertions still expect `OllamaResponses` while `example.env` uses `mlx` |
| `test_linter_agent.py` | `build_linter_tools`, `build_linter_agent` | **Broken at collect**: same Postgres import issue; wrong import `build_default_embedder` from `kma.db` |
| `test_setup_script.py` | `scripts/setup.sh`, `starter.sh`, `compose.yaml` | Infra smoke |
| `test_verify_agent_env_script.py` | `scripts/verify-agent-env.sh` | Infra smoke |
| `test_add_raw_frontmatter_script.py` | `scripts/add_raw_frontmatter.py` | Script behavior |
| `test_tests_data_corpus.py` | `tests/data/raw/*.md` frontmatter | Fixture hygiene |

### Integration tests (`tests/it/`)

| File | Gate | What it covers |
|------|------|----------------|
| `test_db_public_schema.py` | Postgres reachable | `build_db_url`, `get_postgres_db`, `create_knowledge`, `kma` schema |
| `test_compiler_agent_integration.py` | `KMA_IT_COMPILER=1` | Compiler agent run (Ollama chat model injected) |
| `test_compiler_omlx_integration.py` | `KMA_IT_MLX=1` | Compiler compiles `tests/data/raw/kafka.md` via OMLX |

Shared fixtures: `tests/it/conftest.py` (`require_postgres`, `omlx_*`, `ollama_*`, `kma_knowledge_it`).

### To rework (`tests/to_rework/`)

| File | Intended coverage | Blocker |
|------|-------------------|---------|
| `test_navigator_omlx_integration.py` | Navigator reads wiki + manifest | Imports `get_mlx_base_url` / `get_mlx_api_key` (use `get_llm_*`) |
| `test_linter_omlx_integration.py` | Linter reads wiki index | Same import rename |
| `test_researcher_omlx_integration.py` | Researcher ingest to `raw/` | Same + `PARALLEL_API_KEY` not exported from `config.py` yet |
| `test_sql_omlx_integration.py` | SQL capture in `kma` schema | Import / gate review |
| `test_navigator_integration.py` | Navigator wiki read (Ollama) | Legacy Ollama path |
| `test_ollama_integration.py` | Minimal Agno + Ollama chat | Legacy |
| `test_linter_omlx_integration.py` | Linter IT | See above |

### Run commands

```bash
# Unit only (no Postgres needed if collection fixed)
uv run pytest tests/ut -v

# DB integration (Postgres up)
uv run pytest tests/it/test_db_public_schema.py -v

# OMLX compiler IT (OMLX + Postgres + mlx embeddings configured)
KMA_IT_MLX=1 uv run pytest tests/it/test_compiler_omlx_integration.py -m integration -v

# Legacy Ollama compiler IT
KMA_IT_COMPILER=1 uv run pytest tests/it/test_compiler_agent_integration.py -m integration -v
```

---

## Known test debt (fix when resuming)

1. **Import-time Postgres**: `kma.agents.compiler` (and siblings) build module-level agents via `agents/settings.py` → `get_postgres_db()`. Unit tests that import those modules fail without Postgres. Fix: lazy agent construction or mock DB in UT imports.
2. **`test_agent_factories.py`**: Update assertions for `mlx` / `OpenAILike` per `example.env`.
3. **`tests/to_rework/*`**: Rename `get_mlx_*` → `get_llm_*`; add `PARALLEL_API_KEY` helper to `config.py` if Researcher IT is revived.
4. **`test_linter_agent.py`**: Fix embedder import (`kma.llm_factory.build_default_embedder`).

---

## `src/kma/` API and test coverage

Legend: **UT** = covered by unit tests, **IT** = integration only, **—** = intentionally untested (thin wrapper / LLM / Agno delegate), **gap** = optional UT if logic grows.

### `config.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `Env` | class (constants) | UT | — | Keys matched to `example.env` |
| `kma_agent_reasoning_enabled` | function | UT | — | |
| `kma_stream_events_enabled` | function | UT | — | |
| `kma_show_team_member_responses_enabled` | function | UT | — | |
| `get_kma_context_dir` | function | UT | — | |
| `get_llm_provider` | function | UT | — | |
| `get_llm_model_id` | function | UT | IT | IT uses via conftest |
| `get_embed_provider` | function | UT | IT | |
| `get_embed_model_id` | function | UT | IT | |
| `get_embed_dimensions` | function | UT | IT | |
| `get_llm_base_url` | function | UT | IT | |
| `get_llm_api_key` | function | UT | IT | |
| `get_embed_base_url` | function | UT | — | |
| `get_embed_host` | function | UT | — | |
| `_env_truthy` | function | — | — | Private; covered indirectly |
| `_env_first_nonempty` | function | — | — | Private |
| `_llm_host_port_base_url` | function | — | — | Private |

### `db.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `build_db_url` | function | — | IT | `test_db_public_schema` |
| `get_postgres_db` | function | — | IT | |
| `create_knowledge` | function | — | IT | Needs embedder (mlx server for mlx provider) |
| `get_sql_engine` | function | — | gap | Creates `kma` schema; no dedicated UT |
| `db_url`, `DB_ID`, `KMA_SCHEMA` | module constants | — | IT | |

### `llm_factory.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `build_default_llm_model` | function | UT | IT | IT injects `OpenAILike` / `OllamaResponses` explicitly |
| `build_default_embedder` | function | UT | IT | mlx branch needs OMLX for real embed calls |

### `agents/settings.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `agent_db` | singleton | — | IT | Import-time Postgres |
| `kma_knowledge` | singleton | — | IT | |
| `kma_learnings` | singleton | — | IT | |

### `agents/compiler.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `COMPILER_INSTRUCTIONS` | constant | — | — | Prompt text |
| `build_compiler_agent` | function | UT (stale) | IT | Wiring only in UT; full run in IT |
| `compiler` | singleton `Agent` | — | — | Avoid UT import until DB lazy |

### `agents/navigator.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `build_navigator_instructions` | function | — | — | String concat; no UT needed |
| `build_navigator_agent` | function | — | to_rework | LLM run → IT only |
| `navigator` | singleton `Agent` | — | — | |

### `agents/linter.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `LINTER_INSTRUCTIONS` | constant | — | — | |
| `build_linter_agent` | function | UT (weak) | to_rework | UT only asserts truthy |
| `linter` | singleton `Agent` | — | — | |

### `agents/researcher.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `RESEARCHER_INSTRUCTIONS` | constant | — | — | |
| `researcher` | `Agent \| None` | — | to_rework | Gated on Parallel API key; LLM → IT |

### `agents/team.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `members` | list | — | — | Filtered `None` researcher |
| `kma_team` | `Team` | — | gap | Coordinate mode; IT via chat only |

### `agents/instructions.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `BASE_INSTRUCTIONS` | constant | — | — | |
| `EXA_INSTRUCTIONS` | constant | — | — | |
| `WIKI_INSTRUCTIONS` | constant | — | — | |

### `agents/scraper.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| (prototype) | — | — | — | Empty stub; no tests |

### `tools/builder.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `_get_paths` | function | — | — | Private |
| `build_compiler_tools` | function | UT | IT | Partial via `test_compiler_manifest` |
| `build_navigator_tools` | function | — | to_rework | SQL + files; IT |
| `build_researcher_tools` | function | — | to_rework | Parallel + ingest; IT |
| `build_linter_tools` | function | UT | to_rework | Count-only UT |

### `tools/ingest.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `_slugify` | function | UT | — | test ok |
| `_read_manifest` | function | UT | — | test ok |
| `_write_manifest` | function | UT | — | test ok |
| `_parse_frontmatter_lines` | function | — | — | Covered via `sync_manifest_from_raw_markdown` |
| `_normalize_ingested_iso` | function | — | — | Indirect via sync test |
| `_compiled_bool` | function | — | — | Indirect |
| `sync_manifest_from_raw_markdown` | function | UT | IT | test ok  |
| `_build_frontmatter` | function | UT | — | test ok  |
| `_do_ingest_url` | function | UT | — | Stub path without Parallel |
| `_do_ingest_text` | function | UT | — | test ok |
| `create_ingest_tools` | function | UT | — | Returns 5 `@tool` wrappers - test ok |
| `_compiler_uses_labelled_manifest_ids` | function | — | — | Private - test ok |
| `create_compiler_manifest_tools` | function | UT | — | Merged manifest read/update |

Ingest `@tool` closures (`ingest_url`, `ingest_text`, `read_manifest`, `update_manifest_compiled`, `sync_raw_manifest_from_disk`): **—** (delegate to tested helpers).

### `tools/compiler_fs.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `use_labelled_raw_paths` | function | UT | — | |
| `_is_under` | function | — | — | Private |
| `_excluded` | function | — | — | Private |
| `create_compiler_file_tools` | function | UT | IT | `read_file`, `save_file`, `list_files`, `search_files` |

### `tools/wiki.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `get_or_create_wiki_paths` | function | UT | — | |
| `create_wiki_tools` | function | UT | — | Returns 4 tools |
| `read_wiki_index` | `@tool` | — | — | Thin file read |
| `update_wiki_index` | `@tool` | — | — | Thin file write |
| `read_wiki_state` | `@tool` | — | — | JSON read |
| `update_wiki_state` | `@tool` | gap | — | Optional UT if state logic grows |

### `tools/knowledge.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `create_update_knowledge` | function | — | IT | Wraps `knowledge.insert`; IT via agent runs |

### `models/cursor_agent.py`

| Symbol | Kind | UT | IT | Notes |
|--------|------|----|----|-------|
| `_message_text` | function | — | — | Private |
| `format_messages_for_cursor` | function | gap | — | Pure; UT only if cursor provider is used |
| `build_cursor_agent_options` | function | gap | — | |
| `CursorAgentModel` | class | — | gap | Agno `Model` adapter; IT if `KMA_LLM_PROVIDER=cursor` |

#### `CursorAgentModel` methods

| Method | UT | IT | Notes |
|--------|----|----|-------|
| `_resolve_api_key` | — | — | |
| `_get_agent` | — | IT | Needs Cursor SDK |
| `close` | — | — | |
| `_prompt_delta` | — | — | |
| `_run_cursor_prompt` | — | IT | |
| `_result_to_model_response` | — | — | |
| `invoke` | — | IT | |
| `ainvoke` | — | IT | Delegates to `invoke` |
| `invoke_stream` | — | IT | |
| `ainvoke_stream` | — | IT | |
| `_parse_provider_response` | — | — | |
| `_parse_provider_response_delta` | — | — | |

---

## Integration test matrix (LLM / external services)

Assume **OMLX** is the default LLM path (`example.env`). Postgres required for knowledge-backed runs.

| Scenario | Test location | Gate | External deps |
|----------|---------------|------|---------------|
| DB + schema + knowledge create | `it/test_db_public_schema.py` | Postgres | mlx embedder if `KMA_EMBED_PROVIDER=mlx` |
| Compiler sandbox compile | `it/test_compiler_omlx_integration.py` | `KMA_IT_MLX=1` | OMLX chat + mlx embeddings + Postgres |
| Compiler sandbox (Ollama) | `it/test_compiler_agent_integration.py` | `KMA_IT_COMPILER=1` | Ollama + Postgres |
| Navigator wiki Q&A | `to_rework/test_navigator_omlx_integration.py` | `KMA_IT_MLX=1` | OMLX + Postgres; fix imports first |
| Linter wiki pass | `to_rework/test_linter_omlx_integration.py` | `KMA_IT_MLX=1` | OMLX + Postgres |
| Researcher web ingest | `to_rework/test_researcher_omlx_integration.py` | `KMA_IT_MLX=1` + Parallel key | OMLX + Parallel API + Postgres |
| SQL user tables | `to_rework/test_sql_omlx_integration.py` | TBD | OMLX + Postgres |

**No new unit tests** for: `agent.run()`, team routing, navigator/linter/researcher end-to-end behavior, or embed/ chat API calls.

---

## Suggested next steps when resuming

1. Fix UT collection: lazy-init agents or isolate `build_*_agent` tests from module-level `compiler` / `navigator` imports.
2. Move reworked OMLX IT files from `to_rework/` → `it/` after `get_llm_*` import cleanup.
3. Align `test_agent_factories.py` with mlx defaults (`OpenAILike`, not `OllamaResponses`).
4. Add IT for Navigator + Linter before adding any more UT surface area.
