# Developer practices

This chapter is for developer willing to work on this code base.

## Solution Architecture

![](./images/architecture.drawio.png)

## Code structure

The code of the solution is under src

```
src
├── app
│   ├── config.yaml  -- chat default queries
│   └── main.py      -- Fast API with AgnoOS API
├── frontend          -- see [frontend/README.md](../src/frontend/README.md)
│   ├── index.html
│   ├── src
│   │   ├── App.vue   -- router shell; chat UI in views/ and components/
└── kma               -- backend and agents
    ├── agents
        ├── config.py
        ....
    ├── db.py
    ├── llm_factory.py
    └── tools         -- see [tools/README.md](../src/kma/tools/README.md)
        ...
```

---
To BE REWORKED
---

## Bootstrap CLI (`scripts/verify_config.sh`)

* Verify the configuration with frontend
  ```sh
  ./scripts/verify_config.sh --trace-env
  ```
  ensures environment variables are set, Docker is available, LLM server is reachable.

* See [user's specific CLI tools](./USER_GUIDE.md).

## Start the solution in dev mode 

* Docker based execution
  ```sh
  ./scripts/starter.sh --dev --frontend
  ```

* On macOS with Apple's native [`container` CLI](https://github.com/apple/container) (no Docker Compose), use:
  ```sh
  ./scripts/starter_mac.sh --dev --frontend
  ```

This starts Postgres as `agent-db`, runs AgentOS on the host via `uv`,  a foreground `omlx serve` if OMLX is down.

Go to [http://localhost:5174](http://localhost:5174/) for chat user interface or [http://localhost:8000/docs](http://localhost:8000/docs) for AgentOS API backend.

## Postgres Data

Postgres data is stored under `.container-data/postgres` in the repo (override with `KMA_CONTAINER_POSTGRES_DATA`). The volume is bind-mounted at `/var/lib/postgresql` inside the container (parent path; required for Apple container virtiofs).

To wipe the database and start clean:

```bash
container stop agent-db
container delete agent-db
rm -rf .container-data/postgres
./scripts/starter_mac.sh --dev --frontend
```

If you  use Docker Compose, stop its `agent-db` first to avoid port conflicts on `${KMA_DB_PORT:-5432}`.

### Where data lives

Postgres uses the Compose named volume declared as `km-agent-postgres` in `compose.yaml` (mounted at `/var/lib/postgresql` in the container). Docker registers it under a project-scoped name, usually `<compose_project_name>_km-agent-postgres`. The default project name is the directory name (for example `km-agent`), so the volume often appears as `km-agent_km-agent-postgres`. Confirm with:

```bash
docker volume ls
docker volume inspect "$(docker volume ls -q --filter name=km-agent-postgres)"
```

On disk: With Docker, `Mountpoint` from `docker volume inspect` is a real host path (typically under `/var/lib/docker/volumes/.../_data`). With Docker Desktop (macOS or Windows), that path lives inside Docker’s Linux VM, not next to your project folder; you normally access the data only through Postgres or by running a one-off container that mounts the same volume (for example `docker run --rm -v km-agent_km-agent-postgres:/v alpine ls /v` — adjust the volume name to match `docker volume ls`).

### Keeping data between sessions

Named volumes persist until you remove them explicitly. They are not tied to a running container.

| Action | Postgres data |
|--------|----------------|
| `docker compose stop agent-db` or `docker compose stop` | Kept |
| `docker compose start agent-db` | Reattaches the same volume |
| `docker compose down` | Containers removed; volume still kept |
| `docker compose up -d agent-db` after `down` | Same volume is reused |
| `docker compose down -v` | Volume deleted (fresh empty DB on next `up`) |
| `docker volume rm <volume_name>` | Volume deleted |

### Cleaning

To wipe the database and start clean:

```bash
docker compose down -v
docker compose up -d agent-db
```

---
## Agents

When user interacts with the chat user interface, it goes to `/agents/${agentId}/runs` and run the team agent.

* [Team](https://github.com/jbcodeforce/km-agent/tree/main/src/kma/agents/team.py) 
* [Compiler](https://github.com/jbcodeforce/km-agent/tree/main/src/kma/agents/compiler.py) agent is used to process indexing of raw data. It is used by the docs crawler. It can be integrated in tools via the factory function: `build_compiler_agent()`. As an example it is used to index existing docs folder:

  ![](./images/docs_compiler.drawio.png)

* [Linter](https://github.com/jbcodeforce/km-agent/tree/main/src/kma/agents/linter.py) to keep integrity within the wiki content and propose researches. 



## LLM local server (native on the host)

* The `km-agent` service in `compose.yaml` talks to the host via `LLM_HOST`, defaulting to `http://host.docker.internal:11434` so the container can reach a server bound on the host.
* For oMLX the server is on port 7999

### Bootstrap CLI (`scripts/validate_config.sh`)

From the repo root, `validate_config.sh` downloads `compose.yaml`, ensures environment variables are set, Docker is available, LLM server is reachable.


## Frontend (Vue + Vite)

The chat UI lives under `src/frontend`. It is a Vue 3 single-page app built with Vite, using Vue Router for routing and Vitest (Node environment) for small unit tests. It talks to Agno AgentOS over HTTP: the dev server proxies `/agent-os` to the backend so the browser can use same-origin requests and avoid CORS during local development.

### Directory layout

| Path | Purpose |
|------|---------|
| `index.html` | HTML shell; loads `/src/main.js`. |
| `vite.config.js` | Vite + Vue plugin, `@` alias, dev server port, `/agent-os` proxy target. |
| `vitest.config.js` | Test runner config (mirrors the `@` → `src` alias). |
| `src/main.js` | App bootstrap: Vue app, router, global styles. |
| `src/App.vue` | Root layout; renders `<router-view />`. |
| `src/router/index.js` | Routes (currently `/` → `ChatView`). |
| `src/views/ChatView.vue` | Main chat page: sidebar, chat panel, optional “back to docs” header. |
| `src/components/` | Reusable UI (`SessionSidebar.vue`, `KmChatPanel.vue`). |
| `src/services/agentOs.js` | AgentOS client: `fetch` to `/agent-os/...`, JSON helpers, SSE streaming for agent runs. |
| `src/utils/` | Shared helpers (for example SSE parsing) and their tests. |
| `src/assets/main.css` | Global styles. |

Imports can use the `@/` alias as a shortcut for `src/` (configured in both Vite and Vitest).

### How the dev proxy works

In the browser, all API calls use the prefix `/agent-os` (see `src/services/agentOs.js`). Vite’s dev server rewrites that to the real AgentOS HTTP API:

- Path: requests to `http://<vite-host>:<port>/agent-os/agents` are proxied to `{target}/agents` (the `/agent-os` prefix is stripped).
- Target: `VITE_AGENT_OS_ORIGIN`, or if unset `AGENT_OS_ORIGIN`, or default `http://127.0.0.1:8000`. This is read in `vite.config.js` via `loadEnv` from env files and the shell environment when you run `npm run dev`.

So the UI never needs a hard-coded backend origin in client code for local dev: align the proxy target with wherever AgentOS listens (see `scripts/starter.sh --dev --frontend`, which exports `VITE_AGENT_OS_ORIGIN` from `AGENT_OS_PORT` by default).

### Environment and `.env`

Create `src/frontend/.env` (or `.env.local`, etc.) from `src/frontend/.env.example`. Vite loads these from the frontend directory (`process.cwd()` when you run `npm run dev` inside `src/frontend`).

| Variable | Where it applies | Notes |
|----------|------------------|--------|
| `VITE_AGENT_OS_ORIGIN` | Vite config (proxy target only) | Backend base URL for the `/agent-os` proxy. Not exposed to client bundle as `import.meta.env`; the app uses relative `/agent-os` URLs. |
| `AGENT_OS_ORIGIN` | Vite config (fallback) | Same role as `VITE_AGENT_OS_ORIGIN` if the `VITE_` form is unset. |
| `VITE_PORT` | Vite dev server | Dev server port; default `5174` if unset. |
| `VITE_STATIC_SITE_URL` | Client (`import.meta.env`) | If set to a non-empty string, `ChatView` shows a top bar link (e.g. MkDocs or static studies site). If unset or empty, the bar is hidden. |
| `VITE_STATIC_SITE_LABEL` | Client | Label for that link; default `Back to studies` if unset or empty. |

Only variables prefixed with `VITE_` are available in application code via `import.meta.env`. The proxy target variables are consumed at build/config time in `vite.config.js`.

### Running the UI locally

From `src/frontend` after `npm ci` (or `npm install`):

```bash
npm run dev
```

From the repository root, `./scripts/starter.sh --dev --frontend` starts AgentOS in the background, sets `VITE_AGENT_OS_ORIGIN` to match `AGENT_OS_PORT` (default `8000`), waits for `GET /agents`, then runs `npm run dev` in `src/frontend`. Use `./scripts/starter.sh --dev` for backend only. On macOS with Apple's native `container` CLI, use `./scripts/starter-mac.sh --dev --frontend` instead. See comments at the top of `scripts/starter.sh` for `KMA_AGENT_OS_HOST`, `KMA_AGENT_OS_PORT`, and `KMA_VITE_PORT`.

Other npm scripts: `npm run build` (production bundle), `npm run preview` (serve the built app), `npm run test` (Vitest).

## Application and KMA architecture

The ASGI app in `src/app/main.py` wires Agno AgentOS to shared Postgres session storage, Knowledge vector stores, a coordinating Team (`kma_team` in `src/kma/agents/team.py`), and a separate Agent entry for the Compiler so it can be invoked directly over HTTP as well as inside the team. Types named Agent, Team, Knowledge, PostgresDb, Model, and LearningMachine come from the Agno library; the diagram treats `navigator`, `compiler`, and `researcher` as the concrete `Agent` instances built in `src/kma/agents/`.

Shared `agent_db`, `kma_knowledge`, and `kma_learnings` are created in `src/kma/agents/settings.py` via `kma.db.get_postgres_db` and `kma.db.create_knowledge`. `build_default_llm_model()` in `src/kma/llm_factory.py` supplies the chat Model for each agent. Tool lists are assembled in `src/kma/tools/builder.py` (`build_compiler_tools`, `build_navigator_tools`, `build_researcher_tools`) and delegate to `kma.tools.compiler_fs`, `kma.tools.ingest`, `kma.tools.wiki`, `kma.tools.knowledge`, and Agno’s `FileTools`, `SQLTools`, `ParallelTools`, etc.

## Unit tests

Install dependencies (once per clone or after dependency changes):

```bash
uv sync
```

Run all tests under `tests/`:

```bash
uv run pytest
```

Run only unit tests under `tests/ut/`:

```bash
uv run pytest tests/ut -v
```

Tests that talk to PostgreSQL (for example `tests/ut/test_db_public_schema.py`) use the same URL as `kma.db`. Run them on the host with `DB_HOST=localhost` (or `127.0.0.1`) — not `agent-db`, which only resolves inside the Compose network. Set `KMA_DB_PORT` default `5432`. Confirm the mapping with `docker compose ps` or `docker port agent-db`. If the server is not reachable, those tests skip instead of failing.

## Integration tests

Integration tests live under `tests/it/`. They call real services (Ollama HTTP API when the compiler or embedder uses Ollama; OpenAI when `KMA_EMBED_PROVIDER=openai` for embeddings). They are marked with `@pytest.mark.integration` (registered in `pyproject.toml` under `[tool.pytest.ini_options]` → `markers`).

### When to run them

Use them to confirm Agno works against your configured compiler LLM (`KMA_LLM_PROVIDER`) and embeddings (`KMA_EMBED_PROVIDER`)—defaults match local Ollama. They are not required for every commit if you do not have those services configured.

### How to run

From the repository root, after `uv sync`:

```bash
uv run pytest tests/it -m integration -v
```

Running `uv run pytest tests` also collects `tests/it/`; those tests may skip (Ollama down, wrong model, insufficient RAM) or pass, depending on your machine.

### OMLX (mlx) provider and integration suite

km-agent can run chat (and optionally embeddings) on a local OMLX server, reached as an
OpenAI-compatible endpoint at `KMA_MLX_BASE_URL` (default `http://127.0.0.1:7999/v1`).
Chat uses the chat-completions API (Agno `OpenAILike`); OMLX serves no embedding model
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

```bash
KMA_IT_MLX=1 KMA_LLM_PROVIDER=mlx KMA_EMBED_PROVIDER=mlx \
  KMA_EMBED_MODEL=<id> KMA_EMBED_DIMENSIONS=<n> \
  uv run pytest tests/it -m integration -k omlx -v
```

### Compiler agent integration test

- **Module:** [`tests/it/test_compiler_agent_integration.py`](https://github.com/jbcodeforce/km-agent/tree/main/tests/it/test_compiler_agent_integration.py) (gated with `KMA_IT_COMPILER=1`).
- **Requires:** reachable Postgres (`kma.db` / `DB_*`); chat still uses a pulled Ollama model in this test (`OllamaResponses` + `ollama_model_id_for_integration`). Embeddings: with `KMA_EMBED_PROVIDER=ollama` (default), the configured `KMA_EMBED_MODEL` must appear in `ollama list` (`ollama_embed_model_available`). With `KMA_EMBED_PROVIDER=openai`, set `OPENAI_API_KEY` (the fixture skips if missing); no Ollama embed check.
- **Behavior:** builds `build_compiler_agent(..., model=OllamaResponses(...))` for chat, runs one `agent.run(...)`, then asserts manifest `compiled: true`, wiki outputs, and `wiki/index.md`.
- **Run:**

```bash
KMA_IT_COMPILER=1 uv run pytest tests/it -m integration -k compiler -v
```

### Multi-root raw and studies docs compile

The Compiler can read multiple raw directories (for example a studies repo `docs/` tree and `context/raw/` from the Researcher) while writing only under `context/wiki/`. Pass labeled roots to `build_compiler_agent(..., raw_roots=[("studies", Path(...)), ("ingested", context_dir / "raw")])` — see `build_compiler_tools` in `src/kma/tools/builder.py`. When more than one root exists (or the only root is not `context/raw`), file paths use `raw/<label>/...` and `read_manifest` includes `file_id` values such as `studies:sql/joins.md`.

To prepare a studies `docs/` folder in place and run the Compiler against that layout plus ingested raw:

```bash
uv run python scripts/compile_docs_folder.py /path/to/flink-studies/docs \
  --context ./context --source flink-studies --label studies
```

Use `--dry-run` or `--skip-compiler` to only refresh manifests and frontmatter. Requires Postgres and the configured compiler / embedding backends (see `example.env`).

### Skip vs failure

- **Skip** if Ollama is not reachable at `LLM_HOST` when an integration check needs it (for example `ollama_tags` or Ollama embeddings). Start the server with `./scripts/starter.sh` or `ollama serve`.
- **Skip** if `KMA_EMBED_PROVIDER=openai` and `OPENAI_API_KEY` is unset (compiler integration embed gate).
- **Skip** if no Ollama models are returned when the test needs a pulled Ollama chat or embed model.
- **Skip** after a run if Ollama returns an error that looks like missing model or insufficient system memory for the chosen id; the skip message suggests setting `KMA_IT_OLLAMA_MODEL` to a smaller pulled model.

Failures indicate an unexpected error from the model run (assertions on `RunStatus.completed` and non-empty content).

### Adding new integration tests

1. Place modules under `tests/it/`.
2. Add `@pytest.mark.integration` to tests that touch external services.
3. Prefer session-scoped fixtures in `tests/it/conftest.py` for expensive checks (for example API reachability) so one skip short-circuits the whole session consistently.
4. Keep tests focused (one concern per test). The compiler integration test runs a full `Agent` with sandbox `context_dir` and dedicated `kma_knowledge_it` tables; enable it only with `KMA_IT_COMPILER=1` (see above).

## Sources of information

* [Agno web site](https://www.agno.com/) with [Agent doc](https://docs.agno.com/tutorials/agent-platform/overview)
* [Agno PAL project](https://github.com/agno-agi/pal)
* [Agno Scout project](https://github.com/agno-agi/scout)
* [My own agent studies](https://jbcodeforce.github.io/ML-studies/genAI/agentic/) and [machine learning](https://jbcodeforce.github.io/ML-studies/) 
* [Exa.ai for search API](https://exa.ai/)
* [parallel.ai](https://parallel.ai/)