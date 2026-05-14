# KM_Agent Specification

km-agent is a personal knowledge management agent to work on existing studies plus new content discovered by the user.

It works on an existing studies git repositories like [flink-studies](https://github.com/jbcodeforce/flink-studies) to use as  base knowledge, and web search results.

The approach is to use native query interface, to look at files, slack channel, or web content. When new content from wek or slack is added to the knowledge, it goes to raw folder, from which structured wiki is built of.

## Architecture

* agno agent OS to serve the agents and team
* km-agent - to define agents, tools and team
    ├── Navigator    — routes queries, reads wiki, handles SQL/files
    ├── Researcher   - web search, source gathering and write to context/raw/
    ├── Compiler     — reads raw/, writes wiki articles, maintains index
    ├── Linter       — health checks, finds gaps, suggests research

* PostgreSQL 18 to keep agent knowledge,  with pgvector (hybrid vector + keyword search)
* Ollama on the **host** (native CLI; `scripts/setup.sh` + `scripts/starter.sh`) to serve local LLM — not run in Docker Compose for memory reason
*  **Language**: Python 3.12+, managed with `uv`

![](./images/architecture.drawio.png)


**Database layout**: User-created SQL tables (`kma_notes`, `kma_people`, etc.) live in a separate `kma` PostgreSQL schema, isolated from Agno framework tables in the default schema. The SQL engine bootstraps the schema at startup (`CREATE SCHEMA IF NOT EXISTS kma`) and sets `search_path=kma,public` so agents query user tables by default.


## Core Capabilities

### 1. Knowledge Base Pipeline

There are two types of raw knowledge: the docs folder of a studies repository, like flink-studies, and new raw data discovered by the researcher agent.

Raw data flows through a compilation pipeline into a structured wiki:

```
Ingest (Researcher)     →  context/raw/     →  .manifest.json tracks state
Compile (Compiler)      →  context/wiki/    →  concepts/, summaries/, index.md
Query (Navigator)       →  reads wiki index →  pulls specific articles
File outputs (Navigator)→  wiki/outputs/    →  compounds back into wiki
Lint (Linter)           →  wiki/lint-report →  finds gaps, suggests research
```

- **Raw documents** have YAML frontmatter (title, source, date, tags, type, compiled status)
- **Wiki articles** have frontmatter (title, dates, sources, related concepts, tags)
- **Wiki index** lists all articles with 1-line summaries — fits in one LLM read (~5K tokens at 100 articles)
- **Manifest** tracks compile state per raw file — incremental, never rewrites the whole wiki

When data comes from docs of a studies repository the date of the file, and its content may changed overtime after indexing so compiler may modify wiki concepts, index and summaries. 



### 2. Context Navigation

Intent classification determines which sources to check:

| Intent | Sources | Behavior |
|--------|---------|----------|
| `capture` | SQL | Insert, confirm, done |
| `retrieve` | Wiki + SQL + Files + Knowledge | Query, present results |
| `connect` | Wiki + SQL + Files  | Multi-source synthesis |
| `research` | Exa (+ raw/ to save) | Search, summarize, optionally ingest |
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

### 4. Dual Knowledge System

- **`kma_knowledge`** — Metadata index (routing layer). File manifests (`File:`), table schemas (`Schema:`), source capabilities (`Source:`), cross-source discoveries (`Discovery:`), wiki articles (`Wiki:`), raw sources (`Raw:`).
- **`kma_learnings`** — Operational memory. Retrieval strategies (`Retrieval:`), recurring patterns (`Pattern:`), explicit user corrections (`Correction:`). Corrections always take priority.

**Bootstrap**: `context/load_context.py` populates `kma_knowledge` on first run by scanning the context directory, parsing YAML frontmatter for tags, and inserting `File:` metadata entries. This is the bootstrap step that makes Navigator's recall work — without it, the knowledge routing layer is empty. Supports `--recreate` (clear and reload) and `--dry-run` (preview). Also exposed via `/context/reload` endpoint and scheduled daily.

### 5. Learning System

Navigator uses Agno's `LearningMachine` with `AGENTIC` mode — the agent autonomously decides what to learn from each interaction and saves it to `kma_learnings`. This is the mechanism behind the "learns how you work" promise. Manual learning via `save_learning` tool calls is supplementary.

### 6. Agent Memory Tiers

Not all agents need memory. The team uses a tiered approach:

- **Leader + Navigator**: Full memory — agentic memory, past session search, chat history. These are the agents with user-facing continuity across conversations.
- **Researcher, Compiler, Linter, Syncer**: Datetime context only. No memory, no session search. These are stateless workers that get fresh context per invocation.

This keeps worker agents fast and focused while the user-facing agents maintain conversational continuity.


### 7. Context Directory

```
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

- **Parallel** (Researcher): Search + extract via `parallel_search` and `parallel_extract`. Requires `PARALLEL_API_KEY`. When configured, Researcher is active and `ingest_url` auto-fetches content.
- **Exa** (Navigator, Linter): General web search via Exa MCP server (always loaded). `EXA_API_KEY` optional for authenticated access.



## Agents

### kma (Team Leader)

Routes requests to specialists or responds directly for simple things.

| Request Type | Agent |
|-------------|-------|
| Knowledge queries, SQL, files | Navigator |
| "Ingest this", research a topic | Researcher |
| "Compile the wiki" | Compiler |
| "Lint the wiki", "find gaps" | Linter |
| Greetings, thanks, "what can you do?" | Direct response |


### Navigator

Primary agent for user interaction. Handles SQL, files, web search, and wiki-aware Q&A.

Tools: SQLTools, FileTools, MCPTools (Exa), update_knowledge, read_wiki_index, read_wiki_state, read_manifest.

Wiki retrieval priority: `wiki/concepts/` → `wiki/summaries/` → `raw/` → live sources.

### Researcher

Gathers sources from the web, extracts content, converts to clean markdown, saves to `raw/`.

Tools: FileTools, ParallelTools (parallel_search, parallel_extract), update_knowledge, ingest_url (auto-fetches via Parallel), ingest_text, read_manifest.

Conditional — only instantiated when `PARALLEL_API_KEY` is set. Without it, Navigator handles basic web search via Exa.

Does NOT compile wiki articles, modify wiki/, or interact with email/calendar/slack.

### Compiler

Reads uncompiled raw documents and produces/updates wiki articles.

Tools: FileTools, update_knowledge, read_manifest, update_manifest_compiled, read_wiki_index, update_wiki_index, read_wiki_state, update_wiki_state.

Design principles: incremental, additive, source-tracked, index-first.

Does NOT interact with users, query live sources, or run web searches.

### Linter

Periodic health checks on the wiki.

Tools: FileTools, MCPTools (Exa), update_knowledge, read_wiki_index, read_wiki_state, update_wiki_state.

Checks: contradictions, stale articles, missing concepts, orphans, thin articles, duplicates, gap analysis.

### Syncer

Commits and pushes context/ changes to GitHub. Called by the leader after any workflow that creates or modifies files. Writes descriptive commit messages.

Tools: sync_push, sync_pull, sync_status.

Conditional — only included if `GITHUB_ACCESS_TOKEN` and `KMA_REPO_URL` are set.

Push is event-driven (chained by leader after work). Pull is scheduled (every 30 min) and runs at startup.


## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/teams/kma/runs` | POST | Run the KMA team with a prompt |
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