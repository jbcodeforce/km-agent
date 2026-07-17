# User guide

This document is for user leveraging `km-agent` for day to day knowledge management activities: what to install, how to bring the stack up, and how to run the different **use cases**. 

Technical deep dives (Postgres volumes, integration tests, frontend proxy details) live in [`DEVELOPER_PRACTICES.md`](./DEVELOPER_PRACTICES.md). Product and architecture background are in [`SPEC.md`](./SPEC.md).

## Components View

The following figure illustrates the components involved in the solution:

![](./images/agents_solution.drawio.png)

* User interacts with CLIs and chat interface to the backend system, file system and external systems.
* Knowledge can come from existing notes in markdown format, but will be created and compiled in wiki folder, with concept, indexing and ontology.
* Solution interacts with local or Frontier LLMs via agents
* User preferences, embeddings and learning collection are saved to database

## Use Cases

In this section we present the high level use cases and workflow a user can follow:

### Work on a white page to build knowledge

Once the km-agent repository is cloned, use can add content from the web or create raw markdown file under the context/raw folder and perform deep research to enhance the knowledge content and build a body of knowledge on a given domain.

1. clone the repository to km-agent
1. Create a folder at the same level as km-agent folder for managing your domain specific knowledge. As a supporting example we will use environment engineering studies.
  ```sh
  mkdir env-eng-studies
  cd env-eng-studies
  mkdir docs
  ```
1. Use the setup studies to add agentic support to help you develop your deep research and knownledge
  ```sh
  cd kma-agent
  # create with default
  ./scripts/setup_studies.sh ~/Documents/Code/env-eng-studies 
  # same as 
  /scripts/setup_studies.sh ~/Documents/Code/env-eng-studies --kma-home $PWD --label env-eng-studies
  ```

1. Use one of the starter shell to run the km-agent solution:
  ```sh
  # under xxxx-studies/assistants/km-agent
  ./starter_mac.sh --dev --frontend
  ```


### Work from existing content

User has already a set of notes, in the form of markdown files to manage his own knowledge. The tool will help to build semantic search and knowledge graph as wiki, and add more content via deep research.


## Getting started

### What you need

