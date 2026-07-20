# KM_Agent Specification

`km-agent` is a personal knowledge management agent to work on existing studies plus new content discovered by the user.

It works on an existing studies git repositories like [flink-studies](https://github.com/jbcodeforce/flink-studies) to use as  base knowledge, and web search results.

The approach is to use native query interface, to look at files, slack channel, or web content. When new content from web or slack is added to the knowledge, it goes to raw folder, from which structured wiki is built of.

## Architecture

* agno agent OS to serve the agents and team
* km-agent - to define agents, tools and team
```sh
    ├── Navigator    — routes queries, reads wiki, handles SQL/files
    ├── Researcher   - web search, source gathering and write to context/raw/
    ├── Compiler     — reads raw/, writes wiki articles, maintains index
    ├── Linter       — health checks, finds gaps, suggests research
```
* PostgreSQL 18 to keep agent knowledge,  with pgvector (hybrid vector + keyword search)
* OMLX on the **host**  or remote to serve local LLM
*  **Language**: Python 3.12+, managed with `uv`

![](./images/architecture.drawio.png)


**Database layout**: User-created SQL tables (`kma_notes`, `kma_people`, etc.) live in a separate `kma` PostgreSQL schema, isolated from Agno framework tables in the default schema. The SQL engine bootstraps the schema at startup (`CREATE SCHEMA IF NOT EXISTS kma`) and sets `search_path=kma,public` so agents query user tables by default.


## Core Capabilities

### 1. Knowledge Base Pipeline

There are two types of raw knowledge: the docs folder of a studies repository, like flink-studies, and new raw data discovered by the researcher agent.

```sh
├── docs
├── wiki
│   ├── raw
│   ├── entities
│   ├── concepts
│   index.md
│   SCHEMA.md
```

Raw data flows through a compilation pipeline into a structured wiki:

```sh
Ingest (Researcher)     →  context/raw/     →  .manifest.json tracks state
Compile (Compiler)      →  context/wiki/    →  concepts/, summaries/, index.md
Query (Navigator)       →  index-first and/or search_wiki →  pulls specific articles
File outputs (Navigator)→  wiki/outputs/    →  compounds back into wiki
Lint (Linter)           →  wiki/lint-report →  finds gaps, suggests research
```

- **Raw documents** have YAML frontmatter (title, source, date, tags, type, compiled status)
- **Wiki articles** have frontmatter (title, dates, sources, related concepts, tags)
- **Wiki index** lists all articles with 1-line summaries — fits in one LLM read (~5K tokens at 100 articles)
- **Manifest** tracks compile state per raw file — incremental, never rewrites the whole wiki

When articles come from docs of a studies repository the date of the file, and its content may changed overtime after indexing so `compiler` may modify wiki concepts, index and summaries. 

### 2. Context Navigation

Intent classification determines which sources to check:

| Intent | Sources | Behavior |
|--------|---------|----------|
| `capture` | SQL | Insert, confirm, done |
| `retrieve` | Wiki + SQL + Files + Knowledge | Query, present results |
| `connect` | Wiki + SQL + Files  | Multi-source synthesis |
| `research` | Exa (+ raw/ to save) | Search, summarize, optionally ingest |
| `enrich` / search news | Team: Researcher → Navigator → background compile+lint | See enrichment workflow below |
| `ingest` | raw/ | Save article/URL/text to raw/ |
| `compile` | raw/ → wiki/ | Process uncompiled sources into articles |
| `lint` | wiki/ | Health check, find gaps |
| `file_read` / `file_write` | Files | Read or write context directory |
| `organize` | SQL | Propose restructuring, execute on confirmation |
| `meta` | Knowledge + Learnings | Questions about kma itself |

### 3. Execution Loop

Every interaction follows five steps:

1. **Classify** — Determine intent from the user request.
2. **Recall** — Query SQL tables first (for retrieve/connect), then search knowledge, learnings, wiki index, and files.
3. **Read** — Pull from identified sources. Wiki-first for knowledge questions.
4. **Act** — Execute tool calls.
5. **Learn** — Save discoveries, retrieval strategies, and patterns.

### 4. Context stores: Knowledge, Learnings, Wiki

Three systems serve different roles (see [`architecture.md`](./architecture.md)):

- **`kma_knowledge`** — Metadata index (routing layer). File manifests (`File:`), table schemas (`Schema:`), source capabilities (`Source:`), cross-source discoveries (`Discovery:`), wiki articles (`Wiki:`), raw sources (`Raw:`). Not domain article bodies.
- **`kma_learnings`** — Operational memory. Retrieval strategies (`Retrieval:`), recurring patterns (`Pattern:`), explicit user corrections (`Correction:`). Corrections always take priority. Not domain content.
- **`context/wiki/`** — Compiled domain knowledge (markdown). Optional **`kma_wiki`** pgvector table for semantic chunk search via `search_wiki` after offline `scripts/index_wiki.py`.

**Bootstrap**: `context/load_context.py` populates `kma_knowledge` on first run by scanning the context directory, parsing YAML frontmatter for tags, and inserting `File:` metadata entries. This is the bootstrap step that makes Navigator's recall work — without it, the knowledge routing layer is empty. Supports `--recreate` (clear and reload) and `--dry-run` (preview). Also exposed via `/context/reload` endpoint and scheduled daily.

### 5. Learning System

Navigator uses Agno's `LearningMachine` with `AGENTIC` mode — the agent autonomously decides what to learn from each interaction and saves it to `kma_learnings`. This is the mechanism behind the "learns how you work" promise. Manual learning via `save_learning` tool calls is supplementary.

### 6. Agent Memory Tiers

Not all agents need memory. The team uses a tiered approach:

- **Leader + Navigator**: Full memory — agentic memory, past session search, chat history. These are the agents with user-facing continuity across conversations.
- **Researcher, Compiler, Linter, Syncer**: Datetime context only. No memory, no session search. These are stateless workers that get fresh context per invocation.

This keeps worker agents fast and focused while the user-facing agents maintain conversational continuity.


### 7. Context Directory

```sh
context/
├── about-me.md             # User background, goals
├── preferences.md          # Working style, file conventions
├── templates/              # Document scaffolds
├── raw/                    # Ingested source material
│   ├── .manifest.json      # Ingest/compile state tracking
│   └── *.md                # Raw documents with YAML frontmatter
└── wiki/                   # LLM-compiled knowledge base
    ├── index.md            # Master index with article summaries
    ├── .state.json         # Compile/lint timestamps and counts
    ├── concepts/           # One article per concept
    ├── summaries/          # One summary per raw document
    └── outputs/            # Filed query results and reports
```

### 8. Web Research

- **DuckDuckGo** (Researcher): Free web search via Agno `DuckDuckGoTools` (`web_search`). No API key required. Researcher is always a team member.
- **`ingest_url`**: Fetches page text over HTTP (HTML stripped, length-capped via `KMA_INGEST_MAX_CHARS` / legacy `KMA_PARALLEL_INGEST_MAX_CHARS`). Prefer `ingest_text` for curated summaries when fetch quality is poor.



## Agents

### kma (Team Leader)

Primary chat entry point (`POST /teams/kma/runs`). Routes requests to specialists or responds directly for simple things.

| Request Type | Agent |
|-------------|-------|
| Knowledge queries, SQL, files | Navigator |
| Research, enrich knowledge, search news, ingest topic | Researcher → Navigator → background wiki refresh |
| "Compile the wiki" | Compiler |
| "Lint the wiki", "find gaps" | Linter |
| Greetings, thanks, "what can you do?" | Direct response |

#### Enrichment workflow (research / news / enrich)

When the user asks for new external material, the team leader:

1. Delegates to **Researcher** — web search, ingest to `context/raw/`.
2. Delegates to **Navigator** — synthesize an answer from ingested raw + existing wiki (no repeat live search).
3. Returns the answer to the user (streaming).
4. Calls **`trigger_wiki_refresh`** — background compile (per new raw file) then lint. User is not blocked.

Controlled by `KMA_AUTO_COMPILE_AFTER_RESEARCH` (default on). Implementation: `src/kma/workflows/background.py`, `src/kma/agents/team.py`.

#### CLI: `run_search.py`

For scripted research + synchronous compile + lint (blocking, unlike chat):

```bash
uv run python scripts/run_search.py \
  "what are the difference between flink 2.1 and 2.2" \
  --context ./context \
  --src-file web_site_ref.json
```

- **`web_site_ref.json`**: JSON array (or `{"sites": [...]}`) of `{name, url, description}` entries. Researcher reads these via `read_web_site_refs` and biases search/ingest toward listed domains. Default path: `<context>/web_site_ref.json`.
- **Pipeline**: `src/kma/workflows/enrichment.py` — research → `compile_raw_files` → `run_linter`.
- **Flags**: `--skip-research`, `--skip-compile`, `--skip-lint`, `--dry-run`.

Chat uses the same Researcher + site refs; compile/lint stays async via `trigger_wiki_refresh`.


### Navigator

Primary agent for user interaction. Handles SQL, files, and wiki-aware Q&A (synthesis after Researcher ingest).

Tools: SQLTools, FileTools, update_knowledge, read_wiki_index, read_wiki_state, read_manifest, ontology tools, search_wiki (when `kma_wiki` is indexed). No live web-search toolkit.

Wiki retrieval priority: `search_wiki` (if indexed) → ontology / `wiki/index.md` + `read_file` on concepts/summaries → `raw/`.

### Researcher

Gathers sources from the web, extracts content, converts to clean markdown, saves to `raw/`.

Tools: FileTools, DuckDuckGoTools (`web_search`), update_knowledge, read_web_site_refs, ingest_url (HTTP fetch + text extract), ingest_text, read_manifest.

Always available (no paid search API key).

Does NOT compile wiki articles, modify wiki/, or interact with email/calendar/slack.

### Compiler

Reads uncompiled raw documents and produces/updates wiki articles. One file per invocation; the prompt must name an explicit ``file_id``. Batch compile via repeated runs or ``compile_docs_folder.py``.

Tools: FileTools, update_knowledge, read_manifest, update_manifest_compiled, read_wiki_index, update_wiki_index, read_wiki_state, update_wiki_state.

Design principles: incremental, additive, source-tracked, index-first.

Does NOT interact with users, query live sources, or run web searches.

### Linter

Periodic health checks on the wiki.

Tools: FileTools, update_knowledge, read_wiki_index, read_wiki_state, update_wiki_state, ontology tools.

Checks: contradictions, stale articles, missing concepts, orphans, thin articles, duplicates, gap analysis.

### Syncer

Commits and pushes context/ changes to GitHub. Called by the leader after any workflow that creates or modifies files. Writes descriptive commit messages.

Tools: sync_push, sync_pull, sync_status.

Conditional — only included if `GITHUB_ACCESS_TOKEN` and `KMA_REPO_URL` are set.

Push is event-driven (chained by leader after work). Pull is scheduled (every 30 min) and runs at startup.


## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/teams/kma/runs` | POST | **Primary chat** — run the KMA team with a prompt (Vue UI) |
| `/agents/{id}/runs` | POST | Direct agent runs (Compiler, Navigator, etc.) |
| `/context/reload` | POST | Re-index context files |
| `/wiki/compile` | POST | Trigger wiki compilation |
| `/wiki/lint` | POST | Trigger wiki health check |
| `/wiki/ingest` | POST | Ingest URL or text to raw/ |
| `/sync/pull` | POST | Pull remote context/ changes from GitHub |


## Design Constraints

1. **Navigation over search.** Each source keeps its native query interface.
2. **Metadata in vectors, content on demand.** Knowledge stores routing information, not raw data.
3. **Learning is agentic.** The agent decides what to learn. Corrections always take priority.
4. **Graceful degradation.** Missing credentials disable capabilities with clear fallback messages.
5. **Incremental compilation.** Wiki compilation only processes new raw files. Never rewrites the whole wiki.
6. **Index-first routing.** The wiki index is designed to fit in one LLM read for fast article selection.
7. **Thread-as-session.** Slack thread timestamps map to session IDs.
8. **Git is the persistence layer.** No volumes needed. Context/ is synced to GitHub via the Syncer agent. Push is event-driven, pull is scheduled.