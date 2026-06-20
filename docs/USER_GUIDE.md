# User guide

This document is for user leveraging `km-agent` for day to day knowledge management activities: what to install, how to bring the stack up, and how to run the different **use cases**. 

Technical deep dives (Postgres volumes, integration tests, frontend proxy details) live in [`DEVELOPER_PRACTICES.md`](./DEVELOPER_PRACTICES.md). Product and architecture background are in [`SPEC.md`](./SPEC.md).


## Getting started

### What you need

- Docker
- curl
- git cli

### 1. Clone the repository and create `.env` and setup.

* Clone
  ```sh
  git clone https://github.com/jbcodeforce/km-agent
  cd km-agent
  ```
* Set environment variables: From the repository root:
  ```bash
  cp example.env .env
  ```

Edit **`.env`** at minimum for:

| Area | Variables (examples) | Notes |
|------|------------------------|--------|
| Context on disk | `KMA_CONTEXT_DIR` | Default `./context` — here live `raw/`, `wiki/`, and other files agents read and write. You can have different contexts |
| Database | `KMA_DB_HOST`, `KMA_DB_PORT`, `KMA_DB_USER`, `KMA_DB_PASS`, `KMA_DB_DATABASE` | On the **host**, use `localhost`). See [DEVELOPER_PRACTICES — Postgres](DEVELOPER_PRACTICES.md#local-postgresql-docker-compose-only). |
| Chat model | `KMA_LLM_PROVIDER`, `KMA_MODEL_ID` (or provider-specific keys) | Pull the Ollama model you reference before first chat. |
| Embeddings | `KMA_EMBED_PROVIDER`, `KMA_EMBED_MODEL`, `KMA_EMBED_DIMENSIONS` | Vector size must match the model; do not change dimensions on an existing DB without a plan (see developer practices). |

Optional:

- **`PARALLEL_API_KEY`** — enables the **Researcher** agent for web search and richer ingest (see use case *Ingest new material from the web*).
- **`EXA_API_KEY`** — higher limits for Exa-backed search where configured (see `example.env` comments).

Adjust model names to match `KMA_MODEL_ID` and `KMA_EMBED_MODEL` in `.env`.

* Verify your configuration (before or after starting components):
  ```sh
  ./scripts/verify_config.sh
  ./scripts/verify_config.sh --frontend   # also check the Vite dev server
  ```

### 2- Start the Knowledge Management Agent components

In a separate terminal, from the repo root, start the Postgresql server, the km-agent server:

```bash
./scripts/starter.sh
```

After the stack is up, re-run `./scripts/verify_config.sh --frontend` to confirm Postgres, AgentOS, LLM models, and the chat UI are reachable.

### Where to go next

| Topic | Document |
|--------|----------|
| Different use cases | [Section below](#use-cases-living-document) |
| Architecture, agents, pipeline, intents | [`SPEC.md`](./SPEC.md) |
| Knowledge vs learnings vs wiki, index vs embeddings | [`ARCHITECTURE_WIKI_RAG.md`](./ARCHITECTURE_WIKI_RAG.md) |
| Docker volumes, tests, frontend proxy | [`DEVELOPER_PRACTICES.md`](./DEVELOPER_PRACTICES.md) |
| Repo overview and quick links | [`../README.md`](../README.md) |

---

## Use cases

### UC-1 Add annotation to sources file(s)

*Goal:** The source knowledge may not have the frontmatter manifest in each markdown file, and it is needed for metadata managment of the wiki.

* Files that already have km-agent raw frontmatter get a manifest sync only (no rewrite unless --force).
* When specifying a directory, it crawls **/*.md, skips excluded dirs, writes manifest at the folder root with paths like sub/needs.md.
* Files with non-km YAML frontmatter are skipped unless --force.
* Batch runs print a summary line at the end.

#### Preconditions

* python and uv available.

#### Steps (outline)

```sh
# Audit only — report which files have frontmatter (exit 1 if any are missing)
uv run python scripts/add_raw_frontmatter.py /path/to/docs --check

# Single file (unchanged behavior)
uv run python scripts/add_raw_frontmatter.py path/to/doc.md --source flink-studies
# Crawl a folder — adds frontmatter to files missing it, updates manifest with relative paths
uv run python scripts/add_raw_frontmatter.py /path/to/docs --source flink-studies
```


### UC-2 — Attach a studies repository and compile and lint documentation into the wiki

**Goal:** From an existing Markdown tree (for example a `docs/` folder of the [flink-studies](https://github.com/jbcodeforce/flink-studies)), update a tracking manifest entries, and run the **Compiler** and **linter** agents so **`context/wiki/`** gains summaries, concept pages, and an updated **`index.md`**.

#### Preconditions

- Postgres running; LLM and embedder configured (`KMA_LLM_PROVIDER`, `KMA_EMBED_*`).
- OMLX server (or cloud) models pulled for chat.
- Embedding model will be pulled on the first calls
- Input files have frontmatter information

#### Steps (outline)

1. From the km-agent repo folder, run the crawler and knowledge Compiler agent:

   ```bash
   uv run python scripts/compile_docs_folder.py /path/to/docs \
     --context ./context  --label studies
   ```

   Use `--dry-run` or `--skip-compiler` to only prepare manifests and front matter without invoking the agent.

3. Inspect `context/wiki/index.md` and `context/wiki/concepts/` after a successful run.

**Success:** Uncompiled sources in the manifest move to **compiled**, and the wiki index reflects new or updated articles.

### UC-3 - Build ontology

### UC-4 — Ask questions using the wiki, files, and SQL

**Goal:** Use chat to answer a question by combining the wiki index and articles, files under `context/`, structured data in the **`kma`** schema, and vector-backed knowledge where configured.

#### Preconditions

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

### UC-5 — Ingest new material from the web

**Goal:** Gather sources from the web, normalize them as markdown under **`context/raw/`** with proper front matter, and optionally hand them to the **Compiler** so the wiki stays current.

#### Preconditions

- **`PARALLEL_API_KEY`** set so the **Researcher** agent is enabled (see `example.env` and `src/kma/agents/researcher.py`).
- Same database and LLM setup as other use cases.

**Steps:**

1. Start the stack (`./scripts/starter.sh --dev --frontend`).
2. In chat (via **kma team**), ask for research on a topic — e.g. "Search news on Flink 2.2 and enrich the wiki."
3. The team leader delegates to **Researcher** (ingest to `raw/`), then **Navigator** (answer), then schedules **background compile + lint** automatically.

**Success:** New files under `context/raw/` with YAML front matter; user gets an immediate answer; wiki updates in the background (`wiki/index.md`, concepts, lint report).

**Manual compile** (if auto-compile is off): set `KMA_AUTO_COMPILE_AFTER_RESEARCH=0` or use **`compile_docs_folder.py`** / ask the Compiler agent explicitly.

**Next (to expand):**

- Example multi-turn conversation for “research topic Y”.
- Parallel vs stub ingest when the API key is missing.
- How manifests merge for multi-root layouts (`raw/studies/...` vs `raw/ingested/...`).

---

### UC-6 — Incremental compile after editing raw notes

**Goal:** After you add or edit markdown in **`context/raw/`**, refresh only **uncompiled** entries and avoid rewriting the whole wiki.

#### Preconditions

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

## Contributing to this guide

When you add or refine a use case:

1. Keep **Goal → Preconditions → Steps → Success → Next** so readers can skim.
2. Link to **`SPEC.md`** or **`DEVELOPER_PRACTICES.md`** instead of duplicating long environment tables.
3. Use real commands and paths where possible; mark placeholders like `/path/to/your-studies/docs` clearly.
