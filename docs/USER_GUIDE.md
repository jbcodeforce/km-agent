# User guide

This document is for user leveraging km-agent day to day: what to install, how to bring the stack up, and **use cases** you can follow or extend. Technical deep dives (Postgres volumes, integration tests, frontend proxy details) live in [`DEVELOPER_PRACTICES.md`](./DEVELOPER_PRACTICES.md). Product and architecture background are in [`SPEC.md`](./SPEC.md).

We continue to grow the use cases below—each section has a short outline today and a [next block](#where-to-go-next) so contributors know what to add next.

---

## Getting started

### What you need

- Docker

### 1. Clone the repository and create `.env`

From the repository root:

```bash
cp example.env .env
```

Edit **`.env`** at minimum for:

| Area | Variables (examples) | Notes |
|------|------------------------|--------|
| Context on disk | `KMA_CONTEXT_DIR` | Default `./context` — here live `raw/`, `wiki/`, and other files agents read and write. |
| Database | `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_DATABASE` | On the **host**, use `localhost` and the **published** Postgres port (often same as `POSTGRES_PUBLISH_PORT` in Compose). See [DEVELOPER_PRACTICES — Postgres](DEVELOPER_PRACTICES.md#local-postgresql-docker-compose-only). |
| Chat model | `KMA_LLM_PROVIDER`, `KMA_MODEL_ID` (or provider-specific keys) | Pull the Ollama model you reference before first chat. |
| Embeddings | `KMA_EMBED_PROVIDER`, `KMA_EMBED_MODEL`, `KMA_EMBED_DIMENSIONS` | Vector size must match the model; do not change dimensions on an existing DB without a plan (see developer practices). |

Optional:

- **`PARALLEL_API_KEY`** — enables the **Researcher** agent for web search and richer ingest (see use case *Ingest new material from the web*).
- **`EXA_API_KEY`** — higher limits for Exa-backed search where configured (see `example.env` comments).

### 2. Start 
### 4. Start Ollama (when using local LLM / embeddings)

In a separate terminal, from the repo root:

```bash
./scripts/starter.sh
```

This script brings up **`agent-db`** when Compose is available and starts **Ollama** if nothing is already listening on the configured port. Pull the models you configured (chat + embedding), for example:

```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text:latest
```

Adjust model names to match `KMA_MODEL_ID` and `KMA_EMBED_MODEL` in `.env`.

### 7. After first boot (recommended)

- Ensure **`context/`** exists (or your `KMA_CONTEXT_DIR`) with at least `raw/` and `wiki/` as described in [`SPEC.md` — Context directory](SPEC.md#7-context-directory).
- When you adopt a studies repo or many files, consider running **`context/load_context.py`** (or the documented reload flow in `SPEC.md`) so **`kma_knowledge`** gets bootstrap metadata for routing—without it, some recall paths are sparse.

You are ready to use the **use cases** below.

### Where to go next

| Topic | Document |
|--------|----------|
| Architecture, agents, pipeline, intents | [`SPEC.md`](./SPEC.md) |
| Docker volumes, Ollama, tests, frontend proxy | [`DEVELOPER_PRACTICES.md`](./DEVELOPER_PRACTICES.md) |
| Repo overview and quick links | [`../README.md`](../README.md) |

---

## Use cases (living document)

The following sections are **outlines**. We will keep adding steps, examples, troubleshooting, and screenshots. When you extend a use case, preserve the **Goal / Preconditions / Steps / Success / Next** shape so the guide stays scannable.

---

### UC-1 — Ask questions using the wiki, files, and SQL

**Goal:** Use chat to answer a question by combining the wiki index and articles, files under `context/`, structured data in the **`kma`** schema, and vector-backed knowledge where configured.

**Preconditions:**

- AgentOS and (optionally) the Vue UI are running.
- You have content under `context/wiki/` and/or `context/raw/`, or populated SQL tables, depending on what you want queried.

**Steps (outline):**

1. Open the chat UI (or call AgentOS APIs).
2. Ask a **specific** question that references your domain (e.g. a concept you know exists in the wiki or a table you use).
3. For knowledge-heavy questions, the agent should consult the wiki index first, then drill into articles—see [`SPEC.md` — Context navigation](SPEC.md#2-context-navigation).

**Success:** You get an answer grounded in your materials, with paths or citations you can verify under `context/` or in the DB.

**Next (to expand):**

- Example prompts for a studies-style repo.
- How to interpret session vs agent selection in the UI.
- What to do when the answer is too generic (check wiki index, run compile, bootstrap `kma_knowledge`).

---

### UC-2 — Attach a studies repository and compile documentation into the wiki

**Goal:** Point km-agent at an existing Markdown tree (for example a `docs/` folder in [flink-studies](https://github.com/jbcodeforce/flink-studies)), normalize front matter and manifest entries, and run the **Compiler** so **`context/wiki/`** gains summaries, concept pages, and an updated **`index.md`**.

**Preconditions:**

- Postgres running; LLM and embedder configured (`KMA_LLM_PROVIDER`, `KMA_EMBED_*`).
- Ollama (or cloud) models pulled for both chat and embeddings.

**Steps (outline):**

1. Clone or locate the studies repo on disk.
2. From the km-agent repo root, run the compile helper (adjust paths and labels to your layout):

   ```bash
   uv run python scripts/compile_docs_folder.py /path/to/your-studies/docs \
     --context ./context --source your-studies --label studies
   ```

   Use `--dry-run` or `--skip-compiler` to only prepare manifests and front matter without invoking the agent.

3. Inspect `context/wiki/index.md` and `context/wiki/concepts/` after a successful run.

**Success:** Uncompiled sources in the manifest move to **compiled**, and the wiki index reflects new or updated articles.

**Next (to expand):**

- Full flag reference for `compile_docs_folder.py` (`--force`, tags, `doc_type`).
- Combining **studies** raw root with **ingested** `context/raw/` (multi-root) in one compile.
- Troubleshooting: dimension mismatch, Ollama OOM, empty manifest.

---

### UC-3 — Ingest new material from the web

**Goal:** Gather sources from the web, normalize them as markdown under **`context/raw/`** with proper front matter, and optionally hand them to the **Compiler** so the wiki stays current.

**Preconditions:**

- **`PARALLEL_API_KEY`** set so the **Researcher** agent is enabled (see `example.env` and `src/kma/agents/researcher.py`).
- Same database and LLM setup as other use cases.

**Steps (outline):**

1. Start the stack (`./scripts/dev_agent_os.sh`).
2. In chat, issue a **research / ingest** style request aligned with your team instructions (gather sources on topic X, save to raw with tags, etc.).
3. Run compilation (via team instruction to the Compiler, or **`compile_docs_folder.py`**, or a dedicated compile workflow) so new raw files become wiki content.

**Success:** New files appear under `context/raw/` with YAML front matter and `compiled: false` until processed; wiki updates after compile.

**Next (to expand):**

- Example multi-turn conversation for “research topic Y”.
- Parallel vs stub ingest when the API key is missing.
- How manifests merge for multi-root layouts (`raw/studies/...` vs `raw/ingested/...`).

---

### UC-4 — Incremental compile after editing raw notes

**Goal:** After you add or edit markdown in **`context/raw/`**, refresh only **uncompiled** entries and avoid rewriting the whole wiki.

**Preconditions:**

- Existing manifest (`.manifest.json` under the relevant raw root) understands your files.
- Compiler tools and model access unchanged.

**Steps (outline):**

1. Edit or add a raw document; ensure front matter includes **`compiled: false`** when you want recompilation (see [`SPEC.md` — Knowledge base pipeline](SPEC.md#1-knowledge-base-pipeline)).
2. Ask the team or the Compiler agent to process uncompiled files, or use the batch script if your sources live in an external `docs/` tree (UC-2).

**Success:** Only changed sources drive new or updated wiki pages; `wiki/index.md` and `.state.json` stay consistent.

**Next (to expand):**

- Manifest field reference and `file_id` with labelled roots.
- How to force a full recompile safely (if ever needed).

---

### UC-5 — Run backend only (scripts, CI, or custom clients)

**Goal:** Use AgentOS HTTP APIs without the Vue dev server—for automation, debugging, or a different front end.

**Preconditions:**

- `.env` and `uv sync` as in Getting started.

**Steps (outline):**

1. `SKIP_FRONTEND=1 ./scripts/dev_agent_os.sh` **or** `uv run python -m app.main` with `PYTHONPATH=src` and env loaded.
2. Call documented AgentOS routes (e.g. agents, sessions, runs) from your tool of choice.

**Success:** Same agents and team behavior as with the UI, without Node.

**Next (to expand):**

- Minimal `curl` examples for listing agents and starting a run.
- Notes on streaming responses (SSE) for clients.

---

## Contributing to this guide

When you add or refine a use case:

1. Keep **Goal → Preconditions → Steps → Success → Next** so readers can skim.
2. Link to **`SPEC.md`** or **`DEVELOPER_PRACTICES.md`** instead of duplicating long environment tables.
3. Use real commands and paths where possible; mark placeholders like `/path/to/your-studies/docs` clearly.