- Docker engine or Mac contrainer (Tahoe version)
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
| Context on disk | `KMA_CONTEXT_DIR` | Default `./context` — it will contaign `raw/`, `wiki/`, and other files agents read and write. You can have different contexts |
| Database | `KMA_DB_HOST`, `KMA_DB_PORT`, `KMA_DB_USER`, `KMA_DB_PASS`, `KMA_DB_DATABASE` | On the **host**, use `localhost`). See [DEVELOPER_PRACTICES — Postgres](DEVELOPER_PRACTICES.md#postgres-data). |
| Chat model | `KMA_LLM_PROVIDER`, `KMA_MODEL_ID` (or provider-specific keys) | Pull the LLM model you reference before first chat. |
| Embeddings | `KMA_EMBED_PROVIDER`, `KMA_EMBED_MODEL`, `KMA_EMBED_DIMENSIONS` | Vector size must match the model; do not change dimensions on an existing DB without a plan (see developer practices). |

Optional:

- **`PARALLEL_API_KEY`** — enables the **Researcher** agent for web search and richer ingest (see use case *Ingest new material from the web*).
- **`EXA_API_KEY`** — higher limits for Exa-backed search where configured (see `example.env` comments).

Adjust the model names to match `KMA_MODEL_ID` and `KMA_EMBED_MODEL` in `.env`.

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

On macOS with Apple's native `container` CLI (no Docker Compose), use `./scripts/starter-mac.sh --dev --frontend` instead — see [`DEVELOPER_PRACTICES.md`](./DEVELOPER_PRACTICES.md#).

After the stack is up, re-run `./scripts/verify_config.sh --frontend` to confirm Postgres, AgentOS, LLM models, and the chat UI are reachable.

---

## Attach a studies repository (hosted layout)

Use this when km-agent should run **from inside a studies repo** (for example [flink-studies](https://github.com/jbcodeforce/flink-studies)) while keeping `context/` and configuration in that repo. AgentOS and the chat UI still run from your km-agent clone; the studies repo holds context, `.env`, and wrapper scripts under `assistants/km-agent/`.

### Bootstrap (once)

From the **km-agent** repository:

```bash
./scripts/setup_studies.sh /path/to/ML-studies
```

This creates `assistants/km-agent/` with `context/`, `example.env`, `.env`, `.kma-home`, and wrapper scripts. Edit `assistants/km-agent/.env` for LLM keys and ports. The setup uses a dedicated Postgres container name and port (`5433` by default) so it does not clash with a km-agent repo running on `5432`.

### Start from the studies repo

```bash
cd /path/to/ML-studies
./assistants/km-agent/starter-mac.sh --dev --frontend
./assistants/km-agent/verify_config.sh --frontend
```

### Compile studies docs into the wiki

```bash
./assistants/km-agent/compile-docs.sh
./assistants/km-agent/compile-docs.sh --dry-run   # preview only
```

Output lands in `assistants/km-agent/context/wiki/`. The studies `docs/` tree and `docs/.manifest.json` stay in place; the Compiler reads them via the `studies` raw root label.

See also `assistants/km-agent/README.md` in the studies repo after setup.

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
mkdir  /path/to/docs --source flink-studies
```


### UC-2 — Attach a studies repository and compile and lint documentation into the wiki

**Goal:** From an existing Markdown tree (for example a `docs/` folder of the [flink-studies](https://github.com/jbcodeforce/flink-studies)), update a tracking manifest entries, and run the **Compiler** and **linter** agents so **`context/wiki/`** gains summaries, concept pages, and an updated **`index.md`**.

#### Preconditions

- Postgres running; LLM and embedder configured (`KMA_LLM_PROVIDER`, `KMA_EMBED_*`).
- OMLX server (or cloud) models pulled for chat.
- Embedding model will be pulled on the first calls
- Input files have frontmatter information

**Studies-hosted layout:** If you used [`setup_studies.sh`](https://github.com/jbcodeforce/km-agent/tree/main/scripts/setup_studies.sh), start the stack with `./assistants/km-agent/starter-mac.sh --dev --frontend` and compile with `./assistants/km-agent/compile-docs.sh` from the studies repo root. Context is under `assistants/km-agent/context/`.

#### Steps (outline)

**Option A — from km-agent repo:**

1. From the km-agent repo folder, run the crawler and knowledge Compiler agent:

   ```bash
   uv run python scripts/compile_docs_folder.py /path/to/docs \
     --context ./context  --label studies
   ```

   Use `--dry-run` or `--skip-compiler` to only prepare manifests and front matter without invoking the agent.

**Option B — studies-hosted layout:**

1. From the studies repo:

   ```bash
   ./assistants/km-agent/compile-docs.sh
   ```

2. Inspect `assistants/km-agent/context/wiki/index.md` and `assistants/km-agent/context/wiki/concepts/` after a successful run.

**Success:** Uncompiled sources in the manifest move to **compiled**, and the wiki index reflects new or updated articles.

### UC-2b — Catalog studies code into the wiki (intent summaries)

**Goal:** From a studies repo **`code/`** (or **`src/`**) tree—for example [flink-studies](https://github.com/jbcodeforce/flink-studies) `code/`—write one wiki concept page per top-level category (`flink-sql`, `dbt`, …) with short **LLM intent** blurbs and `code:` path references so chat search can find demos.

#### Preconditions

- LLM configured (`KMA_LLM_PROVIDER`, …). Use `--no-llm` for README-only blurbs without a model.
- `--studies-root` or `KMA_STUDIES_ROOT` pointing at the studies clone.

#### Steps

```bash
uv run python scripts/index_studies_code.py \
  --studies-root /path/to/flink-studies \
  --context ./context

# Embed the new wiki pages for semantic chat retrieval
uv run python scripts/index_wiki.py --context ./context
```

Use `--dry-run` to list categories/labs without writes; `--force` to re-summarize when packs changed little; `--limit N` for a smoke run.

**Success:** `context/wiki/concepts/code-*.md` exist, `wiki/index.md` has a **Code catalogs** section, and after `index_wiki.py` Navigator/`search_wiki` can retrieve lab intent.

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
4. **Keep an answer:** use **Copy** on a completed reply to put the markdown on the clipboard, or type `/save my-notes.md` to write the latest assistant reply under `context/raw/` (YAML frontmatter + manifest; overwrites the same filename if it already exists).

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
